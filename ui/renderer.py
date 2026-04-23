"""
Renderer — Pygame による SNES 風描画
タイルマップ・建物・村人・チャッピー・吹き出しを描く
"""

import pygame
import time
import math
from typing import Optional, List
from core.game_state import GameState, Building

# タイルカラーパレット（SNES風16色）
PALETTE = {
    0: (106, 168,  79),   # 草
    1: (180, 150, 100),   # 道
    2: ( 60, 120, 200),   # 水
    3: ( 40, 100,  40),   # 木
    9: (200, 180, 140),   # 建物ベース
}

# 建物カラー
BUILDING_COLORS = {
    "house":    (220, 80,  60),
    "tavern":   (180, 100, 40),
    "market":   (240, 200, 60),
    "church":   (180, 180, 220),
    "barracks": (100, 100, 120),
    "library":  (160, 100, 180),
    "castle":   (120, 120, 160),
}

TILE_SIZE = 32
CAMERA_SPEED = 200.0   # px/sec

# 吹き出し設定
BUBBLE_BG   = (255, 255, 230)
BUBBLE_BD   = (80, 80, 60)
BUBBLE_FONT_SIZE = 15


class SpeechBubble:
    def __init__(self, text: str, duration: float):
        self.text     = text
        self.duration = duration
        self.created  = time.time()

    @property
    def alpha(self) -> float:
        elapsed = time.time() - self.created
        if elapsed > self.duration - 0.5:
            return max(0.0, (self.duration - elapsed) / 0.5)
        return 1.0

    @property
    def expired(self) -> bool:
        return time.time() - self.created > self.duration


