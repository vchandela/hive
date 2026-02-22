"""Evaluator: UDCG scoring, config evaluation, and config comparison.

UDCG (Utility-Discounted Cumulative Gain) assigns:
  +1 to relevant documents
  -1 to distractors (look right, are wrong)
   0 to irrelevant documents
Each weighted by 1/log2(rank+1) — earlier ranks matter more.

Document-level dedup: if a doc produces multiple chunks, only the
highest-ranked chunk contributes.  Subsequent chunks from the same
doc get utility = 0.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from core.searcher import SearchResult, search
from core.store import HiveStore


def compute_udcg(
    results: list[SearchResult],
    golden_query: dict,
    k: int = 10,
) -> dict:
    """Compute UDCG@k for a single query's results against golden labels.

    Returns dict with nudcg, udcg, ideal_udcg, precision_at_k, distractor_count.
    """
    relevant_docs = set(golden_query.get("relevant", []))
    distractor_docs = set(golden_query.get("distractors", []))

    seen_docs: set[str] = set()
    udcg = 0.0
    relevant_in_top_k = 0
    distractor_count = 0
    position = 0

    for r in results[:k]:
        position += 1
        doc_id = r.doc_id

        # Document-level dedup: skip if already scored this doc
        if doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)

        if doc_id in relevant_docs:
            utility = 1.0
            relevant_in_top_k += 1
        elif doc_id in distractor_docs:
            utility = -1.0
            distractor_count += 1
        else:
            utility = 0.0

        discount = 1.0 / math.log2(position + 1)
        udcg += utility * discount

    # Ideal UDCG: all relevant docs at the top
    ideal_udcg = 0.0
    for i in range(1, len(relevant_docs) + 1):
        ideal_udcg += 1.0 / math.log2(i + 1)

    nudcg = udcg / ideal_udcg if ideal_udcg > 0 else 0.0

    return {
        "nudcg": round(nudcg, 4),
        "udcg": round(udcg, 4),
        "ideal_udcg": round(ideal_udcg, 4),
        "precision_at_k": round(relevant_in_top_k / k, 4) if k > 0 else 0.0,
        "distractor_count": distractor_count,
    }


def evaluate_config(
    config_path: str,
    golden_path: str,
    store: HiveStore,
) -> dict:
    """Evaluate a config against all golden queries.

    Returns {per_query: [...], aggregate: {nudcg, precision, total_distractors}}.
    """
    config = json.loads(Path(config_path).read_text())
    golden = json.loads(Path(golden_path).read_text())

    per_query: list[dict] = []
    total_nudcg = 0.0
    total_precision = 0.0
    total_distractors = 0

    for gq in golden["queries"]:
        results = search(gq["query"], config, store)
        metrics = compute_udcg(results, gq, k=config["retrieval"]["top_k"])
        metrics["query"] = gq["query"]

        per_query.append(metrics)
        total_nudcg += metrics["nudcg"]
        total_precision += metrics["precision_at_k"]
        total_distractors += metrics["distractor_count"]

        store.insert_eval_result(
            config_name=config["name"],
            query=gq["query"],
            metrics_json=json.dumps(metrics),
        )

    n = len(golden["queries"])
    aggregate = {
        "nudcg": round(total_nudcg / n, 4) if n else 0.0,
        "precision": round(total_precision / n, 4) if n else 0.0,
        "total_distractors": total_distractors,
    }

    return {"per_query": per_query, "aggregate": aggregate}


def compare_configs(
    config_a_path: str,
    config_b_path: str,
    golden_path: str,
    store: HiveStore,
) -> dict:
    """Compare two configs side by side.

    Returns {config_a: eval, config_b: eval, deltas: per_query, config_diff: {...}}.
    """
    eval_a = evaluate_config(config_a_path, golden_path, store)
    eval_b = evaluate_config(config_b_path, golden_path, store)

    deltas: list[dict] = []
    for qa, qb in zip(eval_a["per_query"], eval_b["per_query"]):
        deltas.append({
            "query": qa["query"],
            "nudcg_a": qa["nudcg"],
            "nudcg_b": qb["nudcg"],
            "delta": round(qb["nudcg"] - qa["nudcg"], 4),
            "distractors_a": qa["distractor_count"],
            "distractors_b": qb["distractor_count"],
        })

    # Config diff: find fields that differ
    config_a = json.loads(Path(config_a_path).read_text())
    config_b = json.loads(Path(config_b_path).read_text())
    config_diff = _diff_dicts(config_a, config_b)

    return {
        "config_a": eval_a,
        "config_b": eval_b,
        "deltas": deltas,
        "config_diff": config_diff,
        "aggregate_delta": {
            "nudcg": round(eval_b["aggregate"]["nudcg"] - eval_a["aggregate"]["nudcg"], 4),
            "distractors": eval_b["aggregate"]["total_distractors"] - eval_a["aggregate"]["total_distractors"],
        },
    }


def _diff_dicts(a: dict, b: dict, prefix: str = "") -> list[dict]:
    """Find fields that differ between two nested dicts."""
    diffs: list[dict] = []
    all_keys = sorted(set(list(a.keys()) + list(b.keys())))

    for key in all_keys:
        path = f"{prefix}.{key}" if prefix else key
        val_a = a.get(key)
        val_b = b.get(key)

        if isinstance(val_a, dict) and isinstance(val_b, dict):
            diffs.extend(_diff_dicts(val_a, val_b, path))
        elif val_a != val_b:
            diffs.append({"field": path, "a": val_a, "b": val_b})

    return diffs
