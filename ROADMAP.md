# Roadmap & Progress

このファイルは yonkomatic 実装進捗の **ライブステータス** です。Step 完了ごと・重要決定ごとに更新します。新セッションは必ずこのファイルを読んでから着手してください。

設計の原典は [`SPEC.md`](SPEC.md)。本ファイルは「いま何ができていて、次に何をやるか」のサマリ。

---

## 現在地

- **完了**: Step 1, Step 2, Step 3, **Step 4a (scenario generator)**
- **次**: Step 4b (news/fetcher.py 統合)
- **ブロッカー**: なし

最終更新: 2026-05-09 (Step 4a 完了時)

---

## Step 進捗

### ✅ Step 1 — 土台 + Slack 疎通 (commit `2216b0a`)

- uv ベースの Python パッケージ骨格 (`src/yonkomatic/`)
- typer ベースの CLI (`yonkomatic --help`, `version`, `test slack`)
- `config.yaml` + `.env` 読み込み (Pydantic)
- `Publisher` Protocol と `SlackPublisher` (`files_upload_v2`)
- `examples/minimal/` のテキストサンプル一式
- `.github/workflows/test-slack.yml` (workflow_dispatch 専用)
- ローカル & GitHub Actions の両方から Slack 投稿成功確認済み

### ✅ Step 2 — 画像生成コア (commit `a3d6f70`)

- `scenario/schema.py` (Episode / Panel / Dialogue / ScenarioWeek)
- `ai/claude_client.py` (Anthropic SDK ラッパ、Messages API)
- `ai/gemini_client.py` (google-genai ラッパ、429/5xx/NO_IMAGE retry 内蔵)
- `panel/description.py` (シナリオ + content pack → 英語統合プロンプト)
- CLI: `test gemini`, `test panel`
- MIME 自動補正 (Gemini が JPEG を返す場合に拡張子調整)
- 開発デフォルト: `image_size: "1K"` (本番品質確認時に 2K へ)
- end-to-end 実 API で 4 コマ漫画生成成功 (`output/test-panel.jpg`)

### ✅ Step 3 — E2E パイプライン + マルチパブリッシュ (commit `1eff27f`)

スコープを軽量化した E2E パイプラインを実装。完了条件「1 コマンドでシナリオ → 画像 → 複数プラットフォーム同時投稿」を Slack + static_site の 2 系統で達成。

実装内容:

- `panel/composer.py` — `mode=never` (デフォルト) はパススルー。`fallback`/`always` は `NotImplementedError`。1K Gemini が日本語を描けるのでオーバーレイは保留
- `panel/validator.py` — スタブ (常に OK)。Gemini Vision 自己チェックは Step 4 以降の課題
- `state/repo.py` — `StateData` / `HistoryEntry` (Pydantic) + `StateStore` (atomic write、auto_commit メソッド)。auto_commit は Step 4 cron 用に用意するだけで publish からは呼ばない
- `publisher/static_site.py` — Jinja2 で `docs/index.html` + `docs/posts/{date}.html` + `docs/images/{date}.{ext}` + `docs/css/style.css` を出力。最大 30 件 / 最新順 / `.posts-index.json` で内部メタ管理
- `yonkomatic publish --scenario-file PATH [--date YYYY-MM-DD] [--dry-run]` コマンド
- `concurrent.futures.ThreadPoolExecutor` で Publisher 並列化、各 Publisher 失敗は `PublishResult(ok=False)` で独立
- アーカイブ書き出し: `output/archive/{date}.{png|jpg}` + `{date}.json` (フラット構造、Gemini が JPEG を返したら拡張子も自動連動)

未実装 (Step 3 で意図的に切り出し):

- `publisher/discord.py` — Step 4 以降。`config.yaml` の `discord.enabled: true` 時は警告ログのみ
- PIL テキストオーバーレイ — `text_rendering.mode` の `fallback`/`always` モード本体
- Gemini Vision 品質チェック

### ⏳ Step 4 — 週次シナリオ + 時事ネタ + 自動化 (進行中)

サブステップ単位で commit する方針。

