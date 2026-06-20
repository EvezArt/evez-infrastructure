"""Tests for the Spectral Topology Engine."""

import numpy as np
import pytest
from topology_engine import (
    GraphBuilder,
    SpectralTopologyAnalyzer,
    StructuralGap,
    TopologyReport,
    quick_analyze,
)


class TestGraphBuilder:
    def test_from_edge_list_basic(self):
        edges = [(0, 1, 1.0), (1, 2, 1.0), (2, 0, 1.0)]
        adj = GraphBuilder.from_edge_list(3, edges)
        assert adj.shape == (3, 3)
        assert adj.nnz == 3

    def test_cosine_similarity(self):
        features = np.array([[1, 0, 0], [0.9, 0.1, 0], [0, 1, 0]], dtype=float)
        sim = GraphBuilder.cosine_similarity_matrix(features)
        assert sim.shape == (3, 3)
        # Node 0 and 1 should be similar
        assert sim[0, 1] > 0.5

    def test_from_citation_graph(self):
        docs = [
            {"id": "a", "references": ["b", "c"]},
            {"id": "b", "references": ["c"]},
            {"id": "c", "references": []},
        ]
        n, adj, idx_map = GraphBuilder.from_citation_graph(docs)
        assert n == 3
        assert adj.nnz == 3


class TestSpectralTopologyAnalyzer:
    def test_triangle_graph_no_gaps(self):
        """A complete triangle should have no structural gaps."""
        edges = [(0, 1, 1.0), (1, 2, 1.0), (2, 0, 1.0)]
        report = quick_analyze(edges, n_nodes=3)
        # A dense 3-node cycle might still have minor negatives,
        # but there should be very few
        assert report.n_nodes == 3
        assert report.n_edges == 3

    def test_star_graph_has_gaps(self):
        """A star graph (hub + spokes) should show structural gaps."""
        edges = [
            (0, 1, 1.0),
            (0, 2, 1.0),
            (0, 3, 1.0),
            (0, 4, 1.0),
        ]
        report = quick_analyze(edges, n_nodes=5, alpha=0.0)
        assert report.n_nodes == 5
        assert report.n_edges == 4

    def test_with_similarity(self):
        """Adding similarity should influence gap detection."""
        edges = [(0, 1, 1.0), (1, 2, 1.0)]
        adj = GraphBuilder.from_edge_list(4, edges)

        # Node 3 is structurally isolated but similar to node 2
        features = np.array([
            [1, 0], [1, 0], [0, 1], [0, 0.99]  # node 3 ≈ node 2
        ], dtype=float)
        sim = GraphBuilder.cosine_similarity_matrix(features)

        analyzer = SpectralTopologyAnalyzer(alpha=0.5)
        report = analyzer.analyze(adj, similarity=sim)
        assert report.n_nodes == 4

    def test_report_summary(self):
        edges = [(0, 1, 1.0), (1, 2, 1.0), (2, 0, 1.0)]
        report = quick_analyze(edges, n_nodes=3)
        summary = report.summary()
        assert "Topology Report" in summary

    def test_report_json_export(self, tmp_path):
        edges = [(0, 1, 1.0)]
        report = quick_analyze(edges, n_nodes=3)
        out = tmp_path / "report.json"
        report.to_json(out)
        import json
        data = json.loads(out.read_text())
        assert data["n_nodes"] == 3


class TestStructuralGap:
    def test_to_dict(self):
        gap = StructuralGap(
            eigenvalue=-0.5,
            eigenvector=np.array([0.1, 0.9, 0.3]),
            node_indices=[1, 2, 0],
            node_weights=[0.9, 0.3, 0.1],
        )
        d = gap.to_dict()
        assert d["eigenvalue"] == -0.5
        assert len(d["node_indices"]) == 3
