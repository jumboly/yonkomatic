# yonkomatic — 実装引き継ぎ仕様書

> **2026-05-10 注記**: 本仕様書は Step 1〜5e 時点での **設計引き継ぎ** スナップショットです。Step 6 で AI ベンダー (Anthropic + Google → OpenAI) 切替、`content/` の 4 フォルダ → `prompt.md` + `images/` への簡素化、`text_rendering.mode` の `pil_overlay` 廃止 + `model_render` 採用、JSON → YAML 切替、プロンプトのテンプレート外出しを実施し、現在の実装は本書から大きく逸脱しています。**現在の構造と運用は [`ROADMAP.md`](ROADMAP.md) を必ず参照してください**。本書はそれ以前の設計判断の根拠を遡りたいときの履歴として残しています。

AI生成4コマ漫画を Slack / Discord / 静的サイト等のプラットフォームへ毎日自動投稿する **オープンソースなプラットフォーム** を構築する。

このリポジトリは「テンプレート」として公開し、利用者は fork または自分のブランチを切って独自のキャラクター・世界観素材を持ち込むだけで自分専用の4コマ漫画ボットを動かせる、という設計を目指す。

## プロダクト名

**yonkomatic** = 四コマ (yonkoma) + automatic。「四コマ漫画を自動的に」という本質を直球で表現した造語。Python パッケージ名 (`import yonkomatic`)、CLI コマンド (`yonkomatic publish`)、リポジトリ名すべてに同じ綴りで使う。

---

## プロジェクトの構造的な前提

### main ブランチの役割

main は **フレームワーク本体 + 動作確認用の最小例** のみを含む「ひな形」として常に保つ。

- `yonkomatic/` (Python フレームワークコード) — フレームワーク本体
- `examples/` — テキストのみの動作確認用サンプル（ライセンス問題を避けるため画像は含めない）
- `content/` — **空** （`.gitkeep` または README のみ）。利用者の素材を入れる場所
- `config.yaml` — デフォルト設定
- `.github/workflows/` — ワークフロー定義
- ドキュメント、ライセンス、コントリビューションガイド

### 利用者の使い方

1. **Use this template / Fork** してリポジトリをコピーするか、clone した後で自分のブランチを切る（例: `my-manga`）
2. `content/` 配下に `characters/`, `world/`, `samples/`, `themes/` を配置
3. `config.yaml` を必要に応じて書き換え
4. GitHub Repository Secrets に API キー類を設定

main からのアップデートを取り込みたい場合は `git fetch upstream && git merge upstream/main` で安全にマージできるよう、`content/` には main 側で一切ファイルを置かない。

---

## 確定済みの技術選定（変更しないこと）

| 領域 | 採用 | 補足 |
|---|---|---|
| 実行基盤 | GitHub Actions (cron) | 1日1回・週1回ジョブには十分、無料、Secrets管理が楽 |
| シナリオ生成 | Claude Sonnet 4.6 (`claude-sonnet-4-6`) | 週次一括生成 |
| パネル描写生成 | Claude Sonnet 4.6 | シナリオ→画像プロンプト変換 |
| 画像生成 | Gemini 3.1 Flash Image Preview (`gemini-3.1-flash-image-preview`) | 2026年2月リリース、キャラ一貫性・テキスト描画に最適 |
| ニュース取得 | RSS (`feedparser`) | 認証不要、利用者がフィード差し替え可能 |
| 投稿先プラットフォーム | 抽象化 (Publisher Protocol) | 初期実装: Slack, Discord, 静的サイト |
| 画像合成 | Pillow + Noto Sans JP | テキストオーバーレイのフォールバック用 |
| 言語 | Python 3.12+ | |
| 依存管理 | uv + pyproject.toml | 高速、lockfile込み |
| 設定 | YAML (`config.yaml`) | コード変更なしで運用カスタマイズ |

**重要**: Gemini 3.1 Flash Image はリリースされたばかり。実装着手時に `https://ai.google.dev/gemini-api/docs/image-generation` で最新の SDK API、モデル ID、料金を必ず確認すること。

---

## ディレクトリ構造

