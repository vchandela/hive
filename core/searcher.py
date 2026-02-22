"""Search engine: BM25, vector search, RRF fusion, dynamic-k, distraction flagging.

This is the core retrieval module.  The top-level `search()` function
orchestrates the pipeline: tokenize → BM25 / vector → fuse → dynamic-k
→ flag distractors → return ranked results.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass

import numpy as np

from core.embeddings import generate_embeddings
from core.store import HiveStore
from core.text import tokenize


@dataclass
class SearchResult:
    chunk_id: str
    doc_id: str
    score: float
    text_preview: str
    category: str
    bm25_rank: int = 0
    vector_rank: int = 0
    flagged: bool = False
    disagreement: float | None = None

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "score": round(self.score, 6),
            "text_preview": self.text_preview,
            "category": self.category,
            "bm25_rank": self.bm25_rank,
            "vector_rank": self.vector_rank,
            "flagged": self.flagged,
            "disagreement": (
                round(self.disagreement, 4) if self.disagreement is not None else None
            ),
        }


# ── BM25 ────────────────────────────────────────────────────────────

K1 = 1.2
B = 0.75


def bm25_search(
    query_tokens: list[str],
    store: HiveStore,
    allowed_ids: set[str] | None = None,
) -> list[tuple[str, float]]:
    """Score chunks by BM25.  Returns [(chunk_id, score)] descending."""
    N, avgdl = store.get_corpus_stats()
    if N == 0:
        return []

    df_map = store.get_term_stats(query_tokens)
    postings_map = store.get_postings_for_terms(query_tokens)

    # Pre-load chunk lengths to avoid N queries
    if allowed_ids is not None:
        chunks = [store.get_chunk_by_id(cid) for cid in allowed_ids]
        length_map = {c["id"]: c["char_length"] for c in chunks if c}
    else:
        all_chunks = store.get_all_chunks()
        length_map = {c["id"]: c["char_length"] for c in all_chunks}

    scores: dict[str, float] = {}

    for term in query_tokens:
        df = df_map.get(term, 0)
        if df == 0:
            continue
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1.0)
        for chunk_id, tf in postings_map.get(term, []):
            if allowed_ids is not None and chunk_id not in allowed_ids:
                continue
            dl = length_map.get(chunk_id, avgdl)
            numerator = tf * (K1 + 1)
            denominator = tf + K1 * (1 - B + B * dl / avgdl)
            scores[chunk_id] = scores.get(chunk_id, 0.0) + idf * numerator / denominator

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ── Vector Search ───────────────────────────────────────────────────


def _deserialize_embedding(data: bytes, dim: int = 1536) -> np.ndarray:
    return np.array(struct.unpack(f"{dim}f", data), dtype=np.float32)


def vector_search(
    query_text: str,
    store: HiveStore,
    allowed_ids: set[str] | None = None,
) -> list[tuple[str, float]]:
    """Score chunks by cosine similarity to query embedding.

    Returns empty list if no embeddings are stored (indexed with --no-embeddings).
    """
    all_chunks = store.get_all_chunks()
    ids: list[str] = []
    embeddings: list[np.ndarray] = []

    for chunk in all_chunks:
        if chunk["embedding"] is None:
            continue
        if allowed_ids is not None and chunk["id"] not in allowed_ids:
            continue
        ids.append(chunk["id"])
        embeddings.append(_deserialize_embedding(chunk["embedding"]))

    if not embeddings:
        return []

    query_emb = generate_embeddings([query_text])[0]

    emb_matrix = np.array(embeddings, dtype=np.float32)
    query_norm = np.linalg.norm(query_emb)
    if query_norm == 0:
        return []

    norms = np.linalg.norm(emb_matrix, axis=1)
    norms[norms == 0] = 1.0  # avoid division by zero
    cosine_scores = np.dot(emb_matrix, query_emb) / (norms * query_norm)

    results = list(zip(ids, cosine_scores.tolist()))
    return sorted(results, key=lambda x: x[1], reverse=True)


# ── Reciprocal Rank Fusion ──────────────────────────────────────────


def rrf_fuse(
    bm25_results: list[tuple[str, float]],
    vector_results: list[tuple[str, float]],
    rrf_k: int = 60,
) -> list[tuple[str, float, int, int]]:
    """Fuse two ranked lists via RRF.

    Returns [(chunk_id, rrf_score, bm25_rank, vector_rank)] descending.
    """
    bm25_rank_map = {cid: rank + 1 for rank, (cid, _) in enumerate(bm25_results)}
    vector_rank_map = {cid: rank + 1 for rank, (cid, _) in enumerate(vector_results)}

    all_ids = set(bm25_rank_map) | set(vector_rank_map)
    fallback_bm25 = len(bm25_results) + 1
    fallback_vector = len(vector_results) + 1

    fused: list[tuple[str, float, int, int]] = []
    for cid in all_ids:
        br = bm25_rank_map.get(cid, fallback_bm25)
        vr = vector_rank_map.get(cid, fallback_vector)
        score = 1.0 / (rrf_k + br) + 1.0 / (rrf_k + vr)
        fused.append((cid, score, br, vr))

    return sorted(fused, key=lambda x: x[1], reverse=True)


# ── Dynamic-k (gap-based cliff detection) ──────────────────────────


def apply_dynamic_k(
    results: list,
    gap_threshold_factor: float,
    min_results: int,
    max_results: int,
) -> list:
    """Cut results when the gap between consecutive scores exceeds
    gap_threshold_factor × running_mean_gap."""
    results = results[:max_results]

    if len(results) <= min_results:
        return results

    gap_sum = 0.0
    gap_count = 0

    for i in range(1, len(results)):
        gap = results[i - 1][1] - results[i][1]
        gap_sum += gap
        gap_count += 1
        running_mean = gap_sum / gap_count

        if (
            i >= min_results
            and running_mean > 0
            and gap > gap_threshold_factor * running_mean
        ):
            return results[:i]

    return results


# ── Distraction Flagging ────────────────────────────────────────────


def flag_distractors(
    results: list[SearchResult],
    disagreement_threshold: float,
) -> list[SearchResult]:
    """Flag results where BM25 and vector ranks disagree significantly."""
    for r in results:
        if r.bm25_rank > 0 and r.vector_rank > 0:
            max_rank = max(r.bm25_rank, r.vector_rank)
            r.disagreement = abs(r.bm25_rank - r.vector_rank) / max_rank
            if r.disagreement > disagreement_threshold:
                r.flagged = True
    return results


# ── Top-level search orchestrator ───────────────────────────────────


def search(query: str, config: dict, store: HiveStore) -> list[SearchResult]:
    """Run the full search pipeline for a query + config."""
    retrieval = config["retrieval"]
    method = retrieval["method"]
    top_k = retrieval["top_k"]
    rrf_k = retrieval.get("rrf_k", 60)
    dynamic_k_cfg = config.get("dynamic_k", {})
    filters = config.get("filters", {})
    distraction_cfg = config.get("distraction_detection", {})

    # Pre-filter by category
    allowed_ids: set[str] | None = None
    if filters:
        filtered_chunks = store.get_all_chunks(filters)
        allowed_ids = {c["id"] for c in filtered_chunks}

    # Run retrievers
    query_tokens = tokenize(query)

    bm25_results: list[tuple[str, float]] = []
    vector_results: list[tuple[str, float]] = []

    if method in ("keyword", "hybrid"):
        bm25_results = bm25_search(query_tokens, store, allowed_ids)

    if method in ("vector", "hybrid"):
        vector_results = vector_search(query, store, allowed_ids)

    # Fuse or single-source
    if method == "hybrid" and bm25_results and vector_results:
        fused = rrf_fuse(bm25_results, vector_results, rrf_k)
    elif method == "keyword":
        fused = [
            (cid, 1.0 / (rrf_k + rank + 1), rank + 1, 0)
            for rank, (cid, _) in enumerate(bm25_results)
        ]
    elif method == "vector":
        fused = [
            (cid, 1.0 / (rrf_k + rank + 1), 0, rank + 1)
            for rank, (cid, _) in enumerate(vector_results)
        ]
    else:
        # Fallback: whichever has results
        if bm25_results:
            fused = [
                (cid, 1.0 / (rrf_k + rank + 1), rank + 1, 0)
                for rank, (cid, _) in enumerate(bm25_results)
            ]
        elif vector_results:
            fused = [
                (cid, 1.0 / (rrf_k + rank + 1), 0, rank + 1)
                for rank, (cid, _) in enumerate(vector_results)
            ]
        else:
            fused = []

    # Limit to top_k
    fused = fused[:top_k]

    # Dynamic-k
    if dynamic_k_cfg.get("enabled", False):
        fused = apply_dynamic_k(
            fused,
            gap_threshold_factor=dynamic_k_cfg.get("gap_threshold_factor", 3.0),
            min_results=dynamic_k_cfg.get("min_results", 1),
            max_results=dynamic_k_cfg.get("max_results", top_k),
        )

    # Build SearchResult objects
    results: list[SearchResult] = []
    for chunk_id, score, bm25_rank, vector_rank in fused:
        chunk = store.get_chunk_by_id(chunk_id)
        if chunk is None:
            continue
        meta = json.loads(chunk["metadata_json"])
        results.append(
            SearchResult(
                chunk_id=chunk_id,
                doc_id=chunk["doc_id"],
                score=score,
                text_preview=chunk["text"][:150],
                category=meta.get("category", ""),
                bm25_rank=bm25_rank,
                vector_rank=vector_rank,
            )
        )

    # Distraction flagging (only meaningful for hybrid)
    if distraction_cfg.get("enabled", False) and method == "hybrid":
        results = flag_distractors(
            results,
            disagreement_threshold=distraction_cfg.get("disagreement_threshold", 0.7),
        )

    return results
