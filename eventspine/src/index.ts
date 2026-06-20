/**
 * EventSpine — Append-Only Cryptographic Event Sourcing Ledger
 *
 * Every state transition emits a frozen, hash-chained event.
 * State is reconstructed by replaying the ledger from genesis.
 * No mutations. No deletions. No database required.
 */

import { createHash, Hash } from "node:crypto";
import { open, FileHandle } from "node:fs/promises";
import { createReadStream, createWriteStream, ReadStream } from "node:fs";
import { join } from "node:path";
import { pipeline } from "node:stream/promises";
import { createInterface } from "node:readline";
import { EventEmitter } from "node:events";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type EventDomain = "market" | "monetization" | "routing" | "automation" | "system";

export interface OperationalEvent<T = Record<string, unknown>> {
  id: string;
  domain: EventDomain;
  kind: string;
  payload: T;
  timestamp: string;
  sequence: number;
  prevHash: string;
  hash: string;
}

export interface SpineConfig {
  /** Directory where .jsonl ledger files live */
  dataDir: string;
  /** Base name for ledger files (default: "spine") */
  baseName?: string;
  /** Max events buffered before flush (default: 100) */
  batchSize?: number;
  /** Max milliseconds before buffered events are flushed (default: 1000) */
  flushIntervalMs?: number;
  /** Maximum ledger file size in bytes before rotation (default: 50 MB) */
  maxFileSizeBytes?: number;
}

export interface SpineStats {
  totalEvents: number;
  lastSequence: number;
  lastHash: string;
  currentFile: string;
  currentFileSize: number;
  pendingBatchSize: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function uuid(): string {
  const { randomUUID } = require("node:crypto");
  return randomUUID();
}

function computeEventHash(event: Omit<OperationalEvent, "hash">): string {
  // Deterministic canonical JSON — keys sorted, no whitespace
  const canonical = JSON.stringify(
    {
      id: event.id,
      domain: event.domain,
      kind: event.kind,
      payload: event.payload,
      timestamp: event.timestamp,
      sequence: event.sequence,
      prevHash: event.prevHash,
    },
    Object.keys(event.payload).sort(),
    0
  );
  return createHash("sha256").update(canonical).digest("hex");
}

function isoNow(): string {
  return new Date().toISOString();
}

// ---------------------------------------------------------------------------
// Ring Buffer — Non-blocking write batching
// ---------------------------------------------------------------------------

class RingBuffer<T> {
  private buffer: (T | null)[];
  private head = 0;
  private tail = 0;
  private count = 0;

  constructor(private capacity: number) {
    this.buffer = new Array(capacity).fill(null);
  }

  push(item: T): boolean {
    if (this.count >= this.capacity) return false;
    this.buffer[this.tail] = item;
    this.tail = (this.tail + 1) % this.capacity;
    this.count++;
    return true;
  }

  drain(): T[] {
    const items: T[] = [];
    while (this.count > 0) {
      const item = this.buffer[this.head];
      if (item !== null) items.push(item);
      this.buffer[this.head] = null;
      this.head = (this.head + 1) % this.capacity;
      this.count--;
    }
    return items;
  }

  get size(): number {
    return this.count;
  }
}

// ---------------------------------------------------------------------------
// EventSpine — The Ledger
// ---------------------------------------------------------------------------

export class EventSpine extends EventEmitter {
  private config: Required<SpineConfig>;
  private ringBuffer: RingBuffer<OperationalEvent>;
  private lastSequence = 0;
  private lastHash =
    "0000000000000000000000000000000000000000000000000000000000000000"; // genesis
  private currentFile = "";
  private currentFileSize = 0;
  private totalEvents = 0;
  private flushTimer: ReturnType<typeof setInterval> | null = null;
  private writeStream: FileHandle | null = null;
  private flushing = false;

  constructor(config: SpineConfig) {
    super();
    this.config = {
      dataDir: config.dataDir,
      baseName: config.baseName ?? "spine",
      batchSize: config.batchSize ?? 100,
      flushIntervalMs: config.flushIntervalMs ?? 1000,
      maxFileSizeBytes: config.maxFileSizeBytes ?? 50 * 1024 * 1024,
    };
    this.ringBuffer = new RingBuffer(this.config.batchSize * 2);
  }

