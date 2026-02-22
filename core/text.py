"""Shared text preprocessing for indexer and searcher.

Both modules must tokenize text identically — differing pipelines
would cause BM25 term mismatches at query time.
"""

from __future__ import annotations

import re

STOP_WORDS = frozenset(
    "a an and are as at be but by for from has have he her his how i if in "
    "into is it its just me my no nor not of on or our own s she so some such "
    "than that the their them then there these they this to too us very was we "
    "were what when where which while who whom why will with would you your".split()
)


def tokenize(text: str) -> list[str]:
    """Lowercase → strip punctuation → split on whitespace → remove stop words."""
    cleaned = re.sub(r"[^a-z0-9]", " ", text.lower())
    return [t for t in cleaned.split() if t and t not in STOP_WORDS]
