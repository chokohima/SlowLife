"""
GameState — 村の全状態を一元管理するデータクラス
SQLite + JSONで永続化される
"""

import time
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional


@dataclass
class Building:
    id: str
    type: str          # "house", "tavern", "market", "church", "castle"...
    x: int
    y: int
    level: int = 1
    built_at: float = field(default_factory=time.time)
    built_by: Optional[str] = None   # チャットで贈られた場合はユーザー名


@dataclass
class Villager:
    id: str
    name: str
    job: str           # "farmer", "merchant", "guard"...
    x: float
    y: float
    home_id: Optional[str] = None
    mood: float = 1.0  # 0.0〜1.0


# ─── ステータス名マッピング（ゲーム内表示用） ─────────────────
STAT_LABELS = {
    "subscriber_count": "村の評判（登録者数）",
    "villager_count":   "村人の数",
    "view_count":       "旅人の訪問数（視聴数）",
    "like_count":       "村の人気度（高評価数）",
    "chat_count":       "村会議の発言数（チャット数）",
    "prosperity":       "繁栄度",
    "culture":          "文化レベル",
    "defense":          "防衛力",
}


@dataclass
class GameState:
    # ─── YouTube由来ステータス ─────────────────────────
    subscriber_count: int = 0
    villager_count: int   = 1
    view_count: int       = 0
    like_count: int       = 0
    chat_count: int       = 0

    # ─── 村ステータス ─────────────────────────────────
    prosperity: float  = 10.0     # 繁栄度
    culture: float     = 5.0      # 文化レベル
    defense: float     = 3.0      # 防衛力
    day: int           = 1        # 村の経過日数
    season: str        = "spring" # spring / summer / autumn / winter

    # ─── 建物・住人 ────────────────────────────────────
    buildings: List[Building] = field(default_factory=list)
    villagers: List[Villager] = field(default_factory=list)
    tile_map: List[List[int]] = field(default_factory=list)

    # ─── チャッピー状態 ─────────────────────────────────
    chappy_x: float    = 320.0
    chappy_y: float    = 240.0
    chappy_mood: str   = "happy"   # happy / neutral / excited / sleepy

    # ─── メタ ─────────────────────────────────────────
    created_at: float  = field(default_factory=time.time)
    last_saved: float  = field(default_factory=time.time)
    session_count: int = 0

    def display_stat(self, key: str) -> str:
        return STAT_LABELS.get(key, key)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "GameState":
        d["buildings"] = [Building(**b) for b in d.get("buildings", [])]
        d["villagers"] = [Villager(**v) for v in d.get("villagers", [])]
        return cls(**d)

    def summary(self) -> str:
        """チャッピーAIに渡す村の状態サマリー（日本語）"""
        return (
            f"現在の村の状態: 村人{self.villager_count}人、"
            f"繁栄度{self.prosperity:.1f}、文化レベル{self.culture:.1f}、"
            f"季節は{self.season}、{self.day}日目。"
            f"建物は{len(self.buildings)}棟。"
            f"評判（登録者数）: {self.subscriber_count}人。"
        )
