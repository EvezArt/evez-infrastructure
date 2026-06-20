"use strict";
/**
 * EventSpine — Append-Only Cryptographic Event Sourcing Ledger
 *
 * Every state transition emits a frozen, hash-chained event.
 * State is reconstructed by replaying the ledger from genesis.
 * No mutations. No deletions. No database required.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.EventSpine = void 0;
const node_crypto_1 = require("node:crypto");
const node_fs_1 = require("node:fs");
const node_path_1 = require("node:path");
const node_readline_1 = require("node:readline");
const node_events_1 = require("node:events");
// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function uuid() {
    const { randomUUID } = require("node:crypto");
    return randomUUID();
}
function computeEventHash(event) {
    // Deterministic canonical JSON — keys sorted, no whitespace
    const canonical = JSON.stringify({
        id: event.id,
        domain: event.domain,
        kind: event.kind,
        payload: event.payload,
        timestamp: event.timestamp,
        sequence: event.sequence,
        prevHash: event.prevHash,
    }, Object.keys(event.payload).sort(), 0);
    return (0, node_crypto_1.createHash)("sha256").update(canonical).digest("hex");
}
function isoNow() {
    return new Date().toISOString();
}
// ---------------------------------------------------------------------------
// Ring Buffer — Non-blocking write batching
// ---------------------------------------------------------------------------
class RingBuffer {
    capacity;
    buffer;
    head = 0;
    tail = 0;
    count = 0;
    constructor(capacity) {
        this.capacity = capacity;
        this.buffer = new Array(capacity).fill(null);
    }
    push(item) {
        if (this.count >= this.capacity)
            return false;
        this.buffer[this.tail] = item;
        this.tail = (this.tail + 1) % this.capacity;
        this.count++;
        return true;
    }
    drain() {
        const items = [];
        while (this.count > 0) {
            const item = this.buffer[this.head];
            if (item !== null)
                items.push(item);
            this.buffer[this.head] = null;
            this.head = (this.head + 1) % this.capacity;
            this.count--;
        }
        return items;
    }
    get size() {
        return this.count;
    }
}
// ---------------------------------------------------------------------------
// EventSpine — The Ledger
// ---------------------------------------------------------------------------
class EventSpine extends node_events_1.EventEmitter {
    config;
    ringBuffer;
    lastSequence = 0;
    lastHash = "0000000000000000000000000000000000000000000000000000000000000000"; // genesis
    currentFile = "";
    currentFileSize = 0;
    totalEvents = 0;
    flushTimer = null;
    writeStream = null;
    flushing = false;
    constructor(config) {
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
    async open() {
        // Discover latest ledger file
        const fs = await import("node:fs/promises");
        await fs.mkdir(this.config.dataDir, { recursive: true });
        const files = await fs.readdir(this.config.dataDir);
        const ledgerFiles = files
            .filter((f) => f.startsWith(this.config.baseName) && f.endsWith(".jsonl"))
            .sort();
        if (ledgerFiles.length > 0) {
            this.currentFile = ledgerFiles[ledgerFiles.length - 1];
            const stat = await fs.stat((0, node_path_1.join)(this.config.dataDir, this.currentFile));
            this.currentFileSize = stat.size;
            // Rehydrate state from last event
            await this.rehydrateTail();
        }
        else {
            await this.rotateFile();
        }
        // Start periodic flush
        this.flushTimer = setInterval(() => this.flush(), this.config.flushIntervalMs);
    }
    async close() {
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
    append(domain, kind, payload) {
        this.lastSequence++;
        const event = {
            id: uuid(),
            domain,
            kind,
            payload,
            timestamp: isoNow(),
            sequence: this.lastSequence,
            prevHash: this.lastHash,
        };
        const hash = computeEventHash(event);
        const fullEvent = { ...event, hash };
        this.lastHash = hash;
        if (!this.ringBuffer.push(fullEvent)) {
            // Ring buffer full — force immediate flush
            this.flush().catch(() => { });
            this.ringBuffer.push(fullEvent);
        }
        this.emit("event", fullEvent);
        // Auto-flush when batch threshold is reached
        if (this.ringBuffer.size >= this.config.batchSize) {
            this.flush().catch(() => { });
        }
        return fullEvent;
    }
    // -----------------------------------------------------------------------
    // Flush — Batch write from ring buffer to disk
    // -----------------------------------------------------------------------
    async flush() {
        if (this.flushing)
            return;
        this.flushing = true;
        try {
            const batch = this.ringBuffer.drain();
            if (batch.length === 0)
                return;
            // Check file rotation
            if (this.currentFileSize >= this.config.maxFileSizeBytes) {
                await this.rotateFile();
            }
            const fs = await import("node:fs/promises");
            const lines = batch.map((e) => JSON.stringify(e)).join("\n") + "\n";
            const filePath = (0, node_path_1.join)(this.config.dataDir, this.currentFile);
            await fs.appendFile(filePath, lines, "utf-8");
            this.currentFileSize += Buffer.byteLength(lines, "utf-8");
            this.totalEvents += batch.length;
            this.emit("flushed", batch.length);
        }
        finally {
            this.flushing = false;
        }
    }
    // -----------------------------------------------------------------------
    // Replay — Reconstruct state from the entire ledger
    // -----------------------------------------------------------------------
    async *replay() {
        const fs = await import("node:fs/promises");
        const files = await fs.readdir(this.config.dataDir);
        const ledgerFiles = files
            .filter((f) => f.startsWith(this.config.baseName) && f.endsWith(".jsonl"))
            .sort();
        for (const file of ledgerFiles) {
            const filePath = (0, node_path_1.join)(this.config.dataDir, file);
            const stream = (0, node_fs_1.createReadStream)(filePath, { encoding: "utf-8" });
            const rl = (0, node_readline_1.createInterface)({ input: stream, crlfDelay: Infinity });
            for await (const line of rl) {
                if (!line.trim())
                    continue;
                try {
                    yield JSON.parse(line);
                }
                catch {
                    // Skip corrupted lines — the hash chain will catch integrity breaks
                }
            }
        }
    }
    /**
     * Rehydrate state by reducing over the entire event history.
     * The reducer function must be a pure function of (state, event) → state.
     */
    async rehydrate(initialState, reducer) {
        let state = initialState;
        for await (const event of this.replay()) {
            state = reducer(state, event);
        }
        return state;
    }
    // -----------------------------------------------------------------------
    // Integrity Verification
    // -----------------------------------------------------------------------
    async verify() {
        const errors = [];
        let prevHash = "0000000000000000000000000000000000000000000000000000000000000000";
        let seq = 0;
        for await (const event of this.replay()) {
            seq++;
            if (event.prevHash !== prevHash) {
                errors.push(`Chain break at seq ${event.sequence}: prevHash mismatch ` +
                    `(expected ${prevHash}, got ${event.prevHash})`);
                if (!errors.length) {
                    return { valid: false, breakAt: event.sequence, errors };
                }
            }
            const expected = computeEventHash({
                id: event.id,
                domain: event.domain,
                kind: event.kind,
                payload: event.payload,
                timestamp: event.timestamp,
                sequence: event.sequence,
                prevHash: event.prevHash,
            });
            if (event.hash !== expected) {
                errors.push(`Hash mismatch at seq ${event.sequence}: ` +
                    `(expected ${expected}, got ${event.hash})`);
                return { valid: false, breakAt: event.sequence, errors };
            }
            prevHash = event.hash;
        }
        return { valid: errors.length === 0, errors };
    }
    // -----------------------------------------------------------------------
    // Query — Filter events by domain, kind, or time range
    // -----------------------------------------------------------------------
    async query(filter) {
        const results = [];
        for await (const event of this.replay()) {
            if (filter.domain && event.domain !== filter.domain)
                continue;
            if (filter.kind && event.kind !== filter.kind)
                continue;
            if (filter.since && event.timestamp < filter.since)
                continue;
            if (filter.until && event.timestamp > filter.until)
                continue;
            results.push(event);
            if (filter.limit && results.length >= filter.limit)
                break;
        }
        return results;
    }
    // -----------------------------------------------------------------------
    // Stats
    // -----------------------------------------------------------------------
    stats() {
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
    async rotateFile() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        this.currentFile = `${this.config.baseName}-${timestamp}.jsonl`;
        this.currentFileSize = 0;
        const fs = await import("node:fs/promises");
        await fs.writeFile((0, node_path_1.join)(this.config.dataDir, this.currentFile), "", "utf-8");
        this.emit("rotate", this.currentFile);
    }
    async rehydrateTail() {
        // Read only the last line of the current file to get sequence and hash
        const fs = await import("node:fs/promises");
        const filePath = (0, node_path_1.join)(this.config.dataDir, this.currentFile);
        const content = await fs.readFile(filePath, "utf-8");
        const lines = content.trim().split("\n").filter(Boolean);
        if (lines.length === 0)
            return;
        let count = 0;
        for (const line of lines) {
            try {
                const event = JSON.parse(line);
                this.lastSequence = Math.max(this.lastSequence, event.sequence ?? 0);
                this.lastHash = event.hash ?? this.lastHash;
                count++;
            }
            catch {
                // skip
            }
        }
        this.totalEvents += count;
    }
}
exports.EventSpine = EventSpine;