  // -----------------------------------------------------------------------
  // Lifecycle
  // -----------------------------------------------------------------------

  async open(): Promise<void> {
    // Discover latest ledger file
    const fs = await import("node:fs/promises");
    await fs.mkdir(this.config.dataDir, { recursive: true });

    const files = await fs.readdir(this.config.dataDir);
    const ledgerFiles = files
      .filter((f) => f.startsWith(this.config.baseName) && f.endsWith(".jsonl"))
      .sort();

    if (ledgerFiles.length > 0) {
      this.currentFile = ledgerFiles[ledgerFiles.length - 1];
      const stat = await fs.stat(join(this.config.dataDir, this.currentFile));
      this.currentFileSize = stat.size;

      // Rehydrate state from last event
      await this.rehydrateTail();
    } else {
      await this.rotateFile();
    }

    // Start periodic flush
    this.flushTimer = setInterval(() => this.flush(), this.config.flushIntervalMs);
  }

  async close(): Promise<void> {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
    await this.flush();
    if (this.writeStream) {
      await this.writeStream.close();
      this.writeStream = null;
    }
  }

  // -----------------------------------------------------------------------
  // Append — The only write operation
  // -----------------------------------------------------------------------

  append<T = Record<string, unknown>>(
    domain: EventDomain,
    kind: string,
    payload: T
  ): OperationalEvent<T> {
    this.lastSequence++;

    const event: Omit<OperationalEvent<T>, "hash"> = {
      id: uuid(),
      domain,
      kind,
      payload,
      timestamp: isoNow(),
      sequence: this.lastSequence,
      prevHash: this.lastHash,
    };

    const hash = computeEventHash(event as OperationalEvent<Record<string, unknown>>);
    const fullEvent: OperationalEvent<T> = { ...event, hash };

    this.lastHash = hash;

    if (!this.ringBuffer.push(fullEvent as OperationalEvent)) {
      // Ring buffer full — force immediate flush
      this.flush().catch(() => {});
      this.ringBuffer.push(fullEvent as OperationalEvent);
    }

    this.emit("event", fullEvent);

    // Auto-flush when batch threshold is reached
    if (this.ringBuffer.size >= this.config.batchSize) {
      this.flush().catch(() => {});
    }

    return fullEvent;
  }

  // -----------------------------------------------------------------------
  // Flush — Batch write from ring buffer to disk
  // -----------------------------------------------------------------------

  async flush(): Promise<void> {
    if (this.flushing) return;
    this.flushing = true;

    try {
      const batch = this.ringBuffer.drain();
      if (batch.length === 0) return;

      // Check file rotation
      if (this.currentFileSize >= this.config.maxFileSizeBytes) {
        await this.rotateFile();
      }

      const fs = await import("node:fs/promises");
      const lines = batch.map((e) => JSON.stringify(e)).join("\n") + "\n";
      const filePath = join(this.config.dataDir, this.currentFile);

      await fs.appendFile(filePath, lines, "utf-8");

      this.currentFileSize += Buffer.byteLength(lines, "utf-8");
      this.totalEvents += batch.length;

      this.emit("flushed", batch.length);
    } finally {
      this.flushing = false;
    }
  }

  // -----------------------------------------------------------------------
  // Replay — Reconstruct state from the entire ledger
  // -----------------------------------------------------------------------

  async *replay<T = Record<string, unknown>>(): AsyncGenerator<OperationalEvent<T>> {
    const fs = await import("node:fs/promises");
    const files = await fs.readdir(this.config.dataDir);
    const ledgerFiles = files
      .filter((f) => f.startsWith(this.config.baseName) && f.endsWith(".jsonl"))
      .sort();

    for (const file of ledgerFiles) {
      const filePath = join(this.config.dataDir, file);
      const stream = createReadStream(filePath, { encoding: "utf-8" });
      const rl = createInterface({ input: stream, crlfDelay: Infinity });

      for await (const line of rl) {
        if (!line.trim()) continue;
        try {
          yield JSON.parse(line) as OperationalEvent<T>;
        } catch {
          // Skip corrupted lines — the hash chain will catch integrity breaks
        }
      }
    }
  }

