#!/usr/bin/env python3
"""
Spectral Topology Engine — Example: Microservice Dependency Analysis

Detects hidden dependencies and unmonitored API endpoints in a
microservice architecture by computing the eigenspectrum of the
service call graph.
"""

from topology_engine import GraphBuilder, SpectralTopologyAnalyzer


def main():
    # Define a microservice call graph
    # (source_service, target_service, call_frequency_weight)
    services = [
        "api-gateway",    # 0
        "auth-service",   # 1
        "user-service",   # 2
        "order-service",  # 3
        "payment-service",# 4
        "inventory",      # 5
        "notifications",  # 6
        "analytics",      # 7
    ]

    # Observed edges: who calls whom
    edges = [
        (0, 1, 10.0),  # gateway → auth (heavy traffic)
        (0, 2, 8.0),   # gateway → users
        (0, 3, 6.0),   # gateway → orders
        (3, 4, 5.0),   # orders → payments
        (3, 5, 4.0),   # orders → inventory
        (1, 2, 3.0),   # auth → users (token validation)
        # MISSING: orders → notifications (gap!)
        # MISSING: analytics → user-service (gap!)
        # MISSING: payment-service → notifications (gap!)
    ]

    n = len(services)
    adj = GraphBuilder.from_edge_list(n, edges)

    # Optional: add metadata similarity (services with similar names/tags)
    features = np.array([
        [1, 0, 0, 0],  # api-gateway: external-facing, HTTP, no DB, sync
        [0, 1, 0, 1],  # auth: internal, HTTP, has DB, async
        [0, 1, 0, 1],  # users: internal, HTTP, has DB, async
        [0, 0, 1, 0],  # orders: internal, gRPC, no DB, sync
        [0, 0, 1, 1],  # payments: internal, gRPC, has DB, async
        [0, 1, 0, 0],  # inventory: internal, HTTP, no DB, sync
        [0, 0, 0, 1],  # notifications: internal, no protocol, no DB, async
        [0, 1, 0, 0],  # analytics: internal, HTTP, no DB, sync
    ], dtype=float)

    import numpy as np  # noqa (re-import for clarity)

    sim = GraphBuilder.cosine_similarity_matrix(features)

    # Analyze
    analyzer = SpectralTopologyAnalyzer(alpha=0.3, top_k_nodes=3)
    report = analyzer.analyze(adj, similarity=sim)

    print(report.summary())
    print()

    if report.gaps:
        print("🔧 Detected Structural Gaps (likely missing service calls):")
        for i, gap in enumerate(report.gaps):
            nodes = [services[j] for j in gap.node_indices[:3]]
            print(f"  Gap {i+1}: λ={gap.eigenvalue:.4f}")
            print(f"    Likely missing call involving: {', '.join(nodes)}")
            print()
    else:
        print("✅ No structural gaps detected — topology appears cohesive.")


if __name__ == "__main__":
    main()
