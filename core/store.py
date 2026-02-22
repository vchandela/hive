"""SQLite storage layer for Hive.

Manages 6 tables: chunks, postings, term_stats, corpus_stats,
config_versions, eval_results.  All I/O is synchronous — the corpus
is small enough that async adds no value.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = "hive.db"


class HiveStore:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    # ── Schema ──────────────────────────────────────────────────────

    def _init_tables(self) -> None:
        stmts = [
            """CREATE TABLE IF NOT EXISTS chunks (
                id          TEXT PRIMARY KEY,
                doc_id      TEXT NOT NULL,
                text        TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                embedding   BLOB,
                char_length INTEGER NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS postings (
                term     TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                tf       REAL NOT NULL,
                PRIMARY KEY (term, chunk_id)
            )""",
            """CREATE TABLE IF NOT EXISTS term_stats (
                term TEXT PRIMARY KEY,
                df   INTEGER NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS corpus_stats (
                id               INTEGER PRIMARY KEY CHECK (id = 1),
                total_chunks     INTEGER NOT NULL,
                avg_chunk_length REAL    NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS config_versions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                version     TEXT NOT NULL,
                config_json TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deployed_at TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS eval_results (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                config_name  TEXT NOT NULL,
                query        TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        ]
        cur = self.conn.cursor()
        for stmt in stmts:
            cur.execute(stmt)
        self.conn.commit()

    # ── Chunks ──────────────────────────────────────────────────────

    def insert_chunks(self, chunks: list[dict]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO chunks (id, doc_id, text, metadata_json, embedding, char_length) "
            "VALUES (:id, :doc_id, :text, :metadata_json, :embedding, :char_length)",
            chunks,
        )
        self.conn.commit()

    def get_all_chunks(self, filters: dict | None = None) -> list[dict]:
        if filters:
            clauses, params = [], []
            for key, values in filters.items():
                placeholders = ",".join("?" for _ in values)
                clauses.append(f"json_extract(metadata_json, '$.{key}') IN ({placeholders})")
                params.extend(values)
            sql = "SELECT * FROM chunks WHERE " + " AND ".join(clauses)
            rows = self.conn.execute(sql, params).fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM chunks").fetchall()
        return [dict(r) for r in rows]

    def get_chunk_by_id(self, chunk_id: str) -> dict | None:
        row = self.conn.execute("SELECT * FROM chunks WHERE id = ?", (chunk_id,)).fetchone()
        return dict(row) if row else None

    def delete_all_chunks(self) -> None:
        self.conn.execute("DELETE FROM chunks")
        self.conn.commit()

    # ── Postings (BM25 inverted index) ─────────────────────────────

    def insert_postings(self, postings: list[tuple]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO postings (term, chunk_id, tf) VALUES (?, ?, ?)",
            postings,
        )
        self.conn.commit()

    def get_postings_for_terms(self, terms: list[str]) -> dict[str, list[tuple[str, float]]]:
        if not terms:
            return {}
        placeholders = ",".join("?" for _ in terms)
        rows = self.conn.execute(
            f"SELECT term, chunk_id, tf FROM postings WHERE term IN ({placeholders})",
            terms,
        ).fetchall()
        result: dict[str, list[tuple[str, float]]] = {}
        for row in rows:
            result.setdefault(row["term"], []).append((row["chunk_id"], row["tf"]))
        return result

    def delete_all_postings(self) -> None:
        self.conn.execute("DELETE FROM postings")
        self.conn.commit()

    # ── Term Stats ─────────────────────────────────────────────────

    def insert_term_stats(self, stats: list[tuple]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO term_stats (term, df) VALUES (?, ?)",
            stats,
        )
        self.conn.commit()

    def get_term_stats(self, terms: list[str]) -> dict[str, int]:
        if not terms:
            return {}
        placeholders = ",".join("?" for _ in terms)
        rows = self.conn.execute(
            f"SELECT term, df FROM term_stats WHERE term IN ({placeholders})",
            terms,
        ).fetchall()
        return {row["term"]: row["df"] for row in rows}

    def delete_all_term_stats(self) -> None:
        self.conn.execute("DELETE FROM term_stats")
        self.conn.commit()

    # ── Corpus Stats ───────────────────────────────────────────────

    def upsert_corpus_stats(self, total_chunks: int, avg_chunk_length: float) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO corpus_stats (id, total_chunks, avg_chunk_length) "
            "VALUES (1, ?, ?)",
            (total_chunks, avg_chunk_length),
        )
        self.conn.commit()

    def get_corpus_stats(self) -> tuple[int, float]:
        row = self.conn.execute("SELECT total_chunks, avg_chunk_length FROM corpus_stats WHERE id = 1").fetchone()
        if row is None:
            return (0, 0.0)
        return (row["total_chunks"], row["avg_chunk_length"])

    # ── Config Versions ────────────────────────────────────────────

    def insert_config_version(self, name: str, version: str, config_json: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO config_versions (name, version, config_json) VALUES (?, ?, ?)",
            (name, version, config_json),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def mark_deployed(self, config_id: int) -> None:
        self.conn.execute(
            "UPDATE config_versions SET deployed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (config_id,),
        )
        self.conn.commit()

    def get_active_config(self) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM config_versions WHERE deployed_at IS NOT NULL "
            "ORDER BY deployed_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    # ── Eval Results ───────────────────────────────────────────────

    def insert_eval_result(self, config_name: str, query: str, metrics_json: str) -> None:
        self.conn.execute(
            "INSERT INTO eval_results (config_name, query, metrics_json) VALUES (?, ?, ?)",
            (config_name, query, metrics_json),
        )
        self.conn.commit()

    def get_eval_results(self, config_name: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM eval_results WHERE config_name = ? ORDER BY created_at",
            (config_name,),
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Utilities ──────────────────────────────────────────────────

    def close(self) -> None:
        self.conn.close()