  /**
   * Rehydrate state by reducing over the entire event history.
   * The reducer function must be a pure function of (state, event) → state.
   */
  async rehydrate<S, T = Record<string, unknown>>(
    initialState: S,
    reducer: (state: S, event: OperationalEvent<T>) => S
  ): Promise<S> {
    let state = initialState;
    for await (const event of this.replay<T>()) {
      state = reducer(state, event);
    }
    return state;
  }

  // -----------------------------------------------------------------------
  // Integrity Verification
  // -----------------------------------------------------------------------

  async verify(): Promise<{ valid: boolean; breakAt?: number; errors: string[] }> {
    const errors: string[] = [];
    let prevHash =
      "0000000000000000000000000000000000000000000000000000000000000000";
    let seq = 0;

    for await (const event of this.replay()) {
      seq++;

      if (event.prevHash !== prevHash) {
        errors.push(
          `Chain break at seq ${event.sequence}: prevHash mismatch ` +
            `(expected ${prevHash}, got ${event.prevHash})`
        );
        if (!errors.length) {
          return { valid: false, breakAt: event.sequence, errors };
        }
      }

      const expected = computeEventHash({
        id: event.id,
        domain: event.domain,
        kind: event.kind,
        payload: event.payload as Record<string, unknown>,
        timestamp: event.timestamp,
        sequence: event.sequence,
        prevHash: event.prevHash,
      } as OperationalEvent);

      if (event.hash !== expected) {
        errors.push(
          `Hash mismatch at seq ${event.sequence}: ` +
            `(expected ${expected}, got ${event.hash})`
        );
        return { valid: false, breakAt: event.sequence, errors };
      }

      prevHash = event.hash;
    }

    return { valid: errors.length === 0, errors };
  }

  // -----------------------------------------------------------------------
  // Query — Filter events by domain, kind, or time range
  // -----------------------------------------------------------------------

  async query<T = Record<string, unknown>>(filter: {
    domain?: EventDomain;
    kind?: string;
    since?: string; // ISO timestamp
    until?: string; // ISO timestamp
    limit?: number;
  }): Promise<OperationalEvent<T>[]> {
    const results: OperationalEvent<T>[] = [];

    for await (const event of this.replay<T>()) {
      if (filter.domain && event.domain !== filter.domain) continue;
      if (filter.kind && event.kind !== filter.kind) continue;
      if (filter.since && event.timestamp < filter.since) continue;
      if (filter.until && event.timestamp > filter.until) continue;

      results.push(event);
      if (filter.limit && results.length >= filter.limit) break;
    }

    return results;
  }

  // -----------------------------------------------------------------------
  // Stats
  // -----------------------------------------------------------------------

  stats(): SpineStats {
    return {
      totalEvents: this.totalEvents,
      lastSequence: this.lastSequence,
      lastHash: this.lastHash,
      currentFile: this.currentFile,
      currentFileSize: this.currentFileSize,
      pendingBatchSize: this.ringBuffer.size,
    };
  }

  // -----------------------------------------------------------------------
  // Internal
  // -----------------------------------------------------------------------

  private async rotateFile(): Promise<void> {
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    this.currentFile = `${this.config.baseName}-${timestamp}.jsonl`;
    this.currentFileSize = 0;

    const fs = await import("node:fs/promises");
    await fs.writeFile(join(this.config.dataDir, this.currentFile), "", "utf-8");

    this.emit("rotate", this.currentFile);
  }

  private async rehydrateTail(): Promise<void> {
    // Read only the last line of the current file to get sequence and hash
    const fs = await import("node:fs/promises");
    const filePath = join(this.config.dataDir, this.currentFile);
    const content = await fs.readFile(filePath, "utf-8");
    const lines = content.trim().split("\n").filter(Boolean);

    if (lines.length === 0) return;

    let count = 0;
    for (const line of lines) {
      try {
        const event = JSON.parse(line);
        this.lastSequence = Math.max(this.lastSequence, event.sequence ?? 0);
        this.lastHash = event.hash ?? this.lastHash;
        count++;
      } catch {
        // skip
      }
    }

    this.totalEvents += count;
  }
}
