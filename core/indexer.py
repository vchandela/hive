"""Indexer: reads markdown, chunks at H2 boundaries, builds BM25 postings,
generates embeddings, and stores everything in SQLite.
"""

from __future__ import annotations

import json
import re
import struct
from collections import Counter
from pathlib import Path

import numpy as np

from core.embeddings import generate_embeddings, load_embeddings_cache, save_embeddings_cache
from core.store import HiveStore
from core.text import tokenize


# ── Chunking ────────────────────────────────────────────────────────

def _slugify(heading: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")


def chunk_markdown(doc_path: str, documents_dir: str, heading_level: int = 2) -> list[dict]:
    """Split a markdown file into chunks at H2 boundaries."""
    path = Path(doc_path)
    text = path.read_text(encoding="utf-8")

    rel_path = str(path.relative_to(documents_dir))
    category = Path(rel_path).parts[0]  # e.g. "api-docs"
    title = path.stem  # e.g. "authentication"

    prefix = "#" * heading_level + " "
    lines = text.split("\n")

    sections: list[tuple[str, list[str]]] = []
    current_heading = title
    current_lines: list[str] = []

    for line in lines:
        if line.startswith(prefix):
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = line[len(prefix) :].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, current_lines))

    if not sections:
        sections = [(title, lines)]

    chunks = []
    for heading, section_lines in sections:
        chunk_text = "\n".join(section_lines).strip()
        if not chunk_text:
            continue
        slug = _slugify(heading)
        chunk_id = f"{rel_path}#{slug}"
        chunks.append(
            {
                "id": chunk_id,
                "doc_id": rel_path,
                "text": chunk_text,
                "metadata": {"category": category, "title": title},
                "heading": heading,
            }
        )

    return chunks


# ── BM25 Index Building ────────────────────────────────────────────

def build_postings(
    chunks: list[dict],
) -> tuple[list[tuple], list[tuple], tuple[int, float]]:
    """Build BM25 inverted index structures from chunks.

    Returns (postings, term_stats, corpus_stats) where:
      postings  = [(term, chunk_id, tf), ...]
      term_stats = [(term, df), ...]
      corpus_stats = (total_chunks, avg_chunk_length)
    """
    postings: list[tuple] = []
    doc_freq: Counter[str] = Counter()
    total_tokens = 0

    for chunk in chunks:
        tokens = tokenize(chunk["text"])
        total_tokens += len(tokens)
        tf_counts = Counter(tokens)

        seen_terms: set[str] = set()
        for term, count in tf_counts.items():
            postings.append((term, chunk["id"], float(count)))
            if term not in seen_terms:
                doc_freq[term] += 1
                seen_terms.add(term)

    total_chunks = len(chunks)
    avg_chunk_length = total_tokens / total_chunks if total_chunks else 0.0

    term_stats = [(term, df) for term, df in doc_freq.items()]
    return postings, term_stats, (total_chunks, avg_chunk_length)


# ── Embedding helpers ───────────────────────────────────────────────

def _serialize_embedding(emb: np.ndarray) -> bytes:
    return struct.pack(f"{len(emb)}f", *emb.tolist())


def _deserialize_embedding(data: bytes, dim: int = 1536) -> np.ndarray:
    return np.array(struct.unpack(f"{dim}f", data), dtype=np.float32)


# ── Main entry point ───────────────────────────────────────────────

def index_collection(
    collection_path: str,
    store: HiveStore,
    force: bool = False,
    embeddings_cache: str | None = None,
    no_embeddings: bool = False,
) -> dict:
    """Index all documents in a collection into SQLite.

    Returns a summary dict with counts.
    """
    col = json.loads(Path(collection_path).read_text())
    documents_dir = col["documents_dir"]

    if force:
        store.delete_all_chunks()
        store.delete_all_postings()
        store.delete_all_term_stats()

    md_files = sorted(Path(documents_dir).rglob("*.md"))
    if not md_files:
        return {"documents": 0, "chunks": 0, "terms": 0}

    heading_level = col.get("chunking", {}).get("heading_level", 2)

    all_chunks: list[dict] = []
    for md_file in md_files:
        file_chunks = chunk_markdown(str(md_file), documents_dir, heading_level)
        all_chunks.extend(file_chunks)

    postings, term_stats, (total_chunks, avg_chunk_length) = build_postings(all_chunks)

    # Embeddings
    embeddings_array: np.ndarray | None = None
    chunk_ids_ordered = [c["id"] for c in all_chunks]

    if not no_embeddings:
        if embeddings_cache and Path(embeddings_cache).exists():
            embeddings_array, cached_ids = load_embeddings_cache(embeddings_cache)
            id_to_emb = dict(zip(cached_ids, embeddings_array))
            ordered = []
            missing_texts = []
            missing_indices = []
            for i, cid in enumerate(chunk_ids_ordered):
                if cid in id_to_emb:
                    ordered.append(id_to_emb[cid])
                else:
                    ordered.append(None)
                    missing_texts.append(all_chunks[i]["text"])
                    missing_indices.append(i)

            if missing_texts:
                new_embs = generate_embeddings(missing_texts)
                for j, idx in enumerate(missing_indices):
                    ordered[idx] = new_embs[j]

            embeddings_array = np.array(ordered, dtype=np.float32)
        else:
            texts = [c["text"] for c in all_chunks]
            embeddings_array = generate_embeddings(texts)

        if embeddings_cache:
            save_embeddings_cache(embeddings_array, chunk_ids_ordered, embeddings_cache)

    # Prepare rows for SQLite
    chunk_rows = []
    for i, chunk in enumerate(all_chunks):
        emb_bytes = None
        if embeddings_array is not None:
            emb_bytes = _serialize_embedding(embeddings_array[i])
        chunk_rows.append(
            {
                "id": chunk["id"],
                "doc_id": chunk["doc_id"],
                "text": chunk["text"],
                "metadata_json": json.dumps(chunk["metadata"]),
                "embedding": emb_bytes,
                "char_length": len(tokenize(chunk["text"])),
            }
        )

    store.insert_chunks(chunk_rows)
    store.insert_postings(postings)
    store.insert_term_stats(term_stats)
    store.upsert_corpus_stats(total_chunks, avg_chunk_length)

    return {
        "documents": len(md_files),
        "chunks": len(all_chunks),
        "terms": len(term_stats),
    }
