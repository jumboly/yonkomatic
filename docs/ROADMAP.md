# Roadmap & Progress

このファイルは yonkomatic 実装進捗の **ライブステータス** です。Step 完了ごと・重要決定ごとに更新します。新セッションは必ずこのファイルを読んでから着手してください。

設計の原典は [`docs/SPEC.md`](SPEC.md)。本ファイルは「いま何ができていて、次に何をやるか」のサマリ。

---

## 現在地

- **完了**: Step 1, Step 2
- **次**: Step 3 (E2E パイプライン + マルチパブリッシュ)
- **ブロッカー**: なし

最終更新: 2026-05-08 (Step 2 完了時)

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

### 🚧 Step 3 — E2E パイプライン + マルチパブリッシュ (次)

予定実装:

- `panel/composer.py` — PIL でテキストオーバーレイ (Gemini 描画失敗のフォールバック)
- `panel/validator.py` — Gemini 自己チェック (品質スコアリング、再生成ループ)
- `state/repo.py` — `state/state.json` 読み書き + 自動 commit ヘルパ
- `publisher/discord.py` — Discord Webhook (multipart/form-data)
- `publisher/static_site.py` — GitHub Pages 互換出力 (Jinja2 利用)
- `yonkomatic publish --episode N [--dry-run]` コマンド
- 並列 Publisher + 各 Publisher 失敗の独立化
- アーカイブ書き出し (`output/archive/{date}.png` + メタ JSON)

完了条件: 1 コマンドでシナリオ → 画像 → 複数プラットフォーム同時投稿が通る (実 Publisher は最低 Slack + 静的サイト で確認)。

着手時の確認事項:
- Discord Webhook の URL を `.env` / Secrets に登録するか
- 静的サイトの `base_url` は GitHub Pages 公開後に追記 (Step 3 中盤)
- `text_rendering.mode` のデフォルトは現状 `fallback` だが、1K でも Gemini が綺麗に描けたので Step 3 では `never` (オーバーレイなし) でも実用可能。後から切り替え

### ⏳ Step 4 — 週次シナリオ + 時事ネタ + 自動化 (未着手)

- `news/fetcher.py` (feedparser で RSS)
- `scenario/generator.py` (Claude 週次 7 話一括)
- `.github/workflows/weekly-scenarios.yml` (毎週日曜 23:00 JST cron)
- `.github/workflows/daily-publish.yml` (毎日 9:00 JST cron)
- エラー時の Publisher 通知

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

- **2026-05-08** Co-Authored-By 行は **付けない**。コミットフックが「捏造」として拒否するため。
- **2026-05-08** 開発デフォルトの `image_size` を **2K → 1K** に。本番品質確認時のみ 2K。
- **2026-05-08** `.gitignore` のランタイムデータパターンに先頭 `/` を付けてリポジトリルート限定 (`/scenarios/`, `/output/`, `/state/`)。`src/yonkomatic/state/` などの巻き込み防止。
- **2026-05-08** パッケージレイアウトは `src/yonkomatic/` (src layout)。
- **2026-05-08** Co-Authored-By を許可するための hook 調整は未対応 (要望次第で別途)。

---

## 既知の挙動・注意 (Gotchas)

- **Gemini NO_IMAGE**: 抽象的すぎるプロンプト (例: "simple test") は `FinishReason.NO_IMAGE` で 3 連続失敗する。具体的な被写体・画風記述が必要。retry はあくまで非決定性に対する保険。
- **Gemini Free Tier では本モデル使用不可**: `gemini-3.1-flash-image-preview` は Paid tier 必須。Google Cloud プロジェクトで billing 有効化が前提。
- **Gemini 出力は JPEG が混じる**: API は `output_mime_type` を Gemini API では受け付けない。CLI で MIME に応じて拡張子を補正している。
- **Anthropic SDK バージョン**: `anthropic>=0.100.0` を使用 (`messages.create` API)。

---

## バックログ (Step 5 以降の継続検討項目)

[`docs/SPEC.md` のロードマップセクション](SPEC.md#ロードマップphase-5-完了後の継続検討項目)から抜粋。Issue 化は OSS 公開後に。

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
