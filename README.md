# yonkomatic

**yonkomatic** = 四コマ (yonkoma) + automatic.

AI が毎日 4 コマ漫画を描き、Slack / Discord / 静的サイトへ自動投稿する OSS テンプレート。

> **Status:** 🚧 Step 6 進行中 (テンプレ化 + OpenAI 切替 + 構造刷新)。
> 進捗は [`ROADMAP.md`](ROADMAP.md)、設計仕様は [`SPEC.md`](SPEC.md) を参照。

## このリポジトリの位置付け

このリポジトリは **テンプレート** です。fork または自分のブランチを切って、`content/` 配下に独自のキャラクター・世界観素材 (`prompt.md`) と参考画像 (`images/`) を持ち込むだけで、自分専用の 4 コマ漫画ボットが動きます。

## アーキテクチャ概要

| 領域 | 採用 |
| ---- | ---- |
| 実行基盤 | GitHub Actions (cron) |
| シナリオ生成 | OpenAI gpt-5.4 (Structured Output) |
| 画像生成 | OpenAI gpt-image-1 (画像参照対応) |
| 投稿先 | Slack / Discord / 静的サイト (Publisher Protocol で抽象化) |
| 言語 | Python 3.12+, uv |

## Quick Start (開発中)

```bash
# 1. 依存関係をインストール
uv sync

# 2. .env を準備 (.env.example をコピー)
cp .env.example .env
# OPENAI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を設定

# 3. 素材を用意
cp -R examples/minimal/* content/
# content/prompt.md を自分の作品に書き換え、content/images/ にキャラ参考画像を置く

# 4. Slack 疎通テスト
uv run yonkomatic test slack

# 5. 1 話分を生成して動作確認 (実 API を叩く)
uv run yonkomatic test panel --content content
```

詳細なセットアップ手順は [`SETUP.md`](SETUP.md) を参照。

## content/ の構造

```
content/
  prompt.md          # キャラクター / 世界観 / 画風 を 1 ファイルにまとめる
  images/            # キャラ参考画像 (PNG/JPEG/WebP)。サブディレクトリ自由
    *.png
```

雛形は `examples/minimal/prompt.md` を参照。プロンプトテンプレ自体をカスタマイズしたい上級者は `content/scenario_prompt.md` / `content/panel_prompt.md` を置けば組み込みデフォルトを上書きできます (フォールバック方式)。

## ライセンス

[MIT License](LICENSE)