```
yonkomatic/
├── .github/
│   └── workflows/
│       ├── weekly-scenarios.yml    # 毎週日曜深夜にシナリオ生成
│       └── daily-publish.yml       # 毎日朝に投稿
├── yonkomatic/                       # フレームワークコード
│   ├── __init__.py
│   ├── cli.py                       # typer ベースの CLI
│   ├── config.py                    # config.yaml + .env 読み込み
│   ├── ai/
│   │   ├── claude_client.py
│   │   └── gemini_client.py
│   ├── news/
│   │   └── fetcher.py               # RSS フィードから時事ネタ取得
│   ├── scenario/
│   │   ├── generator.py             # 週次シナリオ生成
│   │   └── schema.py                # Pydantic models
│   ├── panel/
│   │   ├── description.py           # シナリオ → 4コマプロンプト
│   │   ├── generator.py             # Gemini 呼び出し
│   │   ├── composer.py              # PIL での合成・テキスト
│   │   └── validator.py             # 自己チェック
│   ├── publisher/
│   │   ├── base.py                  # Publisher Protocol + ベースクラス
│   │   ├── slack.py
│   │   ├── discord.py
│   │   └── static_site.py
│   └── state/
│       └── repo.py                  # state.json + 自動コミット
├── content/                         # ★ 利用者の素材置き場 (main では空)
│   ├── README.md                    # 「ここに素材を入れる」説明
│   └── .gitkeep
├── examples/                        # 動作確認用サンプル (テキストのみ)
│   └── minimal/
│       ├── characters/
│       │   └── settings.md
│       ├── world/
│       │   └── settings.md
│       ├── samples/
│       │   └── STYLE.md             # スタイル基準を文章で記述
│       └── themes/
│           └── default.md
├── docs/                            # 静的サイト出力先 (Phase 3 で追加)
│   └── .gitkeep
├── config.yaml                      # デフォルト設定
├── pyproject.toml
├── uv.lock
├── README.md                        # プロジェクト概要 + 使い方
├── SETUP.md                         # 初回セットアップ手順
├── CONTRIBUTING.md
├── LICENSE                          # MIT 推奨
├── .env.example
└── .gitignore
```

利用者が自分のブランチで素材を入れた後の状態：

```
content/
├── characters/
│   ├── settings.md
│   └── refs/{character_name}/{*.png}
├── world/settings.md
├── samples/
│   ├── STYLE.md
│   └── episodes/sample-*.png
└── themes/2026-05.md (任意)

scenarios/                # 機械生成、自動コミット対象
└── 2026-W19.json

output/archive/           # 配信済みエピソード
└── 2026-05/
    ├── day-01.png
    └── day-01.json (メタデータ)

state/state.json
```

---

## 設定ファイル (config.yaml)

```yaml
# yonkomatic のデフォルト設定。利用者は自分のブランチで上書きする。

content:
  base_dir: ./content
  characters_dir: characters
  world_dir: world
  samples_dir: samples
  themes_dir: themes

ai:
  scenario_model: claude-sonnet-4-6
  image_model: gemini-3.1-flash-image-preview
  image_size: "2K"                 # 512 | 1K | 2K | 4K
  aspect_ratio: "3:4"              # 縦長4コマ
  max_image_retries: 3

publishers:
  slack:
    enabled: true
    channel_env: SLACK_CHANNEL_ID
    token_env: SLACK_BOT_TOKEN
  discord:
    enabled: false
    webhook_env: DISCORD_WEBHOOK_URL
  static_site:
    enabled: false
    output_dir: ./docs
    base_url: ""                   # GitHub Pages 等の公開URL

schedule:
  timezone: Asia/Tokyo
  publish_time: "09:00"
  scenario_generation_dow: sunday
  scenario_generation_time: "23:00"

news:
  enabled: true
  feeds:
    # デフォルトは時事色の薄い軽量フィード。利用者が差し替え可能。
    - https://news.yahoo.co.jp/rss/topics/entertainment.xml
    - https://news.yahoo.co.jp/rss/topics/sports.xml
  max_items_per_feed: 10
  lookback_days: 7
  language: ja

text_rendering:
  mode: fallback                   # always | fallback | never
  font_path: ./assets/fonts/NotoSansJP-Regular.otf
  bubble_style: round              # round | rectangle | cloud
```

---

## 動作フロー

### 週次ジョブ (weekly-scenarios.yml)

