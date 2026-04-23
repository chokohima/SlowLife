"""
ChappyAI — Ollama経由のキャラクターAI
独り言・チャット返答の両モードを持つ
<think>タグはChappyStreamと同じ手法でストリップ
"""

import asyncio
import re
import logging
import httpx
from core.game_state import GameState

log = logging.getLogger("chappy")

OLLAMA_URL = "http://localhost:11434/api/generate"

SYSTEM_PROMPT = """
あなたは「チャッピー」という小さな妖精のキャラクターです。
SNES風の中世の村に住んでいて、村の守り神でもあります。

性格:
- のんびりほのぼのしている
- 村のことが大好きで、よく観察している
- 視聴者（チャットしてくれる旅人）をとても歓迎する
- ときどき天然でかわいらしいミスをする
- 感情表現豊か

話し方:
- 一人称は「ボク」
- 語尾は「〜だよ！」「〜かな？」「〜なの！」など柔らかく
- 難しい言葉は使わない
- 絵文字は使わない（ゲーム世界なので）
- 1〜2文で簡潔に

現在の村の状態が渡されるので、それを踏まえて話してください。
"""


def _strip_think(text: str) -> str:
    """<think>...</think>タグを除去"""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


async def _ollama(prompt: str, model: str, max_tokens: int = 120) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.85,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
        }
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(OLLAMA_URL, json=payload)
            r.raise_for_status()
            raw = r.json().get("response", "")
            return _strip_think(raw)
    except Exception as e:
        log.warning(f"Ollama接続エラー: {e}")
        return "うーん、ちょっと考え中だよ…"


class ChappyAI:
    def __init__(self, model: str = "gemma3:4b", rag=None):
        self.model = model
        self.rag   = rag

    async def monologue(self, state: GameState, context: str = "") -> str:
        """独り言（定期的に自発的につぶやく）"""
        village_info = state.summary()
        rag_part = f"\n最近の旅人との会話:\n{context}" if context else ""
        prompt = (
            f"{village_info}{rag_part}\n\n"
            "チャッピーとして、今の村の様子を見ながら独り言をつぶやいてください。"
            "短く1〜2文で。"
        )
        result = await _ollama(prompt, self.model, max_tokens=80)
        return result or "村はいい天気だよ！"

    async def respond(self, username: str, message: str,
                      context: str, state: GameState) -> str:
        """チャットへの返答"""
        village_info = state.summary()
        rag_part = f"\n関連する過去の会話:\n{context}" if context else ""
        prompt = (
            f"{village_info}{rag_part}\n\n"
            f"旅人「{username}」さんが言いました:「{message}」\n\n"
            "チャッピーとして返事をしてください。短く1〜2文で。"
        )
        result = await _ollama(prompt, self.model, max_tokens=100)
        return result or f"{username}さん、ようこそ村へ！"
