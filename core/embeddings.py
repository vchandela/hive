"""OpenAI embedding generation with caching and no-op fallback.

When --no-embeddings is set, the indexer skips this entirely.
When --embeddings-cache is set, embeddings are loaded from / saved to
a .npz file to avoid re-calling the API on every reindex.
"""

from __future__ import annotations

import numpy as np


def generate_embeddings(
    texts: list[str],
    model: str = "text-embedding-3-small",
) -> np.ndarray:
    """Call OpenAI embeddings API. Returns shape (len(texts), dim)."""
    try:
        import openai
    except ImportError:
        raise RuntimeError(
            "openai package is required for embeddings. "
            "Install it with: pip install openai"
        )

    client = openai.OpenAI()  # reads OPENAI_API_KEY from env

    batch_size = 100
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = client.embeddings.create(input=batch, model=model)
        for item in response.data:
            all_embeddings.append(item.embedding)

    return np.array(all_embeddings, dtype=np.float32)


def save_embeddings_cache(
    embeddings: np.ndarray,
    chunk_ids: list[str],
    path: str,
) -> None:
    np.savez(path, embeddings=embeddings, chunk_ids=np.array(chunk_ids))


def load_embeddings_cache(path: str) -> tuple[np.ndarray, list[str]]:
    data = np.load(path, allow_pickle=False)
    return data["embeddings"], data["chunk_ids"].tolist()
