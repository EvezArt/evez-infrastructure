"use strict";
/**
 * EventSpine — Usage Examples
 */
Object.defineProperty(exports, "__esModule", { value: true });
const index_1 = require("./index");
// ---------------------------------------------------------------------------
// Basic Setup
// ---------------------------------------------------------------------------
async function basicExample() {
    const spine = new index_1.EventSpine({
        dataDir: "/tmp/spine-data",
        batchSize: 50,
        flushIntervalMs: 500,
        maxFileSizeBytes: 10 * 1024 * 1024, // 10 MB per file
    });
    await spine.open();
    // Append events — these are buffered in the ring buffer
    const evt1 = spine.append("routing", "SIGNAL_UPDATE", {
        model: "deepseek-v4",
        latency: 42,
        tokens: 1800,
    });
    const evt2 = spine.append("monetization", "USAGE_RECORDED", {
        userId: "usr_abc123",
        costUsd: 0.003,
        decisionCount: 1,
    });
    console.log("Event 1 hash:", evt1.hash.slice(0, 16) + "…");
    console.log("Event 2 prevHash:", evt2.prevHash.slice(0, 16) + "…");
    // Flush remaining buffer and close
    await spine.close();
}
async function rehydrationExample() {
    const spine = new index_1.EventSpine({ dataDir: "/tmp/spine-data" });
    await spine.open();
    // Rehydrate: reduce over the entire event history to rebuild state
    const initialState = {
        currentModel: "unknown",
        totalCost: 0,
        decisions: 0,
    };
    const state = await spine.rehydrate(initialState, (s, event) => {
        switch (event.kind) {
            case "SIGNAL_UPDATE":
                return { ...s, currentModel: event.payload.model ?? s.currentModel };
            case "USAGE_RECORDED":
                return {
                    ...s,
                    totalCost: s.totalCost + (event.payload.costUsd ?? 0),
                    decisions: s.decisions + 1,
                };
            default:
                return s;
        }
    });
    console.log("Rehydrated state:", state);
    await spine.close();
}
// ---------------------------------------------------------------------------
// Integrity Verification
// ---------------------------------------------------------------------------
async function verificationExample() {
    const spine = new index_1.EventSpine({ dataDir: "/tmp/spine-data" });
    await spine.open();
    const result = await spine.verify();
    if (result.valid) {
        console.log("✅ Ledger integrity verified");
    }
    else {
        console.error("❌ Chain broken at sequence", result.breakAt);
        result.errors.forEach((e) => console.error("  ", e));
    }
    await spine.close();
}
// ---------------------------------------------------------------------------
// Time-Range Query
// ---------------------------------------------------------------------------
async function queryExample() {
    const spine = new index_1.EventSpine({ dataDir: "/tmp/spine-data" });
    await spine.open();
    const recent = await spine.query({
        domain: "monetization",
        since: "2026-06-20T00:00:00Z",
        limit: 100,
    });
    console.log(`Found ${recent.length} monetization events since midnight`);
    await spine.close();
}
// Run
basicExample().catch(console.error);
