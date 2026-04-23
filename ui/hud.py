"""
HUD — ゲーム内ステータスバー
YouTubeの数値を村の言葉に翻訳して表示する
"""

import pygame
import time
from core.game_state import GameState

# HUDカラー
HUD_BG     = (10, 8, 20, 200)
HUD_TEXT   = (230, 215, 180)
HUD_ACCENT = (255, 210, 80)
HUD_RED    = (220, 80, 60)
HUD_GREEN  = (80, 200, 120)
BAR_BG     = (40, 35, 60)
BAR_FG     = (80, 200, 120)


class HUD:
    def __init__(self, screen: pygame.Surface, state: GameState):
        self.screen = screen
        self.state  = state
        self.W, self.H = screen.get_size()
        self._debug = False

        try:
            self.font_md = pygame.font.SysFont("Yu Gothic", 15)
            self.font_sm = pygame.font.SysFont("Yu Gothic", 12)
            self.font_lg = pygame.font.SysFont("Yu Gothic", 20)
        except Exception:
            self.font_md = pygame.font.SysFont(None, 15)
            self.font_sm = pygame.font.SysFont(None, 12)
            self.font_lg = pygame.font.SysFont(None, 20)

    def toggle_debug(self):
        self._debug = not self._debug

    def draw(self):
        self._draw_top_bar()
        self._draw_status_panel()
        if self._debug:
            self._draw_debug()

    # ─── 上部タイトルバー ──────────────────────────────
    def _draw_top_bar(self):
        s   = self.state
        bar = pygame.Surface((self.W, 28), pygame.SRCALPHA)
        bar.fill(HUD_BG)
        self.screen.blit(bar, (0, 0))

        # 村の名前
        title = self.font_lg.render("🏡 チャッピーの村", True, HUD_ACCENT)
        self.screen.blit(title, (8, 4))

        # 日付・季節
        season_jp = {"spring": "春", "summer": "夏",
                     "autumn": "秋", "winter": "冬"}
        day_str = f"第{s.day}日 / {season_jp.get(s.season, s.season)}"
        day_surf = self.font_md.render(day_str, True, HUD_TEXT)
        self.screen.blit(day_surf, (self.W // 2 - day_surf.get_width() // 2, 6))

        # 配信中バッジ
        live = self.font_sm.render("● LIVE配信中", True, HUD_RED)
        self.screen.blit(live, (self.W - live.get_width() - 10, 8))

    # ─── 右側ステータスパネル ──────────────────────────
    def _draw_status_panel(self):
        s   = self.state
        pw  = 200
        ph  = 200
        px  = self.W - pw - 6
        py  = 36

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill(HUD_BG)
        self.screen.blit(panel, (px, py))

        # ヘッダー
        hdr = self.font_sm.render("─ 村の状態 ─", True, HUD_ACCENT)
        self.screen.blit(hdr, (px + (pw - hdr.get_width()) // 2, py + 4))

        items = [
            ("村人の数",        f"{s.villager_count} 人",       None),
            ("村の評判",        f"{s.subscriber_count} 人",     None),
            ("旅人の訪問数",    f"{s.view_count:,}",            None),
            ("人気度",          f"{s.like_count:,}",            None),
            ("村会議の発言",    f"{s.chat_count:,}",            None),
        ]
        for i, (label, value, _) in enumerate(items):
            y = py + 24 + i * 22
            l_surf = self.font_sm.render(label, True, HUD_TEXT)
            v_surf = self.font_sm.render(value, True, HUD_ACCENT)
            self.screen.blit(l_surf, (px + 6, y))
            self.screen.blit(v_surf, (px + pw - v_surf.get_width() - 6, y))

        # 繁栄度バー
        bar_y = py + 135
        self._draw_bar("繁栄度", s.prosperity, 500, px + 6, bar_y, pw - 12, HUD_ACCENT)
        self._draw_bar("文化力", s.culture,    200, px + 6, bar_y + 22, pw - 12, (160, 120, 255))
        self._draw_bar("防衛力", s.defense,    100, px + 6, bar_y + 44, pw - 12, HUD_RED)

    def _draw_bar(self, label: str, value: float, max_val: float,
                  x: int, y: int, width: int, color: tuple):
        l_surf = self.font_sm.render(label, True, HUD_TEXT)
        self.screen.blit(l_surf, (x, y))

        bx   = x + 40
        bw   = width - 45
        fill = int(bw * min(value / max_val, 1.0))
        pygame.draw.rect(self.screen, BAR_BG,  (bx, y + 2, bw, 10))
        if fill > 0:
            pygame.draw.rect(self.screen, color, (bx, y + 2, fill, 10))
        pygame.draw.rect(self.screen, HUD_TEXT, (bx, y + 2, bw, 10), 1)

    # ─── デバッグ情報 ──────────────────────────────────
    def _draw_debug(self):
        s = self.state
        lines = [
            f"FPS: (see clock)",
            f"buildings: {len(s.buildings)}",
            f"villagers: {len(s.villagers)}",
            f"session: #{s.session_count}",
            f"last_saved: {time.strftime('%H:%M:%S', time.localtime(s.last_saved))}",
        ]
        for i, line in enumerate(lines):
            surf = self.font_sm.render(line, True, (180, 255, 180))
            self.screen.blit(surf, (8, self.H - 100 + i * 16))
