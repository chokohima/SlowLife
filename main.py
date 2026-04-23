"""
SNES Village Simulator - Main Controller
YouTube Live連動型 村づくりシミュレーター
"""

import pygame
import asyncio
import threading
import json
import time
import logging
from pathlib import Path

from core.game_state import GameState
from core.village_engine import VillageEngine
from core.save_manager import SaveManager
from ai.chappy import ChappyAI
from rag.chat_memory import ChatMemory
from ui.renderer import Renderer
from ui.hud import HUD
from music.generator import MusicGenerator
from utils.youtube_listener import YouTubeListener
from utils.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("data/village.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("main")

# ─── 画面設定 ─────────────────────────────────────────
SCREEN_W, SCREEN_H = 1280, 720
FPS = 30
SAVE_INTERVAL = 30          # 自動セーブ間隔（秒）


class VillageSimulator:
    def __init__(self):
        pygame.init()
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

        self.cfg = Config.load("data/config.json")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("🏡 チャッピーの村 - LIVE配信中")
        self.clock = pygame.time.Clock()

        # コアシステム
        self.state = GameState()
        self.save_mgr = SaveManager("data/saves/")
        self.state = self.save_mgr.load_or_new()

        self.village = VillageEngine(self.state)
        self.renderer = Renderer(self.screen, self.state)
        self.hud = HUD(self.screen, self.state)

        # AI / RAG
        self.rag = ChatMemory("data/rag/")
        self.chappy = ChappyAI(self.cfg.ollama_model, self.rag)

        # 音楽
        self.music = MusicGenerator()
        self.music.start()

        # YouTube連動
        self.yt = YouTubeListener(
            self.cfg.youtube_video_id,
            self.cfg.youtube_api_key,
            on_chat=self._on_chat,
            on_reaction=self._on_reaction,
        )

        # タイマー
        self._last_save = time.time()
        self._last_monologue = time.time()
        self._running = False

    # ─── YouTube イベントハンドラ ──────────────────────
    def _on_chat(self, username: str, message: str, timestamp: str):
        """チャットを受け取ったとき"""
        log.info(f"CHAT [{username}]: {message}")
        self.rag.add(username, message, timestamp)

        # 村の成長トリガー（チャット = 小成長）
        self.village.on_chat_received(username, message)

        # チャッピーが反応
        context = self.rag.retrieve_context(message, k=5)
        asyncio.run(self._chappy_reply(username, message, context))

    def _on_reaction(self, reaction_type: str, count: int):
        """リアクション（❤️等）を受け取ったとき"""
        log.info(f"REACTION: {reaction_type} x{count}")
        self.village.on_reaction_received(reaction_type, count)

    async def _chappy_reply(self, username: str, message: str, context: str):
        reply = await self.chappy.respond(username, message, context, self.state)
        self.renderer.show_speech_bubble(reply, duration=5.0)
        log.info(f"CHAPPY: {reply}")

    # ─── メインループ ──────────────────────────────────
    def run(self):
        self._running = True
        self.yt.start()

        # チャッピー独り言スレッド
        threading.Thread(target=self._monologue_loop, daemon=True).start()

        log.info("村シミュレーター開始")

        while self._running:
            dt = self.clock.tick(FPS) / 1000.0

            # イベント処理
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._running = False
                elif event.type == pygame.KEYDOWN:
                    self._handle_key(event.key)

            # ゲームロジック更新
            self.village.update(dt)
            self.renderer.update(dt)

            # 登録者数で人口同期（毎フレーム or 定期的に）
            self._sync_subscriber_count()

            # 描画
            self.screen.fill((20, 15, 30))
            self.renderer.draw()
            self.hud.draw()
            pygame.display.flip()

            # 自動セーブ
            now = time.time()
            if now - self._last_save > SAVE_INTERVAL:
                self.save_mgr.save(self.state)
                self._last_save = now
                log.info("自動セーブ完了")

        self._shutdown()

    def _monologue_loop(self):
        """チャッピーが一定間隔で独り言をつぶやく"""
        while self._running:
            interval = self.cfg.monologue_interval_sec
            time.sleep(interval)
            context = self.rag.retrieve_context("村の様子", k=3)
            monologue = asyncio.run(
                self.chappy.monologue(self.state, context)
            )
            self.renderer.show_speech_bubble(monologue, duration=4.0)
            log.info(f"独り言: {monologue}")

    def _sync_subscriber_count(self):
        """YouTube登録者数 → 村人数に変換"""
        subs = self.yt.get_subscriber_count()
        if subs is not None:
            self.state.subscriber_count = subs
            # 登録者100人 = 村人10人 (スケール調整可)
            self.state.villager_count = max(1, subs // self.cfg.sub_to_villager_ratio)

    def _handle_key(self, key):
        if key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
            self.save_mgr.save(self.state)
            log.info("手動セーブ")
        elif key == pygame.K_F1:
            self.hud.toggle_debug()

    def _shutdown(self):
        self.save_mgr.save(self.state)
        self.yt.stop()
        self.music.stop()
        pygame.quit()
        log.info("シャットダウン完了")


if __name__ == "__main__":
    sim = VillageSimulator()
    sim.run()