トリガー: 毎週日曜 JST 23:00 + 手動 (`workflow_dispatch`)。

1. リポジトリ checkout
2. `news.enabled: true` なら `news/fetcher.py` で RSS 取得（先週分の見出し10-20件）
3. `content/characters/settings.md`, `content/world/settings.md`, `content/samples/STYLE.md`, `content/themes/{YYYY-MM}.md` (任意), 取得したニュース見出しを入力に Claude へ：
   - 7話分の独立シナリオを JSON で出力
   - ニュースは「直接的な時事言及ではなくムード・気分・話題の傾向として反映」と明示指示
   - 起承転結、オチが明確、各話で完結
4. JSON Schema バリデーション → `scenarios/{YYYY}-W{NN}.json` に書き出し
5. Git commit + push（`bot: scenarios for week YYYY-WNN`）

### 日次ジョブ (daily-publish.yml)

トリガー: 毎日 JST 9:00 + 手動。

1. リポジトリ checkout
2. `state/state.json` から今日のエピソードインデックスを取得
3. `scenarios/{現在のISO週}.json` から対応シナリオを取得（無ければエラー通知）
4. **Stage 1 — パネル描写生成 (Claude)**: シナリオ + キャラ設定 + STYLE.md → 4パネル描写 + 統合プロンプト + 吹き出しテキスト
5. **Stage 2 — 画像生成 (Gemini 3.1 Flash Image)**: 統合プロンプト + キャラ参照画像3-5枚 + サンプル画像0-2枚 → 4コマ全体を1枚で生成
6. **Stage 3 — バリデーション**: Gemini 自身に矛盾チェック。NGなら最大3回リトライ
7. **Stage 4 — テキストオーバーレイ**: `text_rendering.mode` に従って処理
8. **Stage 5 — マルチパブリッシュ**: 有効な全 Publisher に並列投稿
9. **Stage 6 — アーカイブと状態更新**: `output/archive/` 保存 → `state/state.json` 更新 → commit + push

---

## 投稿先プラットフォーム抽象 (Publisher)

### Protocol 定義

```python
# yonkomatic/publisher/base.py
from typing import Protocol
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Episode:
    number: int
    title: str
    summary_no_spoiler: str
    week: str  # e.g. "2026-W19"
    date: str  # e.g. "2026-05-09"

@dataclass
class PublishResult:
    ok: bool
    publisher: str
    artifact_id: str | None  # slack ts, discord message_id, etc.
    url: str | None
    error: str | None

class Publisher(Protocol):
    name: str
    def publish(self, episode: Episode, image_path: Path) -> PublishResult: ...
```

### 初期実装する Publisher

**Slack** — `slack_sdk` + `files_upload_v2`。Bot Token 方式。
スコープ: `chat:write`, `files:write`, `channels:read`。

**Discord** — Webhook 方式（最もシンプル）で初期実装。`requests.post` で multipart/form-data。
利用者は Discord サーバの設定で Webhook URL を発行し、`DISCORD_WEBHOOK_URL` に登録。

**Static Site** — GitHub Pages 互換のシンプルな静的サイト出力。
- `docs/images/{YYYY-MM-DD}.png` に画像をコピー
- `docs/feed.xml` に RSS 2.0 形式でアイテム追加
- `docs/index.html` を簡易テンプレートで再生成（直近30話の一覧）
- `docs/posts/{YYYY-MM-DD}.html` で個別エピソードページ
- 利用者は GitHub Pages を `/docs` 配信で有効化するだけ

3つを Phase 3 で同時実装。Stage 5 では `enabled: true` の Publisher 全てに並列投稿し、結果を state に記録する。

---

## 重要な実装ポイント

### Gemini 3.1 Flash Image の使い方

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GOOGLE_AI_STUDIO_API_KEY"])

char_refs = [open(p, "rb").read() for p in character_ref_paths]
style_refs = [open(p, "rb").read() for p in style_sample_paths]

response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=[
        *[types.Part.from_bytes(data=img, mime_type="image/png") for img in char_refs],
        *[types.Part.from_bytes(data=img, mime_type="image/png") for img in style_refs],
        prompt_text,
    ],
    config=types.GenerateContentConfig(
        response_modalities=["IMAGE"],
        image_config=types.ImageConfig(
            aspect_ratio="3:4",
            image_size="2K",
        ),
    ),
)
for part in response.candidates[0].content.parts:
    if part.inline_data:
        image_bytes = part.inline_data.data
        break
