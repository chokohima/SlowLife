"""
ChatMemory — ChromaDB + SQLite によるRAG管理
ユーザー名・タイムスタンプ付きでチャットを保存し
関連コンテキストを検索して返す
"""

import sqlite3
import time
import logging
from pathlib import Path
from typing import List, Optional

log = logging.getLogger("rag")

try:
    import chromadb
    CHROMA_OK = True
except ImportError:
    log.warning("chromadb未インストール。SQLiteフォールバックで動作")
    CHROMA_OK = False


class ChatMemory:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # SQLite（全チャットログ保存）
        self.db_path = self.base_dir / "chats.db"
        self._init_sqlite()

        # ChromaDB（ベクトル検索）
        if CHROMA_OK:
            self._client = chromadb.PersistentClient(
                path=str(self.base_dir / "chroma")
            )
            self._col = self._client.get_or_create_collection(
                "chats",
                metadata={"hnsw:space": "cosine"}
            )
            log.info("ChromaDB初期化完了")
        else:
            self._col = None

    def _init_sqlite(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_log (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    username  TEXT NOT NULL,
                    message   TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created   REAL NOT NULL
                )
            """)
            conn.commit()

    def add(self, username: str, message: str, timestamp: str):
        """チャットを保存しRAGに追加"""
        created = time.time()

        # SQLite保存
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO chat_log (username, message, timestamp, created)"
                " VALUES (?, ?, ?, ?)",
                (username, message, timestamp, created)
            )
            row_id = cur.lastrowid
            conn.commit()

        # ChromaDB追加
        if self._col is not None:
            doc_id = f"chat_{row_id}"
            doc    = f"[{timestamp}] {username}: {message}"
            meta   = {"username": username, "timestamp": timestamp, "created": created}
            try:
                self._col.add(documents=[doc], metadatas=[meta], ids=[doc_id])
            except Exception as e:
                log.warning(f"ChromaDB追加エラー: {e}")

        log.debug(f"RAG保存: {username} → {message[:40]}")

    def retrieve_context(self, query: str, k: int = 5) -> str:
        """クエリに関連するチャットをRAG検索して返す"""
        if self._col is not None:
            try:
                results = self._col.query(query_texts=[query], n_results=k)
                docs = results.get("documents", [[]])[0]
                return "\n".join(docs) if docs else ""
            except Exception as e:
                log.warning(f"ChromaDB検索エラー: {e}")

        # フォールバック: 最新k件
        return self._recent_context(k)

    def _recent_context(self, k: int) -> str:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT timestamp, username, message FROM chat_log"
                " ORDER BY created DESC LIMIT ?",
                (k,)
            ).fetchall()
        lines = [f"[{r[0]}] {r[1]}: {r[2]}" for r in reversed(rows)]
        return "\n".join(lines)

    def get_user_history(self, username: str, limit: int = 20) -> List[dict]:
        """特定ユーザーの発言履歴を返す"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT username, message, timestamp, created FROM chat_log"
                " WHERE username = ? ORDER BY created DESC LIMIT ?",
                (username, limit)
            ).fetchall()
        return [
            {"username": r[0], "message": r[1],
             "timestamp": r[2], "created": r[3]}
            for r in rows
        ]

    def stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM chat_log").fetchone()[0]
            users = conn.execute(
                "SELECT COUNT(DISTINCT username) FROM chat_log"
            ).fetchone()[0]
        return {"total_chats": total, "unique_users": users}
