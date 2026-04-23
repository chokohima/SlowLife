"""
MusicGenerator — SNESスタイルのほのぼのBGM自動生成
pygame.mixer を使いリアルタイムでチップチューンを合成
Emo8bitAIプロジェクトの簡易バージョン
"""

import threading
import time
import math
import random
import struct
import logging
import pygame
import numpy as np

log = logging.getLogger("music")

SAMPLE_RATE = 44100
BPM         = 90          # ほのぼのテンポ
BEAT_SEC    = 60.0 / BPM  # 1拍の秒数

# SNES風ペンタトニックスケール（Cメジャーペンタ）
PENTA_FREQS = [
    261.63,  # C4
    293.66,  # D4
    329.63,  # E4
    392.00,  # G4
    440.00,  # A4
    523.25,  # C5
    587.33,  # D5
    659.25,  # E5
]

# 季節ごとの音色パラメータ
SEASON_PARAMS = {
    "spring": {"tempo_mult": 1.0,  "brightness": 0.8, "reverb": 0.2},
    "summer": {"tempo_mult": 1.1,  "brightness": 1.0, "reverb": 0.1},
    "autumn": {"tempo_mult": 0.9,  "brightness": 0.6, "reverb": 0.3},
    "winter": {"tempo_mult": 0.75, "brightness": 0.4, "reverb": 0.5},
}


def _square_wave(freq: float, duration: float,
                 duty: float = 0.5, volume: float = 0.3) -> np.ndarray:
    """矩形波（SNESパルス音）"""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    period   = 1.0 / freq
    phase    = (t % period) / period
    wave     = np.where(phase < duty, 1.0, -1.0).astype(np.float32)
    # 軽いエンベロープ
    env      = np.ones(n, dtype=np.float32)
    attack   = int(SAMPLE_RATE * 0.01)
    release  = int(SAMPLE_RATE * 0.05)
    env[:attack]   = np.linspace(0, 1, attack)
    env[-release:] = np.linspace(1, 0, release)
    return (wave * env * volume).astype(np.float32)


def _triangle_wave(freq: float, duration: float,
                   volume: float = 0.25) -> np.ndarray:
    """三角波（SNESバス・メロディ）"""
    n = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    phase = (t * freq) % 1.0
    wave  = np.where(phase < 0.5,
                     4 * phase - 1,
                     3 - 4 * phase).astype(np.float32)
    return (wave * volume).astype(np.float32)


def _noise_drum(duration: float, volume: float = 0.15) -> np.ndarray:
    """ノイズドラム"""
    n = int(SAMPLE_RATE * duration)
    noise = np.random.uniform(-1, 1, n).astype(np.float32)
    env   = np.exp(-np.linspace(0, 10, n)).astype(np.float32)
    return (noise * env * volume).astype(np.float32)


class MusicGenerator:
    def __init__(self):
        self._thread  = None
        self._running = False
        self._season  = "spring"
        self._channel = pygame.sndarray.make_sound(
            np.zeros((SAMPLE_RATE // 4, 2), dtype=np.int16)
        )

    def set_season(self, season: str):
        self._season = season

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info("音楽生成スタート")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self):
        while self._running:
            try:
                self._play_phrase()
            except Exception as e:
                log.warning(f"音楽生成エラー: {e}")
                time.sleep(2)

    def _play_phrase(self):
        """4小節のランダムフレーズを生成して再生"""
        params   = SEASON_PARAMS.get(self._season, SEASON_PARAMS["spring"])
        beat     = BEAT_SEC / params["tempo_mult"]
        measures = 4
        beats_pm = 4

        phrase_duration = beat * beats_pm * measures
        n_samples = int(SAMPLE_RATE * phrase_duration)
        mix = np.zeros(n_samples, dtype=np.float32)

        # メロディ（矩形波）
        for measure in range(measures):
            for beat_i in range(beats_pm):
                if random.random() < 0.7:   # 70%の確率で音を出す
                    freq = random.choice(PENTA_FREQS) * params["brightness"]
                    dur  = beat * random.choice([0.5, 1.0, 1.5])
                    start = int((measure * beats_pm + beat_i) * beat * SAMPLE_RATE)
                    wave  = _square_wave(freq, min(dur, beat * 0.9), volume=0.25)
                    end   = start + len(wave)
                    if end <= n_samples:
                        mix[start:end] += wave

        # ベースライン（三角波、1オクターブ下）
        for measure in range(measures):
            freq = random.choice(PENTA_FREQS[:4]) / 2
            start = int(measure * beats_pm * beat * SAMPLE_RATE)
            dur  = beats_pm * beat * 0.9
            wave = _triangle_wave(freq, dur, volume=0.2)
            end  = start + len(wave)
            if end <= n_samples:
                mix[start:end] += wave

        # ドラム（2拍ごと）
        for beat_i in range(measures * beats_pm):
            if beat_i % 2 == 0:
                start = int(beat_i * beat * SAMPLE_RATE)
                wave  = _noise_drum(0.05)
                end   = start + len(wave)
                if end <= n_samples:
                    mix[start:end] += wave

        # クリッピング防止 & int16変換
        mix = np.clip(mix, -1.0, 1.0)
        stereo = np.stack([mix, mix], axis=1)
        audio  = (stereo * 32767).astype(np.int16)

        sound = pygame.sndarray.make_sound(audio)
        sound.play()
        time.sleep(phrase_duration * 0.95)   # 次のフレーズと少し重ねる