```

最新 SDK 仕様で必ず確認すること（このコードはあくまで指針）。

### キャラクター一貫性

- 参照画像は同じキャラの異なる角度・表情を3-5枚。Gemini公式推奨パターン。
- プロンプトで衣装・髪型を毎回明示
- 過去エピソードで成功した画像をリファレンスプールに昇格させる仕組みは **ロードマップ参照**

### 時事ネタの安全な取り込み

Claude へのシナリオ生成プロンプトに以下を含める：

```
ニュース見出し（先週分）:
- {見出し1}
- {見出し2}
...

これらは「世間のムード・話題の傾向」として薄く反映させてください。直接的な時事言及（特定の人名・事件・政治・災害）は避け、当該ジャンルが流行っている空気感だけを取り込むこと。

避けるべき題材:
- 政治、宗教、災害、訃報、犯罪
- 特定の実在人物への言及
- 商標・著作権のあるキャラやブランド名
```

### Slack 投稿

```python
from slack_sdk import WebClient

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
response = client.files_upload_v2(
    channel=os.environ["SLACK_CHANNEL_ID"],
    file=image_path,
    title=f"【第{episode_num}話】{episode_title}",
    initial_comment=f"今日の4コマです 🎨\n*あらすじ*: {summary_no_spoiler}",
)
```

### Discord 投稿 (Webhook)

```python
import requests

def publish_discord(webhook_url: str, episode: Episode, image_path: Path) -> PublishResult:
    with open(image_path, "rb") as f:
        response = requests.post(
            webhook_url,
            data={
                "content": f"**【第{episode.number}話】{episode.title}**\n{episode.summary_no_spoiler}",
                "username": "yonkomatic",
            },
            files={"file": (image_path.name, f, "image/png")},
        )
    response.raise_for_status()
    return PublishResult(ok=True, publisher="discord", ...)
```

### 静的サイト Publisher

最小実装の指針：

```python
def publish_static_site(config, episode: Episode, image_path: Path) -> PublishResult:
    docs = Path(config.output_dir)

    # 1. 画像をコピー
    dest = docs / "images" / f"{episode.date}.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(image_path, dest)

    # 2. 個別ページ生成 (シンプルな HTML テンプレート)
    post_html = render_post_html(episode, image_url=f"images/{episode.date}.png")
    (docs / "posts" / f"{episode.date}.html").write_text(post_html)

    # 3. index.html 再生成 (直近30話)
    index_html = render_index_html(get_recent_episodes(docs, limit=30))
    (docs / "index.html").write_text(index_html)

    # 4. RSS feed 更新
    update_rss_feed(docs / "feed.xml", episode, base_url=config.base_url)

    return PublishResult(ok=True, publisher="static_site", url=f"{config.base_url}/posts/{episode.date}.html")
```

外部依存を最小化（Jinja2 程度のみ）し、ジェネレータフレームワークには依存しない方針。

### エラーハンドリング

- 画像生成失敗3回 → 過去アーカイブからの再投稿 + Slack/Discord に障害通知
- Publisher 投稿失敗 → 他の Publisher は継続。失敗した Publisher のみ次回ジョブで再試行可能
- シナリオ枯渇（週途中で7話超え） → その場で緊急生成
- 全AI呼び出しのプロンプト・パラメタを `output/archive/{date}.json` に保存し再現性確保
- 各 Stage の冪等化（既に投稿済みなら再実行でスキップ）

---

## 環境変数 (.env.example)

```bash
# AI
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_AI_STUDIO_API_KEY=...