- ✅ **Step 4a — `scenario/generator.py` + `generate-scenarios` CLI** (このコミット)
  - `scenario/generator.py`: `generate_week(claude, pack, week, news_headlines=None) -> ScenarioWeek` (1 コール 7 話一括、temperature=0.8、max_tokens=8192)
  - 応答パース: ``` フェンス → ブレース平衡スキャンの 2 段で前置き混入に耐性
  - `yonkomatic generate-scenarios [--week] [--out] [--no-news] [--force]` を追加
  - `--week` 省略時は今日含む ISO 週を自動算出
  - テーマファイル解決: `themes/{YYYY-MM}.md` 優先、なければ `default.md` (SPEC L125 と既存 publish の食い違いを generate 側で吸収)
  - 実 API で 2026-W19 の 7 話生成 → episode 1 を `publish --dry-run` に流して Step 3 パイプラインまで通る確認済み
- ⏳ **Step 4b** — `news/fetcher.py` (feedparser で RSS)、`generate-scenarios` の自動 fetch 統合、`yonkomatic test news`
- ⏳ **Step 4c** — `.github/workflows/weekly-scenarios.yml` (日曜 23:00 JST) + `daily-publish.yml` (毎日 9:00 JST)、`yonkomatic publish-today` (state から episode 自動選択)
- ⏳ **Step 4d** — `SlackPublisher.notify_failure()` + `publish-today` の障害通知挿入

完了条件: 1 週間放置して 7 話自動投稿できる。

### ⏳ Step 5 — OSS 公開準備 (未着手)

- README に Quick Start + デモ画像
- SETUP.md を fork / branch 戦略まで含めて拡充
- ユニットテスト (API はモック)
- GitHub Template Repository 設定
- LICENSE / CONTRIBUTING.md
- 自分の素材で稼働させた本番サンプルを README に掲載

完了条件: 第三者が README 通り 30 分以内で自分の漫画ボットを立ち上げられる。

---

## 直近の決定事項 (Decisions Log)

新しい決定が出たら頭に追加。古いものは削除せず残す。

- **2026-05-09** Step 4 はサブステップ 4a/4b/4c/4d で commit を分ける。各完了時に `/simplify` レビュー + ROADMAP 更新 + ユーザーレビュー依頼。
- **2026-05-09** 週次シナリオ生成は **毎回 Claude を叩く**。`scenarios/{week}.json` は `--force` がない限り上書きしない (誤って上書きすると過去アーカイブとの整合が壊れるため)。
- **2026-05-09** `generate-scenarios` は月別テーマ (`themes/{YYYY-MM}.md`) があれば優先、なければ既存 `default.md` にフォールバック。SPEC.md L125 の月別仕様と既存 `panel/description.py` の `default.md` 既定を generator 側でブリッジ。`publish` (Step 3) の挙動は据え置き。
- **2026-05-09 (再決定)** ROADMAP.md / SPEC.md を `docs/` から **リポジトリルート** に移動。`static_site.output_dir` は `./docs` のまま (一度 `./site` に変えたが、GitHub Pages の "Deploy from a branch" が `/(root)` か `/docs` しか選べないため戻した)。docs/ は今後 Pages 公開用、ドキュメントはルート直下で OSS 慣例 (`README.md` / `CLAUDE.md`) に揃える。`.gitignore` は docs/ の生成物 (`index.html` / `posts/` / `images/` / `css/` / `.posts-index.json`) のみ ignore。
- **2026-05-09** `text_rendering.mode` のデフォルトを `fallback` → **`never`** に変更。Step 2 の検証で 1K でも Gemini が日本語を綺麗に描けたため。`fallback`/`always` を opt-in した利用者には `NotImplementedError` で気付かせる方針。
- **2026-05-09** Step 3 で `panel/composer.py` はパススルー、`panel/validator.py` はスタブに留める。Discord publisher は Step 4 以降に先送り。Slack + static_site の 2 系統で E2E を成立させた。
- **2026-05-09** Publisher 並列実行は `concurrent.futures.ThreadPoolExecutor`。既存 SDK (slack-sdk / google-genai / anthropic) がすべて同期 API のため。
- **2026-05-09** アーカイブはフラット構造 `output/archive/{date}.{ext}` + `{date}.json`。月別ディレクトリ整理は将来の運用判断 (アーカイブが膨らんだら検討)。
- **2026-05-09** static_site の画像 URL は MIME 由来の拡張子を保持 (`.posts-index.json` に `image_filename` フィールド)。Gemini が JPEG を返しても Content-Type 不整合にならない。
- **2026-05-09** publish コマンドの全 Publisher 失敗時は `state.json` を更新せず exit 1。一部成功時は state を更新して exit 0 (成功した Publisher への重複投稿を避けるため)。
- **2026-05-08** Co-Authored-By 行は **付けない**。コミットフックが「捏造」として拒否するため。
- **2026-05-08** 開発デフォルトの `image_size` を **2K → 1K** に。本番品質確認時のみ 2K。
- **2026-05-08** `.gitignore` のランタイムデータパターンに先頭 `/` を付けてリポジトリルート限定 (`/scenarios/`, `/output/`, `/state/`)。`src/yonkomatic/state/` などの巻き込み防止。
- **2026-05-08** パッケージレイアウトは `src/yonkomatic/` (src layout)。
- **2026-05-08** Co-Authored-By を許可するための hook 調整は未対応 (要望次第で別途)。

---

## 既知の挙動・注意 (Gotchas)

- **Gemini NO_IMAGE**: 抽象的すぎるプロンプト (例: "simple test") は `FinishReason.NO_IMAGE` で 3 連続失敗する。具体的な被写体・画風記述が必要。retry はあくまで非決定性に対する保険。
- **Gemini Free Tier では本モデル使用不可**: `gemini-3.1-flash-image-preview` は Paid tier 必須。Google Cloud プロジェクトで billing 有効化が前提。
- **Gemini 出力は JPEG が混じる**: API は `output_mime_type` を Gemini API では受け付けない。CLI で MIME に応じて拡張子を補正している (archive と static_site の両方で連動)。
- **Anthropic SDK バージョン**: `anthropic>=0.100.0` を使用 (`messages.create` API)。
- **Anthropic 529 overloaded**: `claude-sonnet-4-6` がピーク帯に overloaded を返すことがある。SDK の `max_retries=2` (デフォルト) でも貫通したら少し待って再実行で解決。`yonkomatic publish` は失敗時 state.json を更新せず exit 1 するので、CI で再試行可能。

---

## バックログ (Step 5 以降の継続検討項目)

[`SPEC.md` のロードマップセクション](SPEC.md#ロードマップphase-5-完了後の継続検討項目)から抜粋。Issue 化は OSS 公開後に。

### 画像生成・品質改善

- キャラリファレンスプールの自動成長
- per-panel + composite フォールバックモード
- キャラドリフト検出 (埋め込みベクトル類似度)
- シード固定オプション

### 投稿先プラットフォーム拡張

- Bluesky / Telegram / Misskey / Mastodon / X / Threads / LINE / Microsoft Teams / 汎用 Webhook

### OSS としての整備

- ライセンス・著作権ガイドライン明文化
- `yonkomatic init` セットアップウィザード
- README/ドキュメント i18n (英語版)
- CC0 デモキャラセット (別リポジトリ)
- NSFW / 有害表現フィルタ

### 運用・スケール

- アーカイブ自動クリーンアップ (GitHub Releases へ移動)
- モニタリングダッシュボード
- 月次コスト集計 + 閾値アラート
- ゴールデンファイル統合テスト
- 複数キャラセット並行配信
- 多言語対応 (英語・中国語・韓国語)

### コミュニティ機能

- リアクション集計でシナリオ生成にフィードバック
- 読者からのテーマリクエスト
- 静的サイト全文検索 (Pagefind 等)

---

## 更新ルール

新セッション (または進捗があった時) は以下を維持:

1. 「現在地」セクションの **完了 / 次 / ブロッカー / 最終更新** を更新
2. 完了 Step に commit hash を残す
3. 重要な決定は「直近の決定事項」に **日付付きで追記**
4. ハマりポイントは「既知の挙動・注意」に追加
5. バックログから着手したものは該当 Step セクションへ移す
