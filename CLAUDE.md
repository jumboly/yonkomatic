# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## まず読むもの

1. **`ROADMAP.md`** — ライブステータス。現在地、次の Step、直近の決定事項、既知の挙動 (gotchas)、バックログ。**作業を始める前に必ず読む**。
2. **`SPEC.md`** — 設計仕様書 (引き継ぎ全文)。ROADMAP.md で書かれていない設計判断の根拠が欲しいときに参照。

Step 完了 / 重要決定 / 新たなハマりポイントを発見したら、同じセッション内で `ROADMAP.md` を更新してからコミットする。情報の単一ソース。

## 開発コマンド

```bash
uv sync                            # 依存関係インストール
uv run yonkomatic --help           # CLI 確認
uv run yonkomatic version

# 動作確認 (Step 1)
uv run yonkomatic test slack       # Slack 疎通 (.env に SLACK_BOT_TOKEN/CHANNEL_ID 必要)

# 動作確認 (Step 2)
uv run yonkomatic test gemini --prompt "<具体的な画像描写>"  # Gemini 単体
uv run yonkomatic test panel       # シナリオ → Claude プロンプト → Gemini 画像

# Lint
uv run ruff check src/

# 設定だけ差し替えたい時 (例: 1K → 2K)
sed 's/image_size: "1K"/image_size: "2K"/' config.yaml > /tmp/cfg.yaml
uv run yonkomatic test panel --config /tmp/cfg.yaml
```

`output/`, `scenarios/`, `state/` は `.gitignore` 済み (利用者ブランチでのみ commit される)。テストの生成物は気にせず置いてよい。

## アーキテクチャ大枠

### パイプライン (1 エピソードあたり)

```
ScenarioEpisode (JSON)
   ↓ Stage 1: panel/description.py — Claude にプロンプト生成を依頼
英語の統合画像プロンプト
   ↓ Stage 2: ai/gemini_client.py — Gemini で 1 枚生成
4 コマ画像 (PNG/JPEG)
   ↓ Stage 3+: panel/composer.py + validator.py (Step 3 で実装)
   ↓ Stage 5:  publisher/* — 全 enabled Publisher に並列投稿
PublishResult[]
```

週次でシナリオを Claude が 7 話分一括生成 (Step 4)、日次でその週の今日のエピソードを取り出して上記パイプラインに流す。

### 抽象化のレイヤ

- **`Publisher` Protocol** (`publisher/base.py`): Slack / Discord / 静的サイトを同一 Protocol で扱う。`publish(episode, image_path) → PublishResult`。失敗は **例外送出ではなく `PublishResult(ok=False)`** にする (1 つの Publisher の障害が他に波及しない設計)。
- **AI クライアント** (`ai/claude_client.py`, `ai/gemini_client.py`): SDK 仕様変更を 1 箇所に閉じる薄いラッパ。リトライポリシも内蔵。

### 設定駆動の env var 解決

API キーやチャンネル ID 等の機密値は **設定オブジェクトには入れない**。`config.yaml` には env var **名前** だけを書き (`token_env: SLACK_BOT_TOKEN` のように)、呼び出し側 (CLI の `_require_env`) で `os.environ` から読む。

これにより:
- Publisher / AI Client は `api_key: str` / `token: str` を必須引数で受ける (env への副作用なし、テストしやすい)
- 環境変数名を変えたい利用者は `config.yaml` だけ書き換えれば良い

### `content/` 駆動設定

`ContentConfig` の `characters_dir` / `world_dir` 等は subdir 名を制御する。`ContentPack.from_dir(base, content_cfg=cfg.content)` のようにコンフィグを渡すこと。**ハードコードしない**。

## 利用者ブランチ vs main の境界

このリポジトリは **OSS テンプレート**。main には:

- ✅ フレームワークコード、`examples/minimal/` テキストのみのサンプル、ドキュメント、ワークフロー定義
- ❌ 実キャラ素材、API キー、AI 生成された参照画像 (ライセンス曖昧)、`scenarios/` `output/` `state/` の実データ

`.gitignore` の `/scenarios/`, `/output/`, `/state/` は **先頭 `/` 必須**。`state/` だけだと `src/yonkomatic/state/` まで巻き込んでしまう。

## コーディング規約 / コミット

- **コメントは WHY のみ**。WHAT は識別子で表現。Step 番号やタスクへの参照は code に書かない (PR 説明 / ROADMAP.md に書く)。
- **`raise typer.Exit(code=N)`** で CLI を終了する。`sys.exit` は混ぜない。
- **`try/except + メッセージ + Exit`** の繰り返しは `_fail_on(action)` コンテキストマネージャで集約する (`cli.py`)。
- **`Co-Authored-By: Claude ...`** 行は **付けない**。コミット hook が捏造判定で拒否する (2026-05-08 時点)。
- **`google-genai` の retry**: サーバが返す `retryDelay` を honor する (`_extract_retry_delay`)。固定 backoff だけにしない。

## 開発時の AI 利用は軽めに

`config.yaml` のデフォルトは **`image_size: 1K`** (本番品質確認時のみ 2K)。テスト中の生成は速度・コストを優先する。Anthropic console の **Settings → Limits** で月次 spend limit を設定推奨。

## 段階的実装の進め方

1. ROADMAP.md の現在地を確認
2. その Step のスコープを SPEC.md で詳細確認
3. 不明点があれば AskUserQuestion で先に潰してから実装
4. Step 完了したら `/simplify` でレビューしてからコミット
5. ROADMAP.md の「現在地」「Step 進捗 (commit hash 追記)」「直近の決定事項」を更新してコミット
6. ユーザーレビューを依頼
