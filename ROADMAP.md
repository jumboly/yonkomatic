# Roadmap & Progress

このファイルは yonkomatic 実装進捗の **ライブステータス** です。Step 完了ごと・重要決定ごとに更新します。新セッションは必ずこのファイルを読んでから着手してください。

設計の原典は [`SPEC.md`](SPEC.md)。本ファイルは「いま何ができていて、次に何をやるか」のサマリ。

---

## 現在地

- **完了**: Step 1, Step 2, Step 3, Step 4, **Step 5 (5a/5b/5c/5d 全て + simplify)**
- **次**: Step 6 (OSS 公開準備)
- **ブロッカー**: なし

最終更新: 2026-05-09 (Step 5 完了)

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

### ✅ Step 4 — 週次シナリオ + 時事ネタ + 自動化 (完了)

サブステップ単位で commit。

- ✅ **Step 4a — `scenario/generator.py` + `generate-scenarios` CLI** (commit `76e8061`)
  - `scenario/generator.py`: `generate_week(claude, pack, week, news_headlines=None) -> ScenarioWeek` (1 コール 7 話一括、`_TEMPERATURE=0.8` / `_MAX_TOKENS=8192`)
  - 応答パース: ``` フェンス → ブレース平衡スキャンの 2 段で前置き混入に耐性
  - `yonkomatic generate-scenarios [--week] [--out] [--no-news] [--force]`
  - `--week` 省略時は今日含む ISO 週を自動算出
  - テーマ解決: `themes/{YYYY-MM}.md` 優先 → `default.md` フォールバック
  - 実 API で 2026-W19 の 7 話生成 → `publish --dry-run` で Step 3 パイプラインまで通る確認済み
- ✅ **Step 4b — `news/fetcher.py` 統合** (commit `3a6a033`)
  - `news/fetcher.py`: `fetch_recent_headlines(news_cfg) -> list[str]`、feedparser で feed 単位の例外を吸収
  - socket timeout を 15s でスコープ設定 (stalled feed が weekly cron をハングさせないため)
  - `generate-scenarios` で `cfg.news.enabled` かつ `--no-news` 未指定なら自動 fetch
  - `yonkomatic test news` 追加、`pyproject.toml` に `feedparser>=6.0`
  - 実フィードで 16 headlines → 2026-W20 を生成、SPEC 安全指針通り訃報・実在人物が直接反映されない確認
- ✅ **Step 4c — GitHub Actions cron + `publish-today`** (commit `4b76c68`)
  - `.github/workflows/weekly-scenarios.yml`: 日曜 14:00 UTC (= 23:00 JST) cron + `workflow_dispatch`、`TZ=Asia/Tokyo date -d '+1 day' +%G-W%V` で **翌週の ISO 週** を計算して `generate-scenarios --week ...`、scenarios/ を bot commit
  - `.github/workflows/daily-publish.yml`: 毎日 00:00 UTC (= 09:00 JST) cron、`publish-today` 後に state.json + docs/ + output/archive/ を bot commit
  - `yonkomatic publish-today [--date]` 新コマンド: pub_date から ISO 週を逆算 → scenarios/{week}.json をロード → state の `current_week_index`/`last_published_episode` から次 episode 番号を選択 (週またぎは 1 にリセット)
  - 既存 `publish` 関数の本体を `_publish_episode_pipeline()` ヘルパに切り出し、`publish` と `publish-today` で共有
  - ローカル `publish-today --dry-run` で `scenarios/2026-W19.json` から episode 2 が自動選択されパイプライン通過確認済み
  - 利用者ブランチで `.gitignore` の `/scenarios/` `/state/` `/output/` `/docs/*` を外す (or `git add -f` を使う) 必要あり — SETUP.md (Step 5) で記述予定
- ✅ **Step 4d — エラー通知** (commit `83bd54b`)
  - `SlackPublisher.notify_failure(text) -> bool`: `chat_postMessage` を投げ、失敗は false (例外昇格させない)
  - `cli.py` に `_notify_failure(cfg, message)` ヘルパ。Slack publisher が `enabled` かつ token/channel 揃っているときだけ送信、それ以外は stderr ログのみ
  - `publish-today` の 3 つの障害ポイントで通知:
    - `scenarios/{week}.json` 不在 (シナリオ枯渇)
    - 該当 episode 不在 (週内 8 話目以上要求)
    - `_publish_episode_pipeline` が `typer.Exit` を上げた (Claude/Gemini/Compose/Validate/Publish のいずれか)
  - Slack 通知が成功すれば `· notified Slack: ...`、失敗すれば `notify failed: ...` を stderr に
  - `ANTHROPIC_API_KEY=invalid` で 401 → Slack に :warning: を確認、scenarios 不在ケースも同様に通知発火確認済み (exit code 1 を維持)

完了条件: 1 週間放置して 7 話自動投稿できる。weekly/daily ワークフローのライブ運用は利用者ブランチで `workflow_dispatch` 手動 trigger → cron 観察で検証する。

### ✅ Step 5 — 日本語テキストオーバーレイ (composer fallback 本実装) (完了)

**背景**: Step 4 のライブ検証で `text_rendering.mode = never` (Gemini に直接日本語を描画させる) が **複数吹き出しのある画面で破綻** することが判明。Step 2 の単体テストでは 1K でも綺麗に描けたが、本番で生成した「朝のコーヒーと光の角度」(2026-W19 ep1) では吹き出し内に「うんこ」「マチカカおっちょっ〜」「そんこい？」「わんもおきっちーすん」「やってどうより聞かないけど〜」のような **意味不明な日本語の幻覚** が描かれた。Gemini 3.1 Flash Image は複数の吹き出しを画面内に配置するときに「日本語っぽい記号列」を出力する傾向がある。

SPEC.md の元々の設計は PIL でテキストを後段オーバーレイする方針 (mode `fallback`/`always`)。Step 3 で composer.py をスタブ化したまま残していた本体を、ここで実装する。

**完了条件**: scenarios/ の dialogue が画像内に **正確な日本語** で表示される (シナリオ JSON のテキストと一字一句一致)。

サブステップ進捗 (`/simplify` 1 回 = `4ed0412`):

- ✅ **Step 5a — Gemini プロンプト変更 + Dialogue.kind 追加** (commit `550edc6`、空吹き出し対策強化 = `4c18d29`)
  - `panel/description.py` SYSTEM_PROMPT に「吹き出し・テキストを画像内に一切描画させない」「キャラの上部・横に空白スペースを残す」「英語で `absolutely no speech bubbles, no text, no captions, no letters` をプロンプトに必ず含める」を明示
  - `panel/description.py` `_format_panel()` の dialogue 行を `dialogue (do NOT render as text in the image; for composition hints only):` に変更し、台詞は表情・ポーズの hint として残しつつ描画指示でない旨を二重ガード
  - `scenario/schema.py` `Dialogue` に `kind: Literal["speech","thought","shout"] = "speech"` 追加。デフォルト "speech" で旧 JSON (kind フィールドなし) も互換読み込み可能
  - `scenario/generator.py` SYSTEM_PROMPT サンプルと厳守事項に kind の指示を追加
  - 検証: ローカル `test panel` 1 回で 4 panel 全件で文字・吹き出しゼロ、各 panel に吹き出し配置用の空白を確保した画像を確認
- ✅ **Step 5b — `panel/composer.py` の PIL 本実装** (commit `4fba95f`)
  - mode `fallback`/`always` 同一処理 (Gemini が文字を描かなくなる前提なので fallback と always を区別する意味がない)
  - 4 panel 縦等分割 + dialogue 件数 (1/2/3/4) で固定座標配置
  - kind による形状切替: `speech` → `bubble_style` 設定値 (round/rectangle/cloud) / `thought` → 雲形 (8 ローブ + 中央楕円) / `shout` → 14 角の星型バースト
  - フォントサイズは `panel_h * 0.072` を基準に縮小ループで吸収 (1K で 18px、2K で 36px 相当)
  - 横幅基準のグラフェム単位ラップ (`font.getlength`) + 簡易禁則 (`、。」』）)】` を行頭にしない)
  - cloud/burst は bbox を 1.18x / 1.30x 膨らませて lobe/spike が text を侵食しないよう補正
  - 画像 MIME と拡張子の整合は `image.format` を round-trip して維持 (JPEG は `quality=95, subsampling=0`)
  - `cli.py` の `compose()` 呼び出しに `bubble_style=cfg.text_rendering.bubble_style` 引数追加
  - `scripts/install_fonts.py`: notofonts/noto-cjk が `NotoSansJP-Regular.otf` を main から削除したため URL を `NotoSansCJKjp-Regular.otf` (16MB) に切替。ローカル保存名は維持
  - 検証: ローカル smoketest で 1K Gemini 出力に dialogue 件数 0/1/2/3 + kind speech/thought/shout を全網羅で目視確認
- ✅ **Step 5c — config デフォルト切替 + GHA フォント install/cache** (commit `9c04939`)
  - `config.yaml` / `config.py` の `text_rendering.mode` デフォルトを `never` → `always` に変更 (`bubble_style` コメントに「kind="speech" のみに適用」を明記)
  - `.github/workflows/daily-publish.yml`: `Install dependencies` の直後・`Publish today's episode` の直前に `actions/cache@v4` (静的キー `noto-sans-jp-otf-v1`) + 条件付き `Install fonts` ステップを追加
  - 検証: ローカル `publish --scenario-file examples/minimal/sample-scenario.json --dry-run` で 4 panel × 5 dialogue 全件、生成画像の日本語が scenario JSON と一字一句一致することを確認 (`output/archive/2026-05-09.jpg`)
- ✅ **Step 5d — live ブランチ実 cron / `workflow_dispatch` 検証** (live merge `66b73b3`、空吹き出し fix の live 反映 `b6508b5`)
  - main を live に merge → push origin live で本番デプロイ
  - live `workflow_dispatch` 1 回成功確認 (cache miss → Install fonts → publish)
  - ローカル `publish --dry-run` で 2026-W19 ep2〜ep7 (6 話) を回し、scenario JSON と画像内テキストが一字一句一致することを確認 (`output/archive/2026-05-12〜17.jpg`)
  - 6 話検証中に「Gemini が空の吹き出し型シェイプを描く」cosmetic 問題を発見 → SYSTEM_PROMPT に「空/text-less な吹き出しも禁止」「白い形状は実物体のみ (paper, cloth, sky, fog)」を追加し ep2/ep4 で再検証、空白楕円が完全消失することを確認 (Step 5a 強化として `4c18d29`)
  - 翌日以降の cache-hit 確認は cron に委ね、本実装としては完了とした

### ⏳ Step 6 — OSS 公開準備 (旧 Step 5) (次)

- README に Quick Start + デモ画像
- SETUP.md を fork / branch 戦略まで含めて拡充 (`.gitignore` 緩和、Default branch = live、Secrets、Workflow permissions の手順)
- ユニットテスト (API はモック)
- GitHub Template Repository 設定
- LICENSE / CONTRIBUTING.md
- 自分の素材で稼働させた本番サンプルを README に掲載

完了条件: 第三者が README 通り 30 分以内で自分の漫画ボットを立ち上げられる。

---

## 直近の決定事項 (Decisions Log)

新しい決定が出たら頭に追加。古いものは削除せず残す。

- **2026-05-09 (Step 5 simplify)** `composer._wrap_japanese` は文字単位 measurement の累積で O(n) (元は累積文字列の全長を毎反復で測る O(n²))。戻り値を `(lines, widths)` のタプルにして `_draw_one_bubble` 側の重複測定を排除。kind/style 分岐は `_select_drawer` + `_SPEECH_DRAWERS` dict にフラット化し、5 段 if/elif を回避。
- **2026-05-09 (Step 5d 検証で確定)** Gemini は日本語幻覚を抑え込んだ後も「空の楕円・白い吹き出し型シェイプ」を稀に描く (ep2/ep4 で再現)。読者からは「翻訳抜け」に見える致命的な見栄え問題のため、Claude の英プロンプトに `no empty/blank/text-less bubbles`、`no white rounded shapes overlaid on the scene`、`any white area must be a real diegetic object (paper, cloth, sky, fog)` を必ず含める要件を SYSTEM_PROMPT で強制。再生成で空白楕円ゼロを確認。
- **2026-05-09 (Step 5b 実装で確定)** `Dialogue.kind` を `Literal["speech","thought","shout"]` で追加 (デフォルト "speech")。`config.text_rendering.bubble_style` は `kind="speech"` の場合のみ参照され、`thought` は雲形・`shout` は星型バーストに固定される。kind 拡張時 (e.g. "shout-soft") は `panel/composer.py` の `_select_drawer` 分岐に追加し、generator SYSTEM_PROMPT も更新する。
- **2026-05-09 (Step 5b 実装で確定)** `panel/composer.py` の cloud / burst は bbox を 1.18x / 1.30x 膨らませてから描画する。lobe (cloud) や spike (burst) は外周に張り出すので、テキスト幅で計算した bbox にそのまま描くと先頭・末尾の文字がスパイクと重なって視認性が落ちる。スパイク内側比率 0.78 / lobe 32% を逆算しての固定倍率。
- **2026-05-09 (Step 5b 実装で確定)** `notofonts/noto-cjk` リポジトリは `Sans/OTF/Japanese/NotoSansJP-Regular.otf` を main から削除済み。`scripts/install_fonts.py` の URL を `NotoSansCJKjp-Regular.otf` (16MB、CJK 全部入りの region-targeted regular OTF) に切り替えた。ローカル保存名 `NotoSansJP-Regular.otf` は維持 (composer 等への影響なし)。
- **2026-05-09 (撤回・再判断)** `text_rendering.mode = never` (Gemini に日本語を直接描かせる) を Step 2-4 で採用していたが、Step 4 ライブ検証で **複数吹き出しの画面で文字化け** することが判明。Step 5 で composer.py の `fallback`/`always` を本実装 + デフォルトを `always` に変更する。Step 2 の単体テストは 1 吹き出しのみだったため検出できなかった。1K → 2K の解像度上げでも保証できないので、PIL でテキスト合成する SPEC 元々の設計に戻す。
- **2026-05-09** Step 5 として「composer fallback 本実装」を OSS 公開準備の **前に** 挟む。日本語が読めない 4 コマを公開するわけにはいかないため。旧 Step 5 (OSS 公開準備) は Step 6 に番号繰り下げ。
- **2026-05-09** エラー通知は **既存 SlackPublisher を流用**して `notify_failure` メソッドを生やす方針 (新モジュールは作らない)。Discord 通知は Step 5 以降。Slack publisher が disabled / 認証情報未設定の場合は stderr ログにフォールバック。
- **2026-05-09** `publish-today` は `_publish_episode_pipeline` を `try: ... except typer.Exit` でラップして cron-level コンテキスト (date / episode / week / title) を含めた通知メッセージを送る。pipeline 内部のエラーメッセージはそのまま console に流し、通知は要約だけにする (Slack の表示が短い + GHA log で詳細は追えるため)。
- **2026-05-09** weekly-scenarios cron は「翌週」を生成する。日曜 23:00 JST は ISO 週の最終時間で、その時点の `isocalendar()` はまだ今週を返すため、`TZ=Asia/Tokyo date -d '+1 day'` で次週を明示計算。daily-publish 側は `--date` (デフォルト today) → `_iso_week_of(...)` で逆算するので「月曜から正しく新シナリオを引く」フローが両側で整合する。
- **2026-05-09** publish と publish-today は `_publish_episode_pipeline()` (内部ヘルパ) を共有。同じ Stage1-6 を 2 ヶ所に書きたくないため、scenario の **取得方法** だけが分岐するインターフェースに揃えた。
- **2026-05-09** GitHub Actions ワークフローの commit/push は **利用者ブランチ前提**。main の `.gitignore` で `/scenarios/`/`/state/`/`/output/`/`/docs/*` は無視されているので、利用者は fork 後に該当パスを `.gitignore` から外す (or 該当ファイルを `git add -f`)。SETUP.md (Step 5) で具体的な手順を案内。
- **2026-05-09** news fetcher は **feed 単位で例外吸収**して空 list を返す方針。Publisher の独立性 (1 つの障害が全体を倒さない) と同じ思想で、ニュース取得失敗はシナリオ生成を止めない。
- **2026-05-09 (訂正)** Step を分割して commit する場合でも、`/simplify` は **Step 全体完了時に 1 回だけ** 回す (サブステップ毎の細粒度レビューは粒度過剰)。サブステップ毎の commit リズムは維持。
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

### シナリオ生成・品質改善 (Step 4 レビューで判明)

- `summary_no_spoiler` がオチを匂わせる問題の SYSTEM_PROMPT 強化 (例: 2026-W19 ep7「マチカの行動が鍵だった」)
- 過去 2〜4 週分の `summary_no_spoiler` を generator に渡してネタ被り (朝のコーヒー / 新緑散歩 / そら豆など) を避ける
- 連続生成された複数週シナリオを比較して重複度を機械的にチェックする lint コマンド

### テキストオーバーレイの将来課題 (Step 5 完了後)

- 吹き出し位置の自動検出 (Gemini が描いたフキダシ的空白領域を OpenCV / PIL で検出して PIL 配置と一致させる)
- 吹き出し種別の `ScenarioEpisode.Dialogue` への追加 (`kind: "speech" | "thought" | "shout"` で `bubble_style` を切り替え)
- フォントサイズの動的調整 (台詞の長さで縮小)
- 縦書きオプション

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
