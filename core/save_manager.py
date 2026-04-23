"""
SaveManager — SQLite + JSON によるオートセーブ・リストア
起動時に最新セーブを自動ロードし、クラッシュ前の状態に復帰
"""

import json
import time
import logging
import sqlite3
from pathlib import Path
from core.game_state import GameState

log = logging.getLogger("save")


class SaveManager:
    def __init__(self, save_dir: str):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.save_dir / "village.db"
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saves (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    label     TEXT DEFAULT 'auto',
                    data      TEXT NOT NULL
                )
            """)
            conn.commit()

    def save(self, state: GameState, label: str = "auto") -> int:
        state.last_saved = time.time()
        data_json = json.dumps(state.to_dict(), ensure_ascii=False)
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO saves (timestamp, label, data) VALUES (?, ?, ?)",
                (state.last_saved, label, data_json)
            )
            save_id = cur.lastrowid
            conn.commit()

        # 古いオートセーブを30件を超えたら削除
        self._prune_auto_saves(keep=30)
        log.info(f"セーブ完了 id={save_id} label={label}")
        return save_id

    def load_latest(self) -> GameState:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM saves ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
        if row is None:
            log.info("セーブデータなし。新規ゲーム開始")
            return GameState()
        state = GameState.from_dict(json.loads(row[0]))
        state.session_count += 1
        log.info(f"ロード完了 村の日数={state.day} 繁栄度={state.prosperity:.1f}")
        return state

    def load_or_new(self) -> GameState:
        try:
            return self.load_latest()
        except Exception as e:
            log.error(f"ロード失敗: {e} → 新規ゲームで開始")
            return GameState()

    def _prune_auto_saves(self, keep: int = 30):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM saves
                WHERE label = 'auto'
                  AND id NOT IN (
                    SELECT id FROM saves
                    WHERE label = 'auto'
                    ORDER BY timestamp DESC
                    LIMIT ?
                  )
            """, (keep,))
            conn.commit()

    def list_saves(self):
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, timestamp, label FROM saves ORDER BY timestamp DESC"
            ).fetchall()
        return [{"id": r[0], "timestamp": r[1], "label": r[2]} for r in rows]
