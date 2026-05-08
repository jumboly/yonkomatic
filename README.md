# yonkomatic

**yonkomatic** = 四コマ (yonkoma) + automatic.

AI が毎日 4 コマ漫画を描き、Slack / Discord / 静的サイトへ自動投稿する OSS テンプレート。

> **Status:** 🚧 Step 1 (土台 + Slack 疎通) 実装中。詳細仕様は [`docs/SPEC.md`](docs/SPEC.md) を参照してください。

## このリポジトリの位置付け

このリポジトリは **テンプレート** です。fork または自分のブランチを切って、`content/` 配下に独自のキャラクター・世界観素材を持ち込むだけで、自分専用の 4 コマ漫画ボットが動きます。

## アーキテクチャ概要

| 領域 | 採用 |
| ---- | ---- |
| 実行基盤 | GitHub Actions (cron) |
| シナリオ生成 | Claude Sonnet 4.6 |
| 画像生成 | Gemini 3.1 Flash Image Preview |
| 投稿先 | Slack / Discord / 静的サイト (Publisher Protocol で抽象化) |
| 言語 | Python 3.12+, uv |

## Quick Start (開発中)

```bash
# 1. 依存関係をインストール
uv sync

# 2. .env を準備 (.env.example をコピー)
cp .env.example .env
# SLACK_BOT_TOKEN と SLACK_CHANNEL_ID を設定

# 3. Slack 疎通テスト
uv run yonkomatic test slack
```

詳細なセットアップ手順は [`SETUP.md`](SETUP.md) を参照。

## ライセンス

[MIT License](LICENSE)
