"""
YouTubeListener — YouTube Live Chat & 登録者数をポーリング
pytchat (チャット) + youtube-data-api (登録者数)
完全ローカル動作
"""

import threading
import time
import logging
from typing import Callable, Optional

log = logging.getLogger("youtube")

try:
    import pytchat
    PYTCHAT_OK = True
except ImportError:
    log.warning("pytchat未インストール。チャット機能はダミーモード")
    PYTCHAT_OK = False

try:
    from googleapiclient.discovery import build as yt_build
    YT_API_OK = True
except ImportError:
    log.warning("google-api-python-client未インストール。登録者数はダミーモード")
    YT_API_OK = False


class YouTubeListener:
    def __init__(
        self,
        video_id: str,
        api_key: str,
        on_chat:     Callable[[str, str, str], None] = None,
        on_reaction: Callable[[str, int], None]      = None,
    ):
        self.video_id    = video_id
        self.api_key     = api_key
        self.on_chat     = on_chat
        self.on_reaction = on_reaction

        self._running    = False
        self._subscriber_count: Optional[int] = None
        self._chat_thread = None
        self._sub_thread  = None

        # YouTube Data API クライアント
        if YT_API_OK and api_key:
            try:
                self._yt = yt_build("youtube", "v3", developerKey=api_key)
            except Exception as e:
                log.warning(f"YouTube API初期化失敗: {e}")
                self._yt = None
        else:
            self._yt = None

    def start(self):
        self._running = True
        self._chat_thread = threading.Thread(
            target=self._chat_loop, daemon=True)
        self._sub_thread = threading.Thread(
            target=self._subscriber_loop, daemon=True)
        self._chat_thread.start()
        self._sub_thread.start()
        log.info(f"YouTube Listener開始 video_id={self.video_id}")

    def stop(self):
        self._running = False

    def get_subscriber_count(self) -> Optional[int]:
        return self._subscriber_count

    # ─── チャットポーリング ────────────────────────────
    def _chat_loop(self):
        if not PYTCHAT_OK or not self.video_id:
            log.info("チャットダミーモード（pytchat未使用）")
            self._dummy_chat_loop()
            return

        while self._running:
            try:
                chat = pytchat.create(video_id=self.video_id)
                log.info("Live Chat接続成功")
                while self._running and chat.is_alive():
                    for item in chat.get().sync_items():
                        if self.on_chat:
                            self.on_chat(
                                item.author.name,
                                item.message,
                                item.datetime,
                            )
                    time.sleep(1)
            except Exception as e:
                log.error(f"Chat接続エラー: {e}")
                time.sleep(10)

    def _dummy_chat_loop(self):
        """開発用ダミーチャット（定期的にランダムメッセージ生成）"""
        DUMMY_USERS = ["旅人A", "冒険者B", "魔法使いC", "村人D"]
        DUMMY_MSGS  = [
            "こんにちは！", "村きれいだね", "チャッピーかわいい！",
            "がんばれ！", "ここ最高！", "また来るね", "応援してるよ",
        ]
        import random, datetime
        while self._running:
            time.sleep(random.uniform(8, 20))
            if self.on_chat:
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.on_chat(
                    random.choice(DUMMY_USERS),
                    random.choice(DUMMY_MSGS),
                    ts,
                )

    # ─── 登録者数ポーリング ───────────────────────────
    def _subscriber_loop(self):
        while self._running:
            if self._yt:
                try:
                    # 動画のチャンネルIDを取得してから登録者数を取得
                    vid_resp = self._yt.videos().list(
                        part="snippet", id=self.video_id
                    ).execute()
                    if vid_resp.get("items"):
                        ch_id = vid_resp["items"][0]["snippet"]["channelId"]
                        ch_resp = self._yt.channels().list(
                            part="statistics", id=ch_id
                        ).execute()
                        if ch_resp.get("items"):
                            subs = int(ch_resp["items"][0]["statistics"]
                                       .get("subscriberCount", 0))
                            self._subscriber_count = subs
                            log.debug(f"登録者数: {subs}")
                except Exception as e:
                    log.warning(f"登録者数取得失敗: {e}")
            else:
                # ダミー（ゆっくり増加）
                if self._subscriber_count is None:
                    self._subscriber_count = 100
                else:
                    self._subscriber_count += 1

            time.sleep(60)   # 1分ごとに更新
