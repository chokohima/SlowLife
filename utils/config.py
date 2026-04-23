"""
Config — config.json のロード・デフォルト設定管理
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field

log = logging.getLogger("config")


@dataclass
class Config:
    # YouTube設定
    youtube_video_id: str  = ""
    youtube_api_key:  str  = ""

    # Ollama
    ollama_model: str       = "gemma3:4b"
    ollama_url:   str       = "http://localhost:11434"

    # ゲームバランス
    sub_to_villager_ratio: int  = 1    # 登録者N人 = 村人1人（軽量運用向けに1:1を既定）
    monologue_interval_sec: int = 45   # 独り言間隔（秒）

    # 画面
    fullscreen: bool = False
    vsync:      bool = True

    @classmethod
    def load(cls, path: str) -> "Config":
        p = Path(path)
        if not p.exists():
            log.info(f"config.json未発見。デフォルト設定を使用 ({path})")
            cfg = cls()
            cfg.save(path)
            return cfg
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            cfg = cls(**{k: v for k, v in d.items()
                         if k in cls.__dataclass_fields__})
            log.info("config.json ロード完了")
            return cfg
        except Exception as e:
            log.error(f"config.json 読み込みエラー: {e} → デフォルト使用")
            return cls()

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        log.info(f"config.json 保存: {path}")
