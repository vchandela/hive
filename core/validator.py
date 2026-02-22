"""Three-level config validation: syntactic, semantic, behavioral.

Syntactic = structure and types (like a compiler).
Semantic  = cross-field logical consistency.
Behavioral is handled by the deploy command (nUDCG regression gate).
"""

from __future__ import annotations

import json
from pathlib import Path

from core.store import HiveStore

VALID_METHODS = {"keyword", "vector", "hybrid"}


# ── Syntactic Validation ────────────────────────────────────────────

def validate_syntactic(config: dict) -> list[str]:
    """Check required fields and types.  Returns list of error strings."""
    errors: list[str] = []

    # Top-level required fields
    if not isinstance(config.get("name"), str) or not config["name"]:
        errors.append("'name' is required and must be a non-empty string.")
    if not isinstance(config.get("collection"), str) or not config["collection"]:
        errors.append("'collection' is required and must be a non-empty string.")

    # Retrieval block
    retrieval = config.get("retrieval")
    if not isinstance(retrieval, dict):
        errors.append("'retrieval' is required and must be an object.")
        return errors  # can't check children

    method = retrieval.get("method")
    if method not in VALID_METHODS:
        errors.append(f"'retrieval.method' must be one of {sorted(VALID_METHODS)}, got '{method}'.")

    top_k = retrieval.get("top_k")
    if not isinstance(top_k, int) or top_k < 1:
        errors.append("'retrieval.top_k' must be a positive integer.")

    rrf_k = retrieval.get("rrf_k")
    if not isinstance(rrf_k, int) or rrf_k < 1:
        errors.append("'retrieval.rrf_k' must be a positive integer.")

    # Dynamic-k block
    dk = config.get("dynamic_k")
    if isinstance(dk, dict):
        if not isinstance(dk.get("enabled"), bool):
            errors.append("'dynamic_k.enabled' must be a boolean.")
        gtf = dk.get("gap_threshold_factor")
        if gtf is not None and (not isinstance(gtf, (int, float)) or gtf <= 0):
            errors.append("'dynamic_k.gap_threshold_factor' must be a positive number.")
        mn = dk.get("min_results")
        if mn is not None and (not isinstance(mn, int) or mn < 1):
            errors.append("'dynamic_k.min_results' must be an integer >= 1.")
        mx = dk.get("max_results")
        if mx is not None and (not isinstance(mx, int) or mx < 1):
            errors.append("'dynamic_k.max_results' must be an integer >= 1.")

    # Filters block (optional, but must be dict)
    filters = config.get("filters")
    if filters is not None and not isinstance(filters, dict):
        errors.append("'filters' must be an object if provided.")

    # Distraction detection block
    dd = config.get("distraction_detection")
    if isinstance(dd, dict):
        if not isinstance(dd.get("enabled"), bool):
            errors.append("'distraction_detection.enabled' must be a boolean.")
        dt = dd.get("disagreement_threshold")
        if dt is not None and (not isinstance(dt, (int, float)) or dt < 0 or dt > 1):
            errors.append("'distraction_detection.disagreement_threshold' must be a float between 0 and 1.")

    return errors


# ── Semantic Validation ─────────────────────────────────────────────

def validate_semantic(
    config: dict,
    available_categories: list[str],
) -> list[str]:
    """Check cross-field logical consistency."""
    errors: list[str] = []

    method = config.get("retrieval", {}).get("method", "")
    dd = config.get("distraction_detection", {})

    if dd.get("enabled") and method != "hybrid":
        errors.append(
            f"'distraction_detection.enabled' is true but 'retrieval.method' is '{method}'. "
            "Distraction detection requires 'method: hybrid' because it measures "
            "disagreement between keyword and vector rankings. Set 'method' to 'hybrid' "
            "or disable distraction detection."
        )

    dk = config.get("dynamic_k", {})
    mn = dk.get("min_results", 1)
    mx = dk.get("max_results", 10)
    if isinstance(mn, int) and isinstance(mx, int) and mn > mx:
        errors.append(
            f"'dynamic_k.min_results' ({mn}) > 'dynamic_k.max_results' ({mx}). "
            "min_results must be <= max_results."
        )

    # Check filter values against known categories
    filters = config.get("filters", {})
    if "category" in filters:
        cat_values = filters["category"]
        if isinstance(cat_values, list):
            unknown = [v for v in cat_values if v not in available_categories]
            if unknown:
                errors.append(
                    f"Unknown category filter values: {unknown}. "
                    f"Available categories: {sorted(available_categories)}."
                )

    return errors


# ── Top-level validate ──────────────────────────────────────────────

def validate_config(
    config_path: str,
    store: HiveStore,
) -> tuple[bool, list[str]]:
    """Run syntactic + semantic validation on a config file.

    Returns (passed, errors).
    """
    path = Path(config_path)
    try:
        config = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]
    except FileNotFoundError:
        return False, [f"Config file not found: {config_path}"]

    # Syntactic
    syn_errors = validate_syntactic(config)
    if syn_errors:
        return False, syn_errors

    # Semantic — need available categories from indexed data
    chunks = store.get_all_chunks()
    categories = set()
    for c in chunks:
        try:
            meta = json.loads(c["metadata_json"])
            if "category" in meta:
                categories.add(meta["category"])
        except (json.JSONDecodeError, KeyError):
            pass
    available_categories = sorted(categories)

    sem_errors = validate_semantic(config, available_categories)
    if sem_errors:
        return False, sem_errors

    return True, []
