"""
VillageEngine — 村の成長ロジック
チャット/リアクションを受けて建物・人口が増減する
"""

import random
import math
import time
import uuid
from typing import Optional

from core.game_state import GameState, Building, Villager

# 建物タイプ定義：必要繁栄度 / 文化要件 / ボーナス
BUILDING_DEFS = {
    "house":    {"prosperity": 5,   "culture": 0,   "def": 0,  "culture_bonus": 0,   "def_bonus": 0},
    "tavern":   {"prosperity": 20,  "culture": 3,   "def": 0,  "culture_bonus": 2,   "def_bonus": 0},
    "market":   {"prosperity": 30,  "culture": 5,   "def": 0,  "culture_bonus": 1,   "def_bonus": 0},
    "church":   {"prosperity": 50,  "culture": 10,  "def": 0,  "culture_bonus": 5,   "def_bonus": 0},
    "barracks": {"prosperity": 40,  "culture": 5,   "def": 5,  "culture_bonus": 0,   "def_bonus": 5},
    "library":  {"prosperity": 80,  "culture": 20,  "def": 0,  "culture_bonus": 10,  "def_bonus": 0},
    "castle":   {"prosperity": 200, "culture": 50,  "def": 20, "culture_bonus": 5,   "def_bonus": 20},
}

# タイルID
TILE_GRASS  = 0
TILE_ROAD   = 1
TILE_WATER  = 2
TILE_TREE   = 3

MAP_W, MAP_H = 40, 25   # タイル数

JOB_POOL = ["農夫", "商人", "衛兵", "職人", "聖職者", "旅人"]
NAME_POOL = [
    "タロウ", "ハナコ", "ケンジ", "ユキ", "アキラ", "ミドリ",
    "ソラ", "ヒロシ", "カオル", "ナオミ", "コウ", "レン",
]

# チャット1件あたりの成長量
CHAT_PROSPERITY_GAIN   = 0.5
CHAT_CULTURE_GAIN      = 0.1
REACTION_PROSPERITY_GAIN = 0.2


class VillageEngine:
    def __init__(self, state: GameState):
        self.state = state
        self._time_acc = 0.0
        self._day_length = 120.0   # 秒/ゲーム日

        if not self.state.tile_map:
            self._init_map()

    # ─── マップ初期化 ──────────────────────────────────
    def _init_map(self):
        m = [[TILE_GRASS] * MAP_W for _ in range(MAP_H)]

        # 川を生成
        cx = MAP_W // 2
        for y in range(MAP_H):
            m[y][cx] = TILE_WATER
            m[y][cx + 1] = TILE_WATER

        # 森エリア
        for _ in range(60):
            tx = random.randint(0, MAP_W - 1)
            ty = random.randint(0, MAP_H - 1)
            if m[ty][tx] == TILE_GRASS:
                m[ty][tx] = TILE_TREE

        # 道
        for x in range(MAP_W):
            m[MAP_H // 2][x] = TILE_ROAD

        self.state.tile_map = m

        # 初期建物（家）
        self._add_building("house", 10, 10, built_by="初期村人")

    # ─── イベントハンドラ ──────────────────────────────
    def on_chat_received(self, username: str, message: str):
        """チャット受信 → 村が少し成長"""
        s = self.state
        s.chat_count += 1
        s.prosperity = min(s.prosperity + CHAT_PROSPERITY_GAIN, 9999)
        s.culture    = min(s.culture    + CHAT_CULTURE_GAIN,    9999)

        # 一定確率で建物追加
        if random.random() < 0.05:
            self._try_add_building(built_by=username)

        # 村人を少し歩かせる
        self._nudge_villagers()

    def on_reaction_received(self, reaction_type: str, count: int):
        """リアクション受信 → 繁栄度UP"""
        gain = REACTION_PROSPERITY_GAIN * count
        self.state.prosperity = min(self.state.prosperity + gain, 9999)

    # ─── 定期更新 ──────────────────────────────────────
    def update(self, dt: float):
        self._time_acc += dt

        # ゲーム内時間進行
        if self._time_acc >= self._day_length:
            self._time_acc -= self._day_length
            self.state.day += 1
            self._advance_season()
            self._daily_growth()

        # 村人の動き
        for v in self.state.villagers:
            self._wander(v, dt)

        # チャッピーの動き
        self._move_chappy(dt)

    def _advance_season(self):
        seasons = ["spring", "summer", "autumn", "winter"]
        idx = seasons.index(self.state.season)
        if self.state.day % 30 == 0:
            self.state.season = seasons[(idx + 1) % 4]

    def _daily_growth(self):
        """毎ゲーム日の自然成長"""
        s = self.state
        # 村人数に応じた繁栄度自然増加
        natural = s.villager_count * 0.1
        s.prosperity = min(s.prosperity + natural, 9999)

        # 人口増加（建物数 > 村人数ならスポーン）
        house_count = sum(1 for b in s.buildings if b.type == "house")
        capacity    = house_count * 4
        if len(s.villagers) < capacity and len(s.villagers) < s.villager_count:
            self._spawn_villager()

    def _try_add_building(self, built_by: Optional[str] = None):
        """繁栄度に応じた建物を追加"""
        p = self.state.prosperity
        candidates = [t for t, d in BUILDING_DEFS.items()
                      if d["prosperity"] <= p and d["culture"] <= self.state.culture]
        if not candidates:
            return
        btype = random.choice(candidates)
        x = random.randint(2, MAP_W - 4)
        y = random.randint(2, MAP_H - 4)
        if self.state.tile_map[y][x] == TILE_GRASS:
            self._add_building(btype, x, y, built_by=built_by)

    def _add_building(self, btype: str, x: int, y: int,
                      built_by: Optional[str] = None) -> Building:
        b = Building(
            id=str(uuid.uuid4())[:8],
            type=btype, x=x, y=y,
            built_by=built_by,
        )
        self.state.buildings.append(b)
        self.state.tile_map[y][x] = 9   # 建物タイル
        d = BUILDING_DEFS[btype]
        self.state.culture  += d["culture_bonus"]
        self.state.defense  += d["def_bonus"]
        return b

    def _spawn_villager(self):
        if not self.state.buildings:
            return
        home = random.choice(self.state.buildings)
        v = Villager(
            id=str(uuid.uuid4())[:8],
            name=random.choice(NAME_POOL),
            job=random.choice(JOB_POOL),
            x=float(home.x * 32 + 16),
            y=float(home.y * 32 + 16),
            home_id=home.id,
        )
        self.state.villagers.append(v)

    def _wander(self, v: Villager, dt: float):
        speed = 20.0  # px/sec
        v.x += random.uniform(-1, 1) * speed * dt
        v.y += random.uniform(-1, 1) * speed * dt
        # 境界クランプ
        v.x = max(0, min(v.x, MAP_W * 32 - 32))
        v.y = max(0, min(v.y, MAP_H * 32 - 32))

    def _nudge_villagers(self):
        """チャット受信で村人がちょっとはしゃぐ"""
        for v in self.state.villagers:
            v.x += random.uniform(-5, 5)
            v.y += random.uniform(-5, 5)

    def _move_chappy(self, dt: float):
        s = self.state
        # ゆっくりふらつく
        s.chappy_x += math.sin(time.time() * 0.5) * 15 * dt
        s.chappy_y += math.cos(time.time() * 0.3) * 10 * dt
        s.chappy_x = max(16, min(s.chappy_x, MAP_W * 32 - 48))
        s.chappy_y = max(16, min(s.chappy_y, MAP_H * 32 - 48))
