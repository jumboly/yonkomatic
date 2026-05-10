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

# 動作確認
uv run yonkomatic test slack       # Slack 疎通 (.env に SLACK_BOT_TOKEN/CHANNEL_ID 必要)
uv run yonkomatic test image --prompt "<具体的な画像描写>"  # OpenAI 画像生成単体
uv run yonkomatic test panel       # シナリオ → text LLM プロンプト → 画像生成

# Lint
uv run ruff check src/
```

`output/`, `scenarios/`, `state/` は `.gitignore` 済み (利用者ブランチでのみ commit される)。テストの生成物は気にせず置いてよい。

## アーキテクチャ大枠

### パイプライン (1 エピソードあたり)

```
ScenarioEpisode (YAML)
   ↓ Stage 1: panel/description.py — text LLM (gpt-5.4) に panel_prompt.md を展開して投入
英語の統合画像プロンプト
   ↓ Stage 2: ai/openai_client.py — gpt-image-1 で 1 枚生成 (refs があれば images.edit)
4 コマ画像 (PNG/JPEG)
   ↓ Stage 5:  publisher/* — 全 enabled Publisher に並列投稿
PublishResult[]
```

週次で Stage 0 (`scenario/generator.py` + `scenario_prompt.md`) を Structured Output 経由で叩いて `scenarios/{week}.yaml` を生成、日次でその週の今日のエピソードを取り出して上記パイプラインに流す。

### 抽象化のレイヤ

- **`Publisher` Protocol** (`publisher/base.py`): Slack / Discord / 静的サイトを同一 Protocol で扱う。`publish(episode, image_path) → PublishResult`。失敗は **例外送出ではなく `PublishResult(ok=False)`** にする (1 つの Publisher の障害が他に波及しない設計)。
- **AI クライアント** (`ai/openai_client.py`): OpenAI SDK の薄いラッパ。テキスト complete + Structured Output (`beta.chat.completions.parse`) + 画像生成 (`images.generate` / `images.edit`) を 1 クラスに統合。リトライポリシ内蔵。
- **テンプレート機構** (`template/render.py`, `templates/*.md`): プロンプトテキストはコードから外出しした YAML frontmatter 付き Markdown ファイル。`{{var}}` 単純置換。利用者は `content/` に同名ファイルを置けば上書き可能 (フォールバック方式)。

### 設定駆動の env var 解決

API キーやチャンネル ID 等の機密値は **設定オブジェクトには入れない**。`config.yaml` には env var **名前** だけを書き (`token_env: SLACK_BOT_TOKEN`, `openai_api_key_env: OPENAI_API_KEY` のように)、呼び出し側 (CLI の `_require_env`) で `os.environ` から読む。

これにより:
- Publisher / AI Client は `api_key: str` / `token: str` を必須引数で受ける (env への副作用なし、テストしやすい)
- 環境変数名を変えたい利用者は `config.yaml` だけ書き換えれば良い

### `content/` 駆動設定

`ContentConfig` の `prompt_filename` / `images_dir` は `prompt.md` と `images/` の名前を制御する。`ContentPack.from_dir(base, content_cfg=cfg.content)` のようにコンフィグを渡すこと。**ハードコードしない**。

`images/` は再帰 glob で全画像を集める (サブディレクトリ・ファイル名自由、拡張子 `.png/.jpg/.jpeg/.webp`)。順序を制御したければ `01-...` のような numeric prefix を使う (sorted で安定順)。`max_images` を超えたら warn ログを出して先頭 N 枚に切り捨て。

## upstream テンプレ vs fork 先の境界

このリポジトリは **OSS テンプレート専用** (cron は停止済み、`workflow_dispatch` のみ)。利用者は fork して fork 先で運用する。upstream main には:

- ✅ フレームワークコード、`content/` の動作確認用サンプル素材一式 (テキスト + プロジェクト保有の AI 生成リファレンス画像)、ドキュメント、ワークフロー定義
- ❌ API キー、`scenarios/` `output/` `state/` の実運用データ
- `content/images/` の画像はプロジェクトが OSS ライセンス下で配布する用に保有するものに限定する。fork 先で利用者が自前の画像に差し替える想定 (`.gitattributes` の `content/* merge=ours` で upstream 更新時の衝突を回避)

`.gitignore` の `/scenarios/`, `/output/`, `/state/`, `/tmp/` は **先頭 `/` 必須**。`state/` だけだと `src/yonkomatic/state/` まで巻き込んでしまう。

## 出力ディレクトリのルール

検証用の出力は **production-bound** と **ephemeral** の二階層で分離する。各セッションで出力先がぶれないように厳守。

- **`output/`** — production-bound。`publish` / `publish-today` の archive、`batch-fetch-images` の preflight。CLI が自動運用で書き込む場所、人手で scratch を置かない:
  - `output/archive/{date}.{png,yaml}`
  - `output/preflight/{week}/ep{N}.png`
- **`tmp/`** — 検証・実験。すべて gitignored、人手で気軽に消して良い:
  - `tmp/verify/{cmd}/{YYYYMMDD-HHMMSS}/` — `test panel` / `test image` のデフォルト出力先 (ラン毎に別ディレクトリ、昇順 lexicographic で chronological)。各ディレクトリ内は `image.png` + `panel-prompt.txt` + `image-prompt.txt` のフラット構成
  - `tmp/experiments/{YYYYMMDD}-{tag}/` — A/B 比較や手書きシナリオなど topic ごとの実験。日付 prefix で昇順整列

`test panel --output ...` で個別パスを指定すれば従来どおり明示先に書き出される (デフォルトを変えただけで `--output` 指定時の挙動は同じ)。

## コーディング規約 / コミット

- **コメントは WHY のみ**。WHAT は識別子で表現。Step 番号やタスクへの参照は code に書かない (PR 説明 / ROADMAP.md に書く)。
- **`raise typer.Exit(code=N)`** で CLI を終了する。`sys.exit` は混ぜない。
- **`try/except + メッセージ + Exit`** の繰り返しは `_fail_on(action)` コンテキストマネージャで集約する (`cli.py`)。
- **`Co-Authored-By: Claude ...`** 行は **付けない**。コミット hook が捏造判定で拒否する (2026-05-08 時点)。
- **OpenAI のリトライ**: `RateLimitError` と 5xx `APIError` で指数 backoff 再試行 (最大 60s cap)。それ以外の 4xx は即時 raise (修正不能なため)。

## 開発時の AI 利用は軽めに

`config.yaml` のデフォルトは **`image_model: gpt-image-1`** (本番品質を狙うときは `gpt-image-2` に切替)。テスト中の生成は速度・コストを優先する。OpenAI dashboard の **Settings → Billing** で月次 spend limit を設定推奨。

## 段階的実装の進め方

1. ROADMAP.md の現在地を確認
2. その Step のスコープを SPEC.md で詳細確認
3. 不明点があれば AskUserQuestion で先に潰してから実装
4. Step 完了したら `/simplify` でレビューしてからコミット
5. ROADMAP.md の「現在地」「Step 進捗 (commit hash 追記)」「直近の決定事項」を更新してコミット
6. ユーザーレビューを依頼