class Renderer:
    def __init__(self, screen: pygame.Surface, state: GameState):
        self.screen = screen
        self.state  = state
        self.W, self.H = screen.get_size()

        # カメラ
        self.cam_x = 0.0
        self.cam_y = 0.0

        # フォント（日本語対応）
        try:
            self.font_sm = pygame.font.SysFont("Yu Gothic", BUBBLE_FONT_SIZE)
            self.font_md = pygame.font.SysFont("Yu Gothic", 18)
        except Exception:
            self.font_sm = pygame.font.SysFont(None, BUBBLE_FONT_SIZE)
            self.font_md = pygame.font.SysFont(None, 18)

        # 吹き出しキュー
        self._bubbles: List[SpeechBubble] = []

        # アニメーションカウンタ
        self._t = 0.0

    def update(self, dt: float):
        self._t += dt
        # 期限切れ吹き出し削除
        self._bubbles = [b for b in self._bubbles if not b.expired]

        # カメラをチャッピーに緩やかに追随
        target_x = self.state.chappy_x - self.W / 2
        target_y = self.state.chappy_y - self.H / 2
        self.cam_x += (target_x - self.cam_x) * 0.02
        self.cam_y += (target_y - self.cam_y) * 0.02
        self.cam_x = max(0, self.cam_x)
        self.cam_y = max(0, self.cam_y)

    def show_speech_bubble(self, text: str, duration: float = 5.0):
        self._bubbles.append(SpeechBubble(text, duration))

    def draw(self):
        # タイルマップ
        self._draw_tilemap()
        # 建物
        for b in self.state.buildings:
            self._draw_building(b)
        # 村人
        for v in self.state.villagers:
            self._draw_villager(v)
        # チャッピー
        self._draw_chappy()
        # 吹き出し
        self._draw_bubbles()

    def _w2s(self, wx: float, wy: float):
        """ワールド座標 → スクリーン座標"""
        return int(wx - self.cam_x), int(wy - self.cam_y)

    def _draw_tilemap(self):
        if not self.state.tile_map:
            return
        for ty, row in enumerate(self.state.tile_map):
            for tx, tile_id in enumerate(row):
                sx, sy = self._w2s(tx * TILE_SIZE, ty * TILE_SIZE)
                if sx > self.W or sy > self.H or sx < -TILE_SIZE or sy < -TILE_SIZE:
                    continue
                color = PALETTE.get(tile_id, (80, 60, 80))
                # 水タイルはアニメーション
                if tile_id == 2:
                    wave = int(math.sin(self._t * 2 + tx * 0.5) * 5)
                    color = (max(0, color[0] + wave),
                             max(0, color[1]),
                             min(255, color[2] + wave))
                pygame.draw.rect(self.screen, color,
                                 (sx, sy, TILE_SIZE - 1, TILE_SIZE - 1))

    def _draw_building(self, b: Building):
        sx, sy = self._w2s(b.x * TILE_SIZE, b.y * TILE_SIZE)
        if sx > self.W or sy > self.H:
            return
        color = BUILDING_COLORS.get(b.type, (160, 140, 120))
        # 屋根
        pts = [(sx, sy + 16), (sx + 16, sy), (sx + 32, sy + 16)]
        pygame.draw.polygon(self.screen, color, pts)
        # 壁
        pygame.draw.rect(self.screen, (220, 200, 170),
                         (sx + 4, sy + 16, 24, 20))
        # ドア
        pygame.draw.rect(self.screen, (100, 60, 30),
                         (sx + 12, sy + 26, 8, 10))

    def _draw_villager(self, v):
        sx, sy = self._w2s(v.x, v.y)
        if sx < -16 or sy < -16 or sx > self.W or sy > self.H:
            return
        bob = int(math.sin(self._t * 4 + hash(v.id) * 0.3) * 2)
        # 体
        pygame.draw.rect(self.screen, (100, 160, 220),
                         (sx - 4, sy - 8 + bob, 8, 10))
        # 頭
        pygame.draw.circle(self.screen, (240, 200, 160),
                           (sx, sy - 12 + bob), 5)

    def _draw_chappy(self):
        sx, sy = self._w2s(self.state.chappy_x, self.state.chappy_y)
        bob = int(math.sin(self._t * 3) * 3)
        # 翼
        for dx in [-10, 10]:
            pygame.draw.ellipse(self.screen, (200, 230, 255),
                                (sx + dx - 4, sy - 10 + bob, 10, 6))
        # 体
        pygame.draw.ellipse(self.screen, (140, 220, 140),
                            (sx - 8, sy - 8 + bob, 16, 14))
        # 頭
        pygame.draw.circle(self.screen, (200, 240, 180),
                           (sx, sy - 14 + bob), 8)
        # 目
        eye_y = sy - 15 + bob
        pygame.draw.circle(self.screen, (40, 40, 80),  (sx - 3, eye_y), 2)
        pygame.draw.circle(self.screen, (40, 40, 80),  (sx + 3, eye_y), 2)

    def _draw_bubbles(self):
        if not self._bubbles:
            return
        bubble = self._bubbles[-1]   # 最新1件を表示
        alpha = bubble.alpha

        # テキストを折り返し
        words = bubble.text
        max_w = 300
        surf  = self.font_sm.render(words, True, (40, 40, 30))

        bx = int(self.state.chappy_x - self.cam_x) - 20
        by = int(self.state.chappy_y - self.cam_y) - 70
        pad = 6
        bw  = surf.get_width() + pad * 2
        bh  = surf.get_height() + pad * 2

        # 背景
        bg_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg_surf.fill((*BUBBLE_BG, int(alpha * 230)))
        pygame.draw.rect(bg_surf, (*BUBBLE_BD, int(alpha * 200)),
                         (0, 0, bw, bh), 1)
        self.screen.blit(bg_surf, (bx, by))

        # テキスト
        t_surf = self.font_sm.render(words, True, (40, 40, 30))
        t_surf.set_alpha(int(alpha * 255))
        self.screen.blit(t_surf, (bx + pad, by + pad))

        # しっぽ
        cx = int(self.state.chappy_x - self.cam_x)
        cy = int(self.state.chappy_y - self.cam_y) - 14
        pygame.draw.line(self.screen, BUBBLE_BD,
                         (bx + bw // 2, by + bh), (cx, cy), 1)