# Publishers (有効化したものだけ設定)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# 共通
LOG_LEVEL=INFO
DRY_RUN=false
```

GitHub Actions では Repository Secrets に登録。`.env` は `.gitignore`。

---

## 段階的な実装手順

### Step 1 — 土台

- リポジトリ初期化、`pyproject.toml` (uv)
- `yonkomatic/cli.py` で typer ベースの CLI 骨格 (`yonkomatic --help`)
- `config.py` で `config.yaml` + `.env` 読み込み
- `yonkomatic test slack` コマンド: 固定画像を Slack に投稿
- GitHub Actions の `workflow_dispatch` で `yonkomatic test slack` が動く状態に

**完了条件**: ローカルとGitHub Actionsの両方から、固定画像を指定Slackチャンネルに投稿できる。

### Step 2 — 画像生成コア

- `ai/gemini_client.py`: 1枚の画像生成（参照画像渡し含む）
- `yonkomatic test gemini --prompt "..." --refs ...` で出力確認
- `ai/claude_client.py`: シナリオ → パネル描写の変換
- `yonkomatic test panel --scenario examples/minimal/sample-scenario.json`

**完了条件**: ローカルでサンプルシナリオから4コマ画像を1枚生成できる。

### Step 3 — エンドツーエンドパイプライン + マルチパブリッシュ

- `panel/composer.py`: PIL での合成（4枚を縦結合 + 枠線）とテキストオーバーレイ
- `panel/validator.py`: Gemini自己チェックと再生成ループ
- `state/repo.py`: state.json 読み書き
- `publisher/base.py`: Publisher Protocol
- `publisher/slack.py`, `publisher/discord.py`, `publisher/static_site.py`: 3つ同時実装
- `yonkomatic publish --episode {n} --dry-run` でend-to-end確認
- 実 Publisher で1回手動確認（少なくとも Slack + 静的サイト）

**完了条件**: 1コマンドでシナリオ→画像→複数プラットフォーム同時投稿まで通る。

### Step 4 — 週次シナリオ + 時事ネタ + 自動化

- `news/fetcher.py`: RSS 取得（`feedparser`）
- `scenario/generator.py`: 週次7話分一括生成、ニュース反映
- `yonkomatic generate-scenarios --week 2026-W19` で動作確認
- 2つの GitHub Actions ワークフローを完成させる
- エラー時の Publisher 通知

**完了条件**: 1週間放置して7話自動投稿できる。

### Step 5 — オープンソース公開準備

- `README.md`: 概要、デモ画像、Quick Start
- `SETUP.md`: fork/branch 戦略、各 Publisher のセットアップ手順、API キー取得手順、GitHub Secrets 設定、初回テスト手順
- `examples/minimal/`: テキストのみの動作確認用サンプル一式
- `LICENSE`: MIT 推奨
- `CONTRIBUTING.md`
- ユニットテスト（API はモック）
- GitHub Template Repository 設定
- 自分の素材で稼働させた本番サンプルを README に掲載

**完了条件**: 第三者が README 通りに30分以内で自分の漫画ボットを立ち上げられる。

---

## main 公開時に main に置くもの・置かないもの

### main に置く
- フレームワークコード一式（3つの Publisher 実装含む）
- `examples/minimal/` のテキストサンプル（settings.md, STYLE.md, sample-scenario.json）
- ドキュメント、ライセンス
- `config.yaml` のデフォルト
- ワークフロー定義（テンプレート状態でOK、利用者が secrets 設定すれば動く）

### main に置かない
- 実在する具体的なキャラ素材（参照画像、設定書）
- 自分用のトークン、API キー
- AI 生成された参照画像（ライセンス曖昧なため）
- `content/` 配下の実コンテンツ（`.gitkeep` のみ）
- `scenarios/`, `output/archive/`, `state/` の実データ（`.gitignore` するか、利用者ブランチでのみ生成）

---

## ロードマップ（Phase 5 完了後の継続検討項目）

以下は今回の実装範囲外。OSS 公開後に Issue 化して順次取り組む想定。

### 画像生成・品質改善

- **キャラリファレンスプールの自動成長**: 過去エピソードで品質スコアが高かった画像を半自動で `content/characters/refs/` に昇格させる仕組み。Gemini に「このキャラに最も似ているか」を判定させる
- **per-panel + composite フォールバック**: 1枚生成が失敗しがちな場合、4パネルを個別生成して PIL で合成するモードを追加
- **キャラドリフト検出の強化**: 参照画像と生成画像の埋め込みベクトル類似度を計算し、しきい値以下なら強制再生成
- **シード固定オプション**: 再現性が必要な場合の決定的生成

### 投稿先プラットフォーム拡張

- **Bluesky** Publisher (`atproto` Python SDK、App Password 認証)
- **Telegram** Publisher (Bot API、`sendPhoto`)
- **Misskey / Mastodon** Publisher (ActivityPub、複数インスタンス対応)
- **X (Twitter)** Publisher (Free tier 月500投稿の制約付きで実装、利用者責任)
- **Threads** Publisher (Meta Graph API)
- **LINE Messaging API** Publisher (公式アカウント運用、月200通制限)
- **Microsoft Teams** Publisher (Webhook)
- **汎用 Webhook** Publisher (任意のエンドポイントへ POST)

これらはコミュニティからの PR 歓迎ポリシーで運用する想定。

### OSS としての整備

- **ライセンス・著作権ガイドライン**: 生成物の利用範囲、参照素材の権利関係、商用利用の可否を明文化
- **テンプレート化の強化**: GitHub Template Repository としての公式設定、初回セットアップウィザード CLI (`yonkomatic init`)
- **i18n**: README・ドキュメント・CLI メッセージの英語化
- **デモ用キャラセット**: CC0 ライセンスの簡易キャラ（幾何学的シェイプなど）を別リポジトリ `yonkomatic-examples` として提供
- **コンテンツガイドライン**: 投稿時の自動 NSFW チェック、有害表現フィルタ

### 運用・スケール

- **アーカイブの自動クリーンアップ**: 半年超のエピソード画像を GitHub Releases に移動してリポジトリ肥大化を防ぐ
- **モニタリング**: 生成失敗率、Publisher 成功率、API コスト推移を可視化するダッシュボード（GitHub Pages 上）
- **コスト最適化**: 月次でのコスト集計、しきい値超過時のアラート
- **テスト戦略の強化**: ゴールデンファイルベースの統合テスト、画像生成のメタデータレベルでの回帰テスト
- **複数同時運用**: 1リポジトリで複数キャラセット・複数チャンネルへの並行配信
- **マルチ言語対応**: 日本語以外の言語で漫画生成（英語、中国語、韓国語）

### コミュニティ機能

- **読者からのフィードバック反映**: Slack/Discord のリアクション集計、人気エピソードの傾向をシナリオ生成にフィードバック
- **エピソードリクエスト**: 読者が特定テーマをリクエストできる仕組み
- **アーカイブの検索性**: 静的サイトに全文検索（Pagefind 等）

---

## 既知のリスクと対応

| リスク | 対応 |
|---|---|
| Gemini が日本語テキストを綺麗に書けない | `text_rendering.mode: fallback` で PIL 描画にフォールバック |
| キャラのドリフト | 参照画像3-5枚、衣装明示、ロードマップでリファレンスプール成長 |
| Gemini API レート制限/障害 | エクスポネンシャルバックオフ、3回失敗で過去画像フォールバック |
| 時事ネタで炎上 | プロンプトで政治・災害・実在人物を明示禁止、ムード反映のみ |
| シナリオ枯渇 | 緊急シナリオその場生成、Publisher通知 |
| GitHub Actions 6時間制限 | 通常5分以内、リトライ込みでも余裕 |
| Secret 漏洩 | Repository Secrets のみ、コードへの直書き禁止、`.env` は gitignore |
| 一部 Publisher の障害が全体停止に波及 | Publisher は並列・独立実行、失敗は記録するが他に影響させない |
| OSS としての著作権 | examples にはテキストのみ、参照画像は利用者が用意。LICENSE で利用者の生成物への責任を明示 |

---

## 着手前の確認事項

実装着手時、以下は最新ドキュメントで必ず確認：

- Gemini 3.1 Flash Image の最新モデルID（preview から正式版に変わっている可能性）
- `google-genai` SDK の最新APIシグネチャ（このドキュメントのコード例は変わっている可能性あり）
- Slack `files_upload_v2` の最新仕様
- Discord Webhook の multipart 投稿の最新仕様
- Anthropic SDK のメッセージ API の最新形

---

## 着手指示

1. このドキュメントを読み込み、不明点があれば筆者に確認
2. Step 1 から順に実装
3. 各 Step 完了時に動作確認 + 簡潔なコミットでマージ
4. 各 Step 完了時に筆者にレビュー依頼
5. 設計判断が必要な箇所（特にOSSとして公開する観点で迷う箇所）は勝手に進めず確認

最初の作業は **Step 1 の土台**。リポジトリ初期化と Slack 疎通までを一気通貫で。
