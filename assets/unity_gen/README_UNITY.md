# Unity スプライト自動生成ガイド

## Unity拡張機能でのスプライト生成手順

### 方法1: Unity Sprite Editor + Aseprite連携（推奨）

1. **Aseprite** でドット絵を描く（またはAI生成）
2. Unity の `Assets/Sprites/` にインポート
3. `Sprite Editor` で **Slice** → Automatic or Grid で分割
4. `2D Sprite Atlas` にまとめてテクスチャアトラス化

### 方法2: Unity ML-Agents + Stable Diffusion（高度）

```bash
# Stable Diffusion でSNES風スプライト生成
# プロンプト例:
"SNES style pixel art village building, 32x32, transparent background, retro game sprite"
"SNES pixel art cute fairy character, 16x16, idle animation frames"
```

---

## このプロジェクトで使うスプライトサイズ

| 種類        | サイズ    | ファイル名例              |
|-----------|---------|------------------------|
| タイル      | 32×32   | tile_grass.png          |
| 建物        | 32×48   | building_house.png      |
| 村人        | 16×24   | villager_idle.png       |
| チャッピー  | 32×32   | chappy_idle.png         |
| UI部品      | 各種     | hud_bar.png             |

---

## スプライトなしでも動作します

スプライトファイルが見つからない場合、`renderer.py` は  
pygame の図形描画（矩形・円・多角形）でフォールバック表示します。  
まずはスプライトなしで動作確認し、後から差し替えてください。

---

## 将来対応予定: PyGame + Tiled マップエディタ連携

`.tmx` 形式のTiledマップを読み込む機能を追加予定。  
`pytmx` ライブラリで対応可能。
