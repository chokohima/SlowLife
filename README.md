# 🏡 SNES Village Simulator — チャッピーの村

YouTube Live 連動型・SNESスタイル村づくりシミュレーター  
チャットや登録者数に応じて村が成長し、チャッピーが Ollama で独り言をつぶやく。

---

## 📂 プロジェクト構造

```
snes_village/
├── main.py                  # メインコントローラー（エントリーポイント）
├── requirements.txt
├── data/
│   ├── config.json          # 設定ファイル（要編集）
│   ├── saves/               # オートセーブDB（SQLite）
│   └── rag/                 # RAGベクトルDB（ChromaDB）
├── core/
│   ├── game_state.py        # 村の全状態データクラス
│   ├── village_engine.py    # 成長ロジック
│   └── save_manager.py      # セーブ・ロード
├── ai/
│   └── chappy.py            # チャッピーAI（Ollama連携）
├── rag/
│   └── chat_memory.py       # RAGチャット記憶
├── ui/
│   ├── renderer.py          # Pygame描画
│   └── hud.py               # ステータスHUD
├── music/
│   └── generator.py         # チップチューンBGM自動生成
├── utils/
│   ├── youtube_listener.py  # YouTube Live接続
│   └── config.py            # 設定ローダー
└── assets/
    └── unity_gen/           # Unityで生成したスプライト置き場
        └── README_UNITY.md
```

---

## 🚀 セットアップ手順

### 1. Python環境（RTX3060ローカル）

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 2. Ollama モデルを準備

```bash
ollama pull gemma3:4b
ollama serve   # バックグラウンドで起動
```

### 3. YouTube設定

1. [Google Cloud Console](https://console.cloud.google.com/) で  
   YouTube Data API v3 を有効化 → APIキーを取得
2. `data/config.json` を編集:
   ```json
   {
     "youtube_video_id": "ライブのVideoID",
     "youtube_api_key":  "取得したAPIキー"
   }
   ```
3. ライブ配信を開始し、Video IDを確認

### 4. 起動

```bash
python main.py
```

---

## 📺 OBS配信設定

1. OBS Studio でウィンドウキャプチャ →「チャッピーの村」を選択
2. 解像度: 1280×720 推奨
3. エンコーダ: NVENC (RTX3060) → CBR 4000–6000 kbps
4. YouTube ライブ配信設定でストリームキーを入力して配信開始

---

## 🎮 ステータス対応表（ゲーム内表示）

| YouTube実態      | ゲーム内表示名       |
|-----------------|-----------------|
| 登録者数         | 村の評判（人）      |
| 視聴者数         | 旅人の訪問数        |
| 高評価数         | 村の人気度          |
| チャット数       | 村会議の発言数      |
| 登録者数 ÷ 10   | 村人の数（人口）    |

---

## 🌱 村の成長ロジック

| トリガー         | 効果                            |
|-----------------|-------------------------------|
| チャット1件      | 繁栄度+0.5、文化+0.1            |
| リアクション1個  | 繁栄度+0.2                     |
| 毎ゲーム日       | 繁栄度＋(村人数×0.1) 自然成長   |
| 繁栄度50達成     | 教会が建設可能になる            |
| 繁栄度200達成    | 城が建設可能になる              |

---

## 🎨 Unity スプライト自動生成（任意）

`assets/unity_gen/` に配置したスプライトは自動的に読み込まれます。  
Unity Editor の **Window → 2D Sprite Atlas Generator** (または  
外部ツール `assets/unity_gen/generate.py`) を使って  
タイル・建物・キャラのスプライトシートを生成してください。

スプライトなしでも pygame の図形描画でフォールバック動作します。

---

## ⌨️ キーボードショートカット

| キー          | 動作               |
|-------------|------------------|
| Ctrl+S      | 手動セーブ         |
| F1          | デバッグ情報表示   |
| ESC / ×ボタン | 終了（自動セーブ）|

---

## 🔧 カスタマイズポイント

- `utils/config.json` — OllamaモデルやBPMなど全般設定
- `core/village_engine.py` の `BUILDING_DEFS` — 建物の必要コスト
- `core/village_engine.py` の `CHAT_PROSPERITY_GAIN` — チャットの成長量
- `music/generator.py` の `PENTA_FREQS` / `BPM` — BGMのスケールとテンポ
- `ai/chappy.py` の `SYSTEM_PROMPT` — チャッピーのキャラ設定

---

## ⚡ RTX3060 軽量化のポイント

- Pygame は CPU描画（GPU不使用）→ VRAM消費なし
- Ollama は `gemma3:4b`（約3GB VRAM）→ RTX3060でも余裕
- ChromaDB はローカルDB（APIコールなし）
- BGM は numpy で CPU合成（GPU不使用）
- OBS NVENC で GPU使用するのはエンコードのみ

総VRAM目安: Ollama 3GB + OBS 1GB ≈ **4GB** （12GB中 4GB使用）
