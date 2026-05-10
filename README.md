# yonkomatic

**yonkomatic** = 四コマ (yonkoma) + automatic.

AI が毎日 4 コマ漫画を描き、Slack / 静的サイトへ自動投稿する OSS テンプレート。

> **Status:** Step 6.6 完了。Step 7 (OSS 公開準備) 着手中。
> 進捗は [`ROADMAP.md`](ROADMAP.md)、設計仕様は [`SPEC.md`](SPEC.md) を参照。

## このリポジトリの位置付け

このリポジトリ (`jumboly/yonkomatic`) は **テンプレート専用** で、cron は停止しています。実運用するには **自分のリポジトリに fork** して、fork 先で Secrets / cron / 自前のキャラ素材を設定してください。

```
┌─────────────────────────────┐         ┌─────────────────────────────┐
│ upstream (このリポジトリ)    │         │ あなたの fork (private 推奨) │
│                              │  fork   │                              │
│ - コード / 仕様の単一ソース   │ ──────▶ │ - 自前の content/ 素材       │
│ - cron 停止                  │         │ - Secrets 設定済み            │
│ - PR で改善を上流に戻す       │         │ - cron 有効化、自動投稿       │
└─────────────────────────────┘         └─────────────────────────────┘
```

セットアップ手順は [`SETUP.md`](SETUP.md) を参照。

## アーキテクチャ概要

| 領域 | 採用 |
| ---- | ---- |
| 実行基盤 | GitHub Actions (cron — fork 先で有効化) |
| シナリオ生成 | OpenAI gpt-5.4 (Structured Output) |
| 画像生成 | OpenAI gpt-image-2 (960x1280, batch 50% off) |
| 投稿先 | Slack / 静的サイト (Publisher Protocol で抽象化、Discord は将来対応) |
| 言語 | Python 3.12+, uv |

## Quick Start

```bash
# 1. fork してクローン (詳細は SETUP.md)
gh repo fork jumboly/yonkomatic --clone --remote

# 2. 依存関係インストール
cd yonkomatic
uv sync

# 3. .env を準備
cp .env.example .env
# OPENAI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を埋める

# 4. 自前素材を持ち込む
# content/prompt.md と content/images/ を自分の作品で書き換える
# (上流リポには動作確認用のサンプル素材が同梱されているのでそのままでも動く)

# 5. ローカル動作確認
uv run yonkomatic test slack
uv run yonkomatic test panel --content content
```

## content/ の構造

```
content/
  prompt.md          # キャラクター / 世界観 / 画風 を 1 ファイルにまとめる
  images/            # キャラ参考画像 (PNG/JPEG/WebP)。サブディレクトリ自由
    *.png
```

同梱サンプルがそのまま `content/prompt.md` に入っているので、まずはそのまま動作確認できます。プロンプトテンプレ自体をカスタマイズしたい上級者は `content/scenario_prompt.md` / `content/panel_prompt.md` を置けば組み込みデフォルトを上書きできます (フォールバック方式)。

## ライセンス

[MIT License](LICENSE)
