/**
 * EventSpine — Append-Only Cryptographic Event Sourcing Ledger
 *
 * Every state transition emits a frozen, hash-chained event.
 * State is reconstructed by replaying the ledger from genesis.
 * No mutations. No deletions. No database required.
 */
import { EventEmitter } from "node:events";
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
export declare class EventSpine extends EventEmitter {
    private config;
    private ringBuffer;
    private lastSequence;
    private lastHash;
    private currentFile;
    private currentFileSize;
    private totalEvents;
    private flushTimer;
    private writeStream;
    private flushing;
    constructor(config: SpineConfig);
    open(): Promise<void>;
    close(): Promise<void>;
    append<T = Record<string, unknown>>(domain: EventDomain, kind: string, payload: T): OperationalEvent<T>;
    flush(): Promise<void>;
    replay<T = Record<string, unknown>>(): AsyncGenerator<OperationalEvent<T>>;
    /**
     * Rehydrate state by reducing over the entire event history.
     * The reducer function must be a pure function of (state, event) → state.
     */
    rehydrate<S, T = Record<string, unknown>>(initialState: S, reducer: (state: S, event: OperationalEvent<T>) => S): Promise<S>;
    verify(): Promise<{
        valid: boolean;
        breakAt?: number;
        errors: string[];
    }>;
    query<T = Record<string, unknown>>(filter: {
        domain?: EventDomain;
        kind?: string;
        since?: string;
        until?: string;
        limit?: number;
    }): Promise<OperationalEvent<T>[]>;
    stats(): SpineStats;
    private rotateFile;
    private rehydrateTail;
}
