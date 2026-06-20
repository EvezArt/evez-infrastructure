"""
Spectral Topology Engine — Graph Anomaly Detection via Eigenvalue Decomposition

Finds structural holes, hidden dependencies, and missing links in directed
networks by computing the eigenspectrum of a combined adjacency + similarity
matrix. Negative eigenvalues indicate topological gaps where edges should
exist to balance the network but are missing from the observed data.

Designed for:
  - Microservice/API dependency graph analysis
  - Document citation network forensics
  - Supply chain topology auditing
  - Blockchain transaction graph analysis

Memory-optimized: uses scipy.sparse matrices throughout to stay well within
a 2GB RAM budget even for graphs with 100k+ nodes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from scipy import sparse
from scipy.sparse import linalg as sparse_linalg


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class StructuralGap:
    """A detected structural hole in the graph topology."""
    eigenvalue: float
    """Negative eigenvalue magnitude — larger absolute value = more severe gap."""
    eigenvector: np.ndarray
    """Cohesion vector indicating which nodes participate in the gap."""
    node_indices: list[int]
    """Top-N node indices contributing most to this gap."""
    node_weights: list[float]
    """Corresponding weights for the top-N nodes."""

    def to_dict(self) -> dict:
        return {
            "eigenvalue": float(self.eigenvalue),
            "node_indices": self.node_indices,
            "node_weights": [float(w) for w in self.node_weights],
        }


@dataclass
class TopologyReport:
    """Full analysis report from a spectral topology scan."""
    n_nodes: int
    n_edges: int
    alpha: float
    eigenvalues: np.ndarray
    gaps: list[StructuralGap] = field(default_factory=list)
    density: float = 0.0
    spectral_gap: float = 0.0
    """Gap between largest and second-largest eigenvalue (graph connectivity)."""

    @property
    def n_gaps(self) -> int:
        return len(self.gaps)

    def summary(self) -> str:
        lines = [
            f"Topology Report",
            f"  Nodes:          {self.n_nodes}",
            f"  Edges:          {self.n_edges}",
            f"  Density:        {self.density:.4f}",
            f"  Alpha:          {self.alpha}",
            f"  Spectral gap:   {self.spectral_gap:.6f}",
            f"  Structural gaps: {self.n_gaps}",
        ]
        for i, gap in enumerate(self.gaps[:5]):
            lines.append(
                f"  Gap {i+1}: λ = {gap.eigenvalue:.6f}, "
                f"top nodes: {gap.node_indices[:5]}"
            )
        return "\n".join(lines)

    def to_json(self, path: str | Path) -> None:
        data = {
            "n_nodes": self.n_nodes,
            "n_edges": self.n_edges,
            "alpha": self.alpha,
            "eigenvalues": [float(v) for v in self.eigenvalues],
            "gaps": [g.to_dict() for g in self.gaps],
            "density": float(self.density),
            "spectral_gap": float(self.spectral_gap),
        }
        Path(path).write_text(json.dumps(data, indent=2))


# ---------------------------------------------------------------------------
# Graph Builder
# ---------------------------------------------------------------------------

class GraphBuilder:
    """Construct sparse adjacency and similarity matrices from edge lists."""

    @staticmethod
    def from_edge_list(
        n_nodes: int,
        edges: list[tuple[int, int, float]],
    ) -> sparse.csr_matrix:
        """Build a weighted adjacency matrix from (src, dst, weight) tuples."""
        rows, cols, weights = [], [], []
        for src, dst, w in edges:
            rows.append(src)
            cols.append(dst)
            weights.append(w)
        return sparse.csr_matrix(
            (weights, (rows, cols)), shape=(n_nodes, n_nodes)
        )

    @staticmethod
    def cosine_similarity_matrix(
        features: np.ndarray,
    ) -> sparse.csr_matrix:
        """Build a sparse cosine similarity matrix from node feature vectors.

        Args:
            features: (n_nodes, n_features) array of node embeddings/metadata.

        Returns:
            Sparse cosine similarity matrix.
        """
        norms = np.linalg.norm(features, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # avoid div-by-zero
        normalized = features / norms
        sim = normalized @ normalized.T
        # Zero out self-similarity and very weak connections
        np.fill_diagonal(sim, 0)
        sim[sim < 0.01] = 0
        return sparse.csr_matrix(sim)

    @staticmethod
    def from_citation_graph(
        documents: list[dict],
        id_key: str = "id",
        ref_key: str = "references",
    ) -> tuple[int, sparse.csr_matrix, dict[str, int]]:
        """Build adjacency matrix from a citation graph.

        Args:
            documents: List of dicts with 'id' and 'references' fields.
            id_key: Key for document identifier.
            ref_key: Key for list of referenced document IDs.

        Returns:
            (n_nodes, adjacency_matrix, id_to_index)
        """
        id_to_idx: dict[str, int] = {}
        for doc in documents:
            if doc[id_key] not in id_to_idx:
                id_to_idx[doc[id_key]] = len(id_to_idx)

        n = len(id_to_idx)
        rows, cols = [], []
        for doc in documents:
            src = id_to_idx[doc[id_key]]
            for ref_id in doc.get(ref_key, []):
                if ref_id in id_to_idx:
                    rows.append(src)
                    cols.append(id_to_idx[ref_id])

        data = np.ones(len(rows), dtype=np.float64)
        adj = sparse.csr_matrix((data, (rows, cols)), shape=(n, n))
        return n, adj, id_to_idx


# ---------------------------------------------------------------------------
# Spectral Analyzer
# ---------------------------------------------------------------------------

class SpectralTopologyAnalyzer:
    """Detect structural holes in directed graphs via eigenvalue decomposition.

    The combined matrix C = A + α·S merges the explicit adjacency structure
    with metadata similarity. Negative eigenvalues of C reveal topological
    gaps — locations where edges should exist to maintain structural cohesion
    but are absent from the observed network.
    """

    def __init__(self, alpha: float = 0.3, top_k_nodes: int = 10):
        """
        Args:
            alpha: Weight for the similarity matrix S in C = A + α·S.
                   Higher values prioritize metadata similarity over
                   explicit graph structure. Default 0.3.
            top_k_nodes: Number of top-contributing nodes to report per gap.
        """
        self.alpha = alpha
        self.top_k_nodes = top_k_nodes

    def analyze(
        self,
        adjacency: sparse.csr_matrix,
        similarity: Optional[sparse.csr_matrix] = None,
        n_eigenvalues: Optional[int] = None,
    ) -> TopologyReport:
        """Run spectral analysis on the graph.

        Args:
            adjacency: Sparse weighted adjacency matrix (n × n).
            similarity: Optional sparse similarity matrix (n × n).
                        If None, only the adjacency structure is analyzed.
            n_eigenvalues: Number of eigenvalues to compute.
                           If None, computes min(n, 50).

        Returns:
            TopologyReport with eigenvalues, gaps, and metrics.
        """
        n = adjacency.shape[0]
        if n_eigenvalues is None:
            n_eigenvalues = min(n, 50)

        # Build combined matrix C = A + α·S
        C = adjacency.astype(np.float64).tocsc()
        if similarity is not None:
            assert similarity.shape == adjacency.shape, "Matrix shape mismatch"
            C = C + self.alpha * similarity.astype(np.float64).tocsc()

        # Compute eigenvalues using sparse solver (ARPACK)
        # We ask for more eigenvalues than we need to capture negatives
        k = min(n_eigenvalues, n - 2)
        if k < 1:
            k = 1

        try:
            eigenvalues, eigenvectors = sparse_linalg.eigs(
                C.astype(np.complex128), k=k, which="LM", tol=1e-6
            )
        except sparse_linalg.ArpackNoConvergence as e:
            eigenvalues, eigenvectors = e.eigenvalues, e.eigenvectors

        # Sort by real part descending
        idx = np.argsort(eigenvalues.real)[::-1]
        sorted_vals = eigenvalues.real[idx]
        sorted_vecs = eigenvectors.real[:, idx]

        # Find structural gaps (negative eigenvalues)
        gaps: list[StructuralGap] = []
        negative_mask = sorted_vals < 0

        for i in np.where(negative_mask)[0]:
            vec = np.abs(sorted_vecs[:, i])
            top_idx = np.argsort(vec)[::-1][: self.top_k_nodes]
            top_weights = vec[top_idx]

            gaps.append(
                StructuralGap(
                    eigenvalue=float(sorted_vals[i]),
                    eigenvector=sorted_vecs[:, i],
                    node_indices=top_idx.tolist(),
                    node_weights=top_weights.tolist(),
                )
            )

        # Compute graph metrics
        n_edges = int(adjacency.nnz)
        density = n_edges / (n * (n - 1)) if n > 1 else 0.0
        spectral_gap = float(sorted_vals[0] - sorted_vals[1]) if len(sorted_vals) > 1 else 0.0

        return TopologyReport(
            n_nodes=n,
            n_edges=n_edges,
            alpha=self.alpha,
            eigenvalues=sorted_vals,
            gaps=gaps,
            density=density,
            spectral_gap=spectral_gap,
        )


# ---------------------------------------------------------------------------
# Convenience — Quick Analysis from Edge List
# ---------------------------------------------------------------------------

def quick_analyze(
    edges: list[tuple[int, int, float]],
    n_nodes: int,
    alpha: float = 0.3,
) -> TopologyReport:
    """One-shot analysis from an edge list.

    Args:
        edges: List of (source, target, weight) tuples.
        n_nodes: Total number of nodes in the graph.
        alpha: Similarity weighting coefficient.

    Returns:
        TopologyReport
    """
    adj = GraphBuilder.from_edge_list(n_nodes, edges)
    analyzer = SpectralTopologyAnalyzer(alpha=alpha)
    return analyzer.analyze(adj)
