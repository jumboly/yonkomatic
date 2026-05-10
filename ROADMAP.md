# Roadmap & Progress

このファイルは yonkomatic 実装進捗の **ライブステータス** です。Step 完了ごと・重要決定ごとに更新します。新セッションは必ずこのファイルを読んでから着手してください。

設計の原典は [`SPEC.md`](SPEC.md)。本ファイルは「いま何ができていて、次に何をやるか」のサマリ。

---

## 現在地

- **完了**: Step 1〜4, **Step 5 全部** (5a/5b/5c/5d + simplify), **Step 5e** (実装 + A/B 検証、本番採用見送り), **Step 6** (テンプレ化 + OpenAI 切替 + 構造刷新), **Step 6.5** (gpt-image-2 → 960x1280 本番採用、**W21 全 7 話で 7/7 完全一致を確証**), **Step 6.6** (Actions の batch 化 — 実装は Step 6.5 と一体で完了済み), **Step 7a** (生成物の gh-pages 分離 — workflow を gh-pages worktree + symlink 経由に切替、main からランタイムを完全分離), **Step 7b** (`batch-resubmit-missing` CLI + manifest `retries[]` + daily-publish への best-effort step 配線、上限 2 回・prompt reuse、ローカル 5 ケース目視 OK), **Step 7c** (CONTRIBUTING.md 新規作成 — fork 運用前提 + 開発ルール明文化、README から「貢献」節経由でリンク), **Step 7d** (pytest 6 ファイル / 44 ケース新設 — schema / state / panel / news / static_site / batch manifest をオフラインモック化、`.github/workflows/ci.yml` で PR + main push に lint+test、`[dependency-groups].dev` に統一), **Step 7e** (README 全面リライト — 6 節構成 = Status/Demo/Quick Start/How it works/位置付け/リンク集、W21 ep4+ep5 を `assets/demo/` に並べて本番品質サンプル提示、章立て表で gpt-5.4 / gpt-image-2 / Publisher Protocol を要約)、batch CLI、モデル別ガイダンス機構 (scenario / panel-prompt 両 LLM)、参考画像 LLM 告知配線
- **次**: **Step 7f** (SETUP.md 全面改訂 — `.gitignore` 緩和削除 + gh-pages deploy 設定 + batch リトライ運用) に着手 — Step 7 全体は 7a〜7h に分割済み (下記セクション参照)
- **ブロッカー**: Step 7a/7b の private fork 動作確認 (Step 7g 検証手順) は実環境がないと実施不可、コミット後に手動 dispatch で確認

最終更新: 2026-05-10 (Step 7e 実装完了 — README を 6 節構成にリライト、`assets/demo/` に W21 ep4 「静かな通知音」+ ep5 「傘の待機列」の 2 枚を本番品質サンプルとして配置、Demo URL は fork 後 `https://<your>.github.io/yonkomatic/` 例として注記)

### Step 6.5 余波の検証ログ (2026-05-10 W21 batch で 3 件すべて確証済み)

> 以下の 3 件は当初「次セッションでやる残課題」だったが、2026-05-10 の **W21 全 7 話 batch (7/7 完全一致)** で一括確証された。検証手法と判定根拠を歴史記録として保持。


**1. 新ガイダンスの画像レイヤ効果評価 — ep1/ep5 完了 (2026-05-10)**

評価対象:
- `tmp/batch-W19-imgs/ep1.png` (風の向きの会議) / `ep5.png` (音だけ先に夏)
- 元シナリオ: `tmp/W19-with-guidance.yaml` (新 guidance 適用、SFX 込み、verbatim 角度のキャラ anchor)
- batch manifest: `tmp/batch-W19-test.yaml` (status: completed, image batch $0.274 = sync の半額)
- ベースライン: `output/step6.5-gpt-image-2/2026-05-04.png` (ep1=風の予告) / `2026-05-08.png` (ep5=植木鉢の会議)
  - 注: ベースラインと新バッチは別シナリオ (W19 を再生成しているため)。同一エピソード比較ではなく、各々が自シナリオを忠実に描けたかと、Step 6.5 の品質水準 (6/7 完全一致) を維持/向上できたかで判定。

評価結果:

| 観点 | ベースライン (Step 6.5) | 新ガイダンス (ep1/ep5) |
|---|---|---|
| dialogue 一字一句一致 | 維持 (8/8 + 8/8) | 維持 (9/9 + 8/8) |
| 4 panel 厳守 | 維持 | 維持 |
| 話者スワップ | 1/7 で発生 (W19 全 7 話中) | 0/2 (サンプル少) |
| **SFX 描画** | **不明瞭/未描画** | **明確に scene art に描画 (ep1=2件, ep5=3件 全て)** |
| 吹出スタイル | 横書き中心 | 縦書き多め (日本語マンガらしい) |

**判定**: 新ガイダンス (Verbatim キャラ anchor / SFX 指示 / Sequential panel labels / Literal text in double quotes / Negative constraints 末尾集約) は **Step 6.5 の品質水準を維持しつつ SFX 描画を明確に改善**。特に ep5 では「りーん」が Panel 1/2/3 連続描画され、「音だけ先に夏」のオチが視覚的にも成立。

**残課題**: サンプル数 2 話のため確度を上げるには ep2/ep3/ep4/ep6/ep7 を batch 投入して 7 話完走で再評価すべき。本番デフォルト化判定はそれを待ってから。

**2. 画像サイズ最適化検討 — 1 話 4 サイズ完了 (2026-05-10)**

ep1 (風の向きの会議) を 768/960/1152/1536 で生成 (sync 計 $0.53)、視認比較:

| サイズ | 実コスト (sync) | batch 推定 | テキスト視認性 | SFX 描画 | キャラ造形 | 判定 |
|---|---|---|---|---|---|---|
| 768x1024 | $0.15 | ~$0.075 | 不足 (Slack で潰れる) | あり | 粗い | 不採用 |
| **960x1280** | **$0.18** | **~$0.09** | 読める (全 dialogue 識別可) | くっきり | 認識可 | **本命** |
| 1152x1536 | $0.20 | ~$0.10 | 綺麗 | 「ぶいーん」が矢印化 (1 サンプル) | 丁寧 | 候補 |
| 1536x2048 (現行) | $0.27 (Step 6.5 batch $0.137) | ~$0.14 | 綺麗 | 明確 | 丁寧 | 過剰気味 |

ROADMAP の旧見積もり「推定/枚」列は概ね sync 実コストと一致 (768 で乖離あり)。実コストは output_tokens に比例し、サイズ差ほどスケールしないことが判明 (768→1536 で output_tokens は約 1.85x のみ、ピクセル数は 4x)。

保存後ファイル:
- `tmp/size-comparison/ep1-768x1024.png` (1.46MB)
- `tmp/size-comparison/ep1-960x1280.png` (2.25MB)
- `tmp/size-comparison/ep1-1152x1536.png` (3.11MB)
- `tmp/batch-W19-imgs/ep1.png` (5.08MB, 1536x2048 既存)

**判定**: 本番デフォルトを **960x1280 に切替** (`config.yaml` 反映済み)。コスト -33% (1536x2048 比) で Slack/static_site の表示サイズ (端末で約 1024px に縮小される) に必要十分。印刷品質が必要な場合のみ 1536x2048 を CLI フラグ or config で opt-in。

**残課題**:
- 960x1280 で W19 全 7 話を batch 投入し、ガイダンス効果評価 (上記 1) と合わせて品質再検証
- 1152x1536 は SFX 表現リスク (1 例で「ぶいーん」が矢印アイコン化) のため、印刷向け中間解像度として将来検討候補

**3. 参考画像を LLM ステージにも渡す機構 (Option A + 軽量 B) — 実装完了 (2026-05-10)**

`pack.images` (`content/images/*`) を両 LLM ステージにも告知する配線を追加 (commit `f445b74` 実装 + `efc225d` examples/minimal/images/ に AI 生成リファレンス 3 枚を main 同梱)。

- **A 完了**: `ContentPack` に `reference_images_block` プロパティを追加 (空 list 時は空文字、画像ありなら `# 参考画像 (画像モデルに N 枚渡される)` セクション + Image 1: filename リスト + 「Image N 順序参照する」一文)。両テンプレ (`scenario_prompt.md` / `panel_prompt.md`) の system frontmatter に `{{reference_images_block}}` を差し込み (`news_block` と同パターン)
- **B 完了**: Image N 順序参照の guidance は block 内に集約 (`## 要件` に同じ bullet を重複させない方針 — block が画像ありのときだけ guidance を出すのでノイズが少ない)
- **C (将来)**: gpt-5.4 のマルチモーダル機能で実画像を LLM に見せる — 未着手

`examples/minimal/prompt.md` の `# 参考画像` セクションも書式例付きに差し替え (`Image 1 (01-yonko-front.png)`: ヨンコの正面立ち絵... のように利用者が各画像の意味を書ける書式)。

**残検証** (実 API):
- `uv run yonkomatic test panel --prompt "..."` (デフォルトは `--content content`) で出力英語プロンプトに `Image 1:` 等のインデックス参照が出ることを目視
- `uv run yonkomatic generate-scenarios --week 2026-W21` の `{week}.rendered.txt` system に `# 参考画像 (画像モデルに N 枚渡される)` セクションが含まれることを確認

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

### ✅ Step 5e — AI 描画モード切替 + Pro モデル検証 (実装 + 検証完了、本番採用は見送り)

**背景**: Step 5d のライブ運用で「AI が描いた吹き出しの方が PIL オーバーレイよりクオリティが高い」ことが見えてきた。Pro モデル (gemini-3-pro-image-preview) は公式にテキスト描画精度向上を謳うため、日本語が一字一句綺麗に出るならば PIL 後段合成より見栄えが良いので採用したい。

**スコープ**: PIL オーバーレイ vs AI 描画を **config + CLI フラグで切り替え可能** にし、A/B 検証できる足場を作る (実装)。Pro/Flash 両モデルでの日本語精度検証 (検証)。

**完了条件**: `--text-mode model_render --image-model gemini-3-pro-image-preview` 一発で AI 描画モードに切り替わり、A/B 比較ができる状態。検証で本番採用可否の判断材料が揃う。

実装内容:

- `text_rendering.mode` の literal を `pil_overlay` / `model_render` に **改名** (旧 `always` / `fallback` / `never` は廃止、開発段階のため後方互換は捨てた)
- `panel/description.py` に SYSTEM_PROMPT を 2 系統:
  - `SYSTEM_PROMPT_PIL_OVERLAY` (旧 `SYSTEM_PROMPT`、現行を維持) — Gemini に吹き出し・テキスト一切描かせない
  - `SYSTEM_PROMPT_MODEL_RENDER` (新規) — Gemini に吹き出し+正確な日本語を描かせる
- `_format_panel(panel, mode)` で dialogue 行のヘッダを mode 別に切替 (composition hint vs render-as-text)
- `panel/composer.py` の早期 return を `if mode == "model_render"` に。`pil_overlay` は従来の PIL 合成を実行
- `cli.py` の `publish` / `publish-today` / `test panel` に `--text-mode` `--image-model` フラグを追加。`_apply_cli_overrides()` ヘルパで pydantic 経由で revalidate しながら cfg を上書き
- `test panel` を Stage1+Stage2 から Stage1+Stage2+Stage3 (compose) に拡張 (両モードで本番と同じ最終出力が得られるように)
- `Dialogue.kind` (speech/thought/shout) は **`model_render` モードでは AI に渡さない** (純粋なモデル品質を見たい / 複数吹き出し+kind 分岐をモデルに要求すると負荷が上がるため)

**検証結果** (W20 全 7 話 × Flash + model_render = C 路線):

| | 完全一致 | 致命的バグ | 軽微な逸脱 |
|---|---|---|---|
| C (Flash + model_render) | 2/7 (29%) | 1/7 (14%) | 4/7 (57%) |

致命的バグ: ep5「収穫はあった。」→「収穫はお前あった。」(「お前」混入)。
軽微な逸脱: 三点リーダ抜け / 「苦笑い」ラベル混入 / 5 コマ化 / 文字重複疑い。

**プロンプト強化試行も実施**: `SYSTEM_PROMPT_MODEL_RENDER` に「文字数一致」「単語追加禁止」「4 コマ厳守」「吹き出し外テキスト禁止」を追加した v2 で再検証 → **悪化** (完全一致 3/7 だが致命的 3/7 に増加)。否定文を増やすと逆に「同じ台詞を 2 度描く」「単語を勝手に挿入」が誘発される LLM の典型症状。**v1 プロンプトに復帰してこのセッションでは打ち止め**。

**判定**: 致命的バグ 14% は本番運用に許容できないため、デフォルトは `pil_overlay` 維持。`model_render` は実装として温存し CLI フラグで opt-in 可能。

**今後の課題 (Step 5e バックログ)**:
- few-shot example をプロンプトに含める実験 (否定文より肯定例の方が誘導しやすい仮説)
- 1K → 2K でテキスト描画精度が上がるか検証 (コスト見合いの判断)
- Pro での 7 話検証 (B 路線、コスト高いが精度向上の可能性)
- Gemini 側のモデル世代が上がったタイミングで再検証

### ✅ Step 6 — 全面リファクタ (テンプレ化 + OpenAI + 構造刷新 + model_render 採用) (実装完了 commit `1646742`)

**背景**: Step 5e で `model_render` を本番見送りにした判断を、運用印象 ("8 割は達成できていた") と OpenAI への AI ベンダー集約を機に再評価。同時に content/ の 4 フォルダ構造とプログラム埋め込みプロンプトを整理し、OSS 公開前の負債を解消する。

**スコープ**:
1. **テンプレート化**: `panel/description.py` と `scenario/generator.py` の埋め込み SYSTEM_PROMPT を `src/yonkomatic/templates/{scenario_prompt.md,panel_prompt.md}` のフロントマター付き Markdown に外出し。利用者は `content/` に同名ファイルを置けば上書き可能 (フォールバック方式)
2. **content/ 構造刷新**: 旧 `characters/`, `world/`, `samples/`, `themes/` の 4 フォルダ → `prompt.md` (1 つに統合) + `images/` (再帰 glob、サブディレクトリ任意) の 2 要素のみ。月別テーマはシナリオ自動生成内で吸収して廃止
3. **AI ベンダー切替**: Anthropic + Google の 2 SDK → OpenAI 1 SDK。デフォルト `text_model: gpt-5.4`, `image_model: gpt-image-1`。Structured Output (`response_format=PydanticModel`) で ScenarioWeek を直接 validate
4. **model_render 採用 + pil_overlay 完全廃止**: `panel/composer.py`, `panel/validator.py`, `assets/fonts/`, `scripts/install_fonts.py`, `text_rendering` config セクション、`Dialogue.kind` を一括削除
5. **JSON → YAML 全面切替**: `scenarios/{week}.yaml`, `output/archive/{date}.yaml`, `state/state.yaml`
6. **デバッグログ強化**: archive YAML に `rendered_panel_prompt` + `rendered_image_prompt` を保存、`generate-scenarios` は `{week}.rendered.txt` を自動出力

**完了条件**:
- `uv run yonkomatic test panel --content examples/minimal` が新構造で動作
- `uv run yonkomatic generate-scenarios --week ...` が YAML を出力
- `uv run yonkomatic publish-today` が新パイプラインで Slack + static_site に投稿
- `uv run ruff check src/` が通る
- 旧依存 (anthropic, google-genai) と PIL 合成系コードが完全に消えている

**検証結果 (2026-05-10, gpt-image-1 + model_render, scenarios/2026-W19 全 7 話)**:

| | 完全一致 | 致命的バグ | 軽微な逸脱 |
|---|---|---|---|
| OpenAI (Step 6) | 0/7 (0%) | 7/7 (100%) | 0/7 (0%) |
| Gemini Flash (Step 5e 比較) | 2/7 (29%) | 1/7 (14%) | 4/7 (57%) |

各話の問題 (致命的バグ多発の主因はパネル数違反 + 誤字幻覚):

- ep1: 2 コマ生成 / 「がいつもと」欠落 / 話者スワップ
- ep2: 3 コマ生成 / 「左側だけ横築します」(意味不明な誤字) / 「ですね」欠落
- ep3: 3 コマ生成 / 「食封」「永暑」誤字 / コマ間で台詞混入
- ep4: 2 コマ生成 / panels 3-4 完全欠落 (「ぽふ」 / 「座布団」)
- ep5: 2 コマ生成 / 「鞶」「塲」誤字 / 後半 2 コマ欠落
- ep6: 3 コマ生成 / 「ぴ→び」誤字 / 「ななな」幻覚 / 話者スワップ
- ep7: 2 コマ生成 / 「てます」欠落 / 後半 2 コマ欠落

**根本原因の推定**:
1. **アスペクト比ミスマッチ**: `image_size: "1024x1536"` は実比率 2:3。OpenAI gpt-image-1 が portrait で提供するのは 2:3 / 1:1 / 3:2 のみで真の 3:4 はない。縦の余裕不足で「4 コマ → 2-3 コマに端折る」挙動が頻発
2. **gpt-image-1 のテキスト精度は Gemini Flash 同等またはやや劣る** (誤字幻覚 / 単語欠落の傾向は類似)
3. **コマ数指示の遵守率が低い** (「4 panels stacked vertically」を視覚モデルが強く守らない)

**判定**: Step 5e と同じく本番採用は許容できない品質。判断を保留し、(a) gpt-image-2 で再検証、(b) prompt-engineering で 2x2 グリッド指定 + size を 1024x1024 にして 4 panel を分割描画、(c) scaffold は維持しつつ将来の高品質画像モデル登場を待つ、のいずれかで進める。Step 6 の実装そのものは完成済みでテンプレ化 / OpenAI 化 / 構造刷新は意図通り動作。

### ✅ Step 6.5 — gpt-image-2 採用 + batch CLI (commit `e7873a6` config 切替, `ef5a49f` batch CLI, `a08c677` cost tracking)

**背景**: Step 6 で gpt-image-1 + 1024x1536 (実 2:3) が「パネル数違反 + 誤字幻覚」で **0/7 完全一致 / 7/7 致命的バグ**。原因は (a) アスペクト比が真の 3:4 ではない、(b) gpt-image-1 のテキスト精度。2026-04-21 リリースの **gpt-image-2** はカスタムサイズ可 (各辺 16 の倍数 / 最大 3840px / 比率 3:1 以下) で **真の 3:4 = 1536x2048** が選べる。OpenAI 公式が "improved multilingual text rendering" を謳い、ユースケースに **comics** を筆頭に挙げている。

**スコープ**:
1. config を `gpt-image-2` + `image_size: "1536x2048"` に切替 (commit `e7873a6`)
2. **コール毎の token usage + コスト推定**を `OpenAIClient` に組み込み (`UsageTracker`)。stderr に `[cost] gpt-5.4 (text): prompt_tokens=... → $0.0xx` を 1 行表示、コマンド終了時に per-model 集計、archive YAML の `usage` キーに永続化 (commit `a08c677`)
3. **`/v1/batches` 経由の週単位画像バッチ生成** (50% off、24h 完走) を CLI に追加: `batch-submit-images --week W` / `batch-fetch-images --week W` (commit `ef5a49f`)
4. 矛盾していた `aspect_ratio` フィールドや dead な `StateStore.auto_commit` 等を削除 (commit `88771d8`)

**検証結果 (2026-05-10、scenarios/2026-W19 全 7 話、sync 実行 ~$2.04)**:

| | Step 5e Flash | Step 6 gpt-image-1 | **Step 6.5 gpt-image-2** |
|---|---|---|---|
| 完全一致 | 2/7 (29%) | 0/7 (0%) | **6/7 (86%)** |
| 致命的バグ | 1/7 (14%) | 7/7 (100%) | **0/7 (0%)** |
| 軽微な逸脱 | 4/7 (57%) | 0/7 (0%) | **1/7 (14%)** |

各話の詳細:
- ep1 風の予告 / ep2 新緑のベンチ / ep4 拍手の練習 / ep5 植木鉢の会議 / ep6 通知音じゃない / ep7 靴ひもの勝敗: 全 8 dialogue 一字一句一致、話者・パネル数も正確、擬音 (「ぽふ」「ぴ」「トン」) まで自然に挿入
- ep3 早口のアイス: 8/8 テキスト一字一句一致 + 話者スワップ (Panel 2 で台詞が逆) → 軽微な逸脱

**判定**: 本番採用。gpt-image-2 + 1536x2048 をデフォルトとして固定。残る 1/7 の話者スワップは現時点では許容範囲。コストは gpt-image-1 高品質 ($0.20/枚) と比べて gpt-image-2 高品質 1536x2048 で約 $0.29/枚、batch 投入なら $0.145/枚。

**追加検証 (2026-05-10、scenarios/2026-W21 全 7 話、batch 実行 $0.6102 = sync 換算 $1.89 比 -68%)**:

| | Step 6.5 W19 (1536x2048 sync) | **Step 6.5 W21 (960x1280 batch + 新ガイダンス + 参考画像配線)** |
|---|---|---|
| 完全一致 | 6/7 (86%) | **7/7 (100%)** |
| 致命的バグ | 0/7 (0%) | **0/7 (0%)** |
| 軽微な逸脱 | 1/7 (14%、話者スワップ) | **1/7 (14%、ep3 で dialogue が「」付き装飾)** |
| コスト | $0.137/週 (batch) | **$0.610/週** (実コスト、gpt-image-2 batch x 7) |

各話の判定:
- ep1 風の予告 / ep2 冷やしすぎ注意 / ep4 静かな通知音 / ep5 傘の待機列 / ep6 朝の練習問題 / ep7 窓辺の主役: 8 dialogue 全て一字一句一致、4 panel 厳守、話者一致、SFX (「さらっ」「ぴらっ」「ひや〜」「しーん」「ピッ」「ぴっ…」「ぽつ」) 描画
- ep3 駅まで十分: 8 dialogue 一字一句一致、SFX「ゴトン…」描画。dialogue が `「駅まで十分！」` のように鉤括弧付きで吹出デザインに描画 — テキスト本文は完全一致なので軽微な逸脱

**batch 完了時間**: submit (06:21:23 UTC) → 最初の completed 観測 (06:32:45 UTC) で **約 11 分 22 秒**。OpenAI の completion_window 24h に対して非常に高速。

**判定**: 960x1280 + 新ガイダンス + 参考画像 LLM 告知の組み合わせが本番運用品質として確立。Step 6.5 の本番デフォルト (gpt-image-2 + 960x1280) が W19 ベースラインを上回る品質を実証。

**バッチ機能の使い方**:
```bash
# Sun に scenarios 生成 → そのまま batch 投入
yonkomatic generate-scenarios --week 2026-W21
yonkomatic batch-submit-images --week 2026-W21
# state/batches/2026-W21.yaml に batch_id 保存
# Mon 朝に fetch
yonkomatic batch-fetch-images --week 2026-W21
# output/preflight/2026-W21/ep{1..7}.png に展開
```

(`publish-today` への自動連携は Step 7 で実装予定)

### ✅ Step 6.6 — GitHub Actions も batch 画像生成に切替 (実装完了、Step 6.5 と一体)

**背景**: `daily-publish.yml` を sync 毎朝 ($0.27/枚 × 7 = $1.89/週) から batch 経由 ($0.95/週、50% off) に切替える。週次で一括投入し、日次は fetch + publish のみで済ませる。

**実装場所**: スコープ 4 項目すべて Step 6.5 の commit `c829994` (「feat: 週次バッチ生成 + 日次 publish の preflight 自動採用」) で組み込み済み。当時 ROADMAP の更新が漏れて Step 6.6 を ⏳ のまま残していたが、2026-05-10 に整合化した。

| ROADMAP スコープ | 実装場所 |
|------------------|----------|
| weekly-scenarios で `batch-submit-images` 投入 | `.github/workflows/weekly-scenarios.yml:43-46` |
| daily-publish で `batch-fetch-images` 先行実行 | `.github/workflows/daily-publish.yml:37-46` (`continue-on-error: true`) |
| publish-today: preflight があれば再生成 skip | `src/yonkomatic/cli.py:702-755` (`use_preflight=True` がデフォルト) |
| preflight 不在時の sync フォールバック | 同上 (`else` 分岐で `build_image_prompt` + `_run_openai_image`) |

**完了条件 (達成済み)**:
- 月〜日 7 日分の画像が batch 経由で生成される配線になっている (cron 連鎖)
- batch 失敗時は sync フォールバックで投稿は継続される (`continue-on-error` + `_publish_episode_pipeline` の preflight 不在分岐)
- `state/batches/{week}.yaml` の status を見て manifest の挙動を分岐できる

**残課題 (Step 6.7 に送り)**: batch が 24h 以内に完走しなかった場合の自動リトライ戦略 (ユーザー指定方針: 当日 sync + 翌日以降 batch 再投入)。

**実運用検証の扱い**: 本来は live ブランチで 1 週間 cron 観察を予定していたが、live を 2026-05-10 に履歴ごと削除 + 新規作成したため運用パターンが定まっていない。実運用検証は Step 7 (OSS 公開準備) で運用ディレクトリ集約 + 利用者ブランチ運用の再設計と合わせて行う。

### ✅ Step 6.7 — batch 失敗時の自動リトライ (Step 6.6 の発展) → **Step 7b として完了 (2026-05-10)**

> **2026-05-10 完了**: 本 Step は Step 7 の **7b** として実装済み (下記 Step 7b セクション参照)。実装サマリ: `batch-resubmit-missing --week W` CLI 追加、manifest に `retries: [...]` 配列追記、`batch-fetch-images` が retries も poll、`daily-publish.yml` に best-effort step 追加。**未決事項の確定値**: 上限 2 回 / 配列追記方式 / 「pending かつ preflight 不在」を `state.history` × `_find_preflight_image` の AND で判定 (date 列挙はせず episode_number 基準、§Step 7b 設計判断 3 参照)。

**背景**: Step 6.6 の cron 運用で batch が 24h 以内に完走しない / failed した場合に、人手介入なしで投稿を継続する。Step 6.5 の CLI (`batch-submit-images` / `batch-fetch-images`) は手動運用前提なので、自動リカバリパスを追加する。

**スコープ (ユーザー指定方針 2026-05-10)**:
1. その日の preflight が無ければ fetch を試行 (実装済み = Step 6.6)
2. fetch しても無ければ sync 生成 (実装済み = Step 6.6)
3. **publish 後に week 内の未投稿エピソード (今日以降) で preflight 不在のものがあれば新規 batch を投入** (本 Step で新規実装)

**実装方針**:
- CLI に `batch-resubmit-missing --week W` を追加: 既存 manifest と `output/preflight/{week}/` を照合し、不在エピソード分のみを新規 batch に投入
- manifest 構造拡張: 既存 `state/batches/{week}.yaml` に `retries: [...]` 配列を追加 (1 ファイルで完結) または `{week}-r1.yaml` 等のバージョン分割 (履歴が独立)。着手時に決める
- `_load_batch_job_meta` / `_find_preflight_image` を複数 manifest 対応に拡張 (preflight 化済みエピソードのメタを正しく archive に復元するため)
- `daily-publish.yml` の `Publish today's episode` 直後に `batch-resubmit-missing` step を `continue-on-error: true` で追加

**完了条件**:
- batch failed/expired 翌日には残り日数分の新規 batch が自動投入される
- preflight が再び揃った日からは自動的に preflight 経由で publish される
- 既に投稿済みのエピソードは再投入されない (ムダ排除)

**未決事項 (着手時に確定)**:
- 再投入の上限回数 (失敗が続いた場合に sync 永続化に倒すか)
- batch_id 履歴の管理形式 (manifest 内追記 vs 別ファイル)

### ⏳ Step 7 — OSS 公開準備 (7a〜7h に分割)

**背景**: Step 7 は (a) gh-pages 分離、(b) Step 6.7 自動リトライ、(c) ドキュメント整備 (README/SETUP/CONTRIBUTING)、(d) ユニットテスト + CI、(e) private fork での 1 週間実運用検証、(f) Template Repository 化、と幅広いスコープを含む。1 セッションで一気にやると粒度過剰なので Step 4 (4a-4d) / Step 5 (5a-5e) に倣ってサブステップ分割する。

**完了条件**: 第三者が README 通り 30 分以内で自分の漫画ボットを立ち上げられる、かつ private fork で 1 週間 cron を観察して preflight 利用率と batch 完走率が記録されている状態。

**着手順序と依存関係**:

```
7a (gh-pages 分離)              ← workflow と運用の根本変更。後続全部の前提
  ├─ 7b (Step 6.7 自動リトライ)   ← 7a で manifest/preflight の置き場が gh-pages に確定後
  ├─ 7c (CONTRIBUTING.md)         ← 軽量、7a と並行可
  ├─ 7d (ユニットテスト + CI)     ← 7a/7b 実装が固まってから
  ├─ 7e (README リライト + デモ)  ← 7a 後でないと Quick Start が嘘になる
  ├─ 7f (SETUP.md 全面改訂)       ← 7a/7b 後でないと運用記述が古くなる
  ├─ 7g (private fork 実運用検証) ← 7a/7b/7d/7f が揃ってから 1 週間観察
  └─ 7h (Template Repository 化)  ← 全ドキュメント完成後に押すスイッチ
```

順序の根拠:
- **7a が先頭**: workflow / `.gitignore` / ドキュメント全てに影響する根本変更。後続が「どの版」を書くかが 7a で確定する
- **7g (検証) が末尾寄り**: 唯一の長尺 (1 週間)。7a/7b/7f が乗った workflow を観察対象にする
- **7h を末尾**: Template Repository を先に押すと第三者が未完成版を踏む

並行可能ペア: 7c + 7a, 7c + 7b, 7e + 7d (ファイル衝突しない)。

#### ✅ Step 7a — 生成物の gh-pages 分離 (2026-05-10)

**スコープ**: cron 生成物 (`docs/`, `state/`, `scenarios/`, `output/archive/`, `output/preflight/`) を main から外し、orphan branch `gh-pages` に push。main はコード + `content/` サンプル + ドキュメントのみのクリーン状態に。

**完了条件**:
- ✅ 両 workflow が `git worktree add .gh-pages gh-pages` で orphan branch をぶら下げ、root 直下に 4 本の symlink (`scenarios -> .gh-pages/scenarios` 等) を張ってから CLI を実行する流れで動く
- ✅ `cli.py` 完全無改修。CLI は従来どおりリポジトリルート相対 (`Path("output/archive")` 等) で書き込み、symlink 経由で `.gh-pages/` に着地
- ✅ main の `.gitignore` から `/scenarios/`, `/state/`, `/output/`, `/docs/*` を削除し、代わりに `/.gh-pages/` と末尾なしの `/scenarios` `/state` `/output` `/docs` (symlink も捕捉) に置換
- ✅ ローカル `uv run ruff check src/` 緑、CLI 起動 OK。symlink 不在時はローカルでも従来どおり main ルート直下に書き込む (新 `.gitignore` で全部無視)
- ⏳ private fork で workflow_dispatch 手動実行による gh-pages 初期化 → daily-publish 動作確認は **次セッションで実施** (Step 7g の検証手順の項目 1-5 に統合)

**影響ファイル**: `.github/workflows/{weekly-scenarios,daily-publish}.yml`, `.gitignore`, `CLAUDE.md`

**確定した方針** (実装時に決定):
1. **実装手段**: **git worktree + ルート直下 symlink (案 A)** を採用。CLI / `./content` / `./config.yaml` の参照を一切いじらずに済む。`uv --project ..` のような cwd 操作も不要。
2. **gh-pages 初期化**: workflow 内フォールバック方式。`git fetch origin gh-pages` の有無で分岐し、無ければ `index.html` プレースホルダ 1 個で orphan commit + push。手動 init は SETUP に書かない (Step 7f でローカル試運転モードのみ別記)。
3. **state.yaml race**: gh-pages 側で `git pull --rebase --autostash origin gh-pages`。weekly と daily で書込先ファイルが実質分離されているため衝突確率は低い。`concurrency` group は **入れない** (Step 7g 観察で必要なら追加検討)。
4. **既存 bot commit 履歴**: orphan で新規作成、`state.yaml` の history[] injection ロジックは workflow に書かない。既存 live 運用ユーザは Step 7g 検証手順書の任意手順として手動 put する。
5. **`fetch-depth: 0`** 採用 (両 workflow): `git pull --rebase` が full clone を要求するため。週次 / 日次 cron 程度では overhead 無視可。
6. **末尾なし `.gitignore` パターン**: `/scenarios` (末尾スラッシュなし) で「ファイル / ディレクトリ / symlink 全部」マッチさせる。`src/yonkomatic/state` は先頭 `/` がないため影響受けず。CLAUDE.md L74 に行儀の説明を追記。

**未確認 (Step 7g に持越し)**: orphan 初期化時のフォールバック動作、両 workflow が緑になるか、main に generated 物が漏れていないか、preflight ヒット率 / batch 完走率の実測。

#### ✅ Step 7b — Step 6.7 自動リトライ実装 (2026-05-10)

**スコープ**: ROADMAP §Step 6.7 のスコープをそのまま実装。`batch-resubmit-missing --week W` CLI、manifest 拡張、`daily-publish.yml` への step 追加。

**完了条件 (実装結果)**:
- ✅ `uv run yonkomatic batch-resubmit-missing --week W`: pending (`state.history` 不在) かつ `_find_preflight_image` 不在の ep のみを抽出し、初回 prompt を reuse して新規 batch 投入。manifest の `retries: [...]` 配列に append
- ✅ `batch-fetch-images` が main batch のポーリング後に `manifest["retries"]` を回って未完了の retry も poll → 完了したら preflight に書き出し manifest 更新 (シェアドヘルパ `_drain_batch_results` で result 書き出しを共用化)
- ✅ `daily-publish.yml` の `Publish today's episode` 直後に `continue-on-error: true` で `batch-resubmit-missing` step を追加
- ✅ `_load_batch_job_meta` / `_find_preflight_image` は **無改修** (top-level `jobs[]` から prompt メタを引け、preflight パスは固定 — 「複数 manifest 対応」は配列追記方式採用により不要に)
- ✅ 既投稿エピソードは再投入されない (`state.history` × week filter で除外)
- ✅ ローカル 5 ケース目視: (1) manifest 不在 → silent no-op、(2) main 未完了 → skip メッセージ、(3) cap reached (2/2) → warn + exit、(4) 全 published → "nothing to resubmit"、(5) ep5 preflight 存在 + ep1-4 published → "resubmitting 2 episode(s) (ep6, ep7) as retry #1 of 2" を確認 (実 API 投入は本番運用 / Step 7g に持越し)

**影響ファイル**: `src/yonkomatic/cli.py` (`_drain_batch_results` 抽出、`batch-resubmit-missing` 新規、`batch-fetch-images` 拡張、`BatchStatus` import 追加), `.github/workflows/daily-publish.yml` (step 1 つ追加), `ROADMAP.md`

**確定した方針** (実装時に決定):
1. **manifest 構造**: **配列追記方式 (オプション A)** を採用。`state/batches/{week}.yaml` に `retries: [{batch_id, submitted_at, custom_ids, status, fetched_at, results}]` を append。1 ファイルで完結 = ファイル探索ロジック不要、glob 不要。
2. **再投入の上限回数**: **上限 2 回 (`_MAX_BATCH_RETRIES = 2`)**。3 回目以降は warn ログ + exit 0、sync フォールバックに任せる
3. **pending 判定**: ROADMAP 当初記述の「ISO week → 月〜日マッピング」は不要と判断。`publish-today` の現在の挙動 (`state.last_published_episode + 1`) は ep_n と weekday n が必ずしも一致しないため date 列挙は無意味。代わりに `state.history` 走査 (week 一致) × `_find_preflight_image` 不在の AND で判定
4. **prompt は再生成しない**: 初回の `jobs[].rendered_image_prompt` をそのまま `BatchImageJob.prompt` に渡す。理由: (a) batch 失敗の大半は infra 起因 (expire / 一部 job の transient エラー)、(b) 再生成すると text LLM コストが乗る、(c) `_load_batch_job_meta` が読む archive 用 metadata が初回と一致して整合性が取れる
5. **main batch 未完了時のガード**: `manifest.status != "completed"` のときは resubmit を実行しない (preflight が無いのは main がまだ走っているからで、二重投入になる)。`batch-fetch-images` が main を completed に更新した後の cron で初めて retry ロジックが起動する

#### ✅ Step 7c — CONTRIBUTING.md 新規作成 (2026-05-10)

**スコープ**: 現状不在の `CONTRIBUTING.md` を新規作成。fork 前提運用 + 上流 PR 流儀 + 開発ルール (uv / ruff / commit メッセージ規約 / Co-Authored-By 禁止) を明文化。

**実装サマリ**:
- `CONTRIBUTING.md` を 9 章で新規作成: (1) 位置付けと貢献の範囲、(2) 開発環境 (uv)、(3) Lint (`uv run ruff check src/`)、(4) テスト (Step 7d 完了後追記の placeholder + 既存 `test slack/panel` 案内)、(5) コーディング規約 (CLAUDE.md からの噛み砕き)、(6) コミットメッセージ規約 (Conventional Commits 風 + Co-Authored-By 禁止再掲)、(7) PR 流儀 (説明テンプレ・lint 緑前提)、(8) Issue/Discussions (バグ報告のみ受付)、(9) ライセンスと行動規範 (MIT + Contributor Covenant 相当を inline)
- README.md の「ライセンス」直前に「貢献」節を追加 (1 段落、CONTRIBUTING へのリンク)

**確定した未決事項**:
1. Issue / PR テンプレート → **置かない** (テンプレ専用リポなので Issue 流入を絞る)
2. Code of conduct → **CONTRIBUTING.md に inline** (別ファイルにしない)
3. テスト実行手順 → **placeholder のみ** (Step 7d 完了後に追記)
4. PR 流儀の温度感 → **基本ルール中心** (ROADMAP 更新義務は contributor に課さない、メンテナ向け規約は CLAUDE.md 既載)
5. Issue 方針 → **再現性あるバグのみ**、機能要望/質問/運用相談は Discussions

**影響ファイル**: `CONTRIBUTING.md` (新規), `README.md`

#### ✅ Step 7d — ユニットテスト + CI lint (2026-05-10)

**実装サマリ**: `tests/` をフラット構成で新設し、6 ファイル 44 ケースの pytest を追加。OpenAI / Slack / RSS / ファイル I/O はすべて `pytest-mock` の `MagicMock(spec=...)` または `mocker.patch("...feedparser.parse")` でオフライン化、ローカル `uv run pytest` が約 0.5 秒で完走。`.github/workflows/ci.yml` を PR + main push トリガーで新設し、`uv run ruff check src/ tests/` + `uv run pytest` を 1 job に統合。dev deps は `[project.optional-dependencies]` を削除し `[dependency-groups].dev` に集約 (uv 流儀統一)、`[tool.pytest.ini_options]` に `testpaths = ["tests"]` を設定。

**新規ファイル**:
- `tests/test_scenario_schema.py` (7 ケース) — `Panel(index)` 1-4 境界、`ScenarioEpisode` の panels=4 厳守、`episode_number≥1`、`ScenarioWeek` の episodes 1-7 境界
- `tests/test_state_repo.py` (7 ケース) — `StateStore` の load 不在/round-trip/atomic save (tempfile 残骸なし) / append round-trip / `current_week_index` の None 保持 / 親ディレクトリ自動作成
- `tests/test_panel_description.py` (8 ケース) — `MagicMock(spec=OpenAIClient)` で complete を mock、内蔵 `panel_prompt.md` をレンダ、known/unknown model のガイダンス分岐、temperature の forwarding
- `tests/test_news_fetcher.py` (8 ケース) — `feedparser.parse` を fully mock、enabled=False / feeds=[] / multi-feed flatten / max_items truncate / lookback フィルタ / pubdate なし採用 / 単一 feed 失敗の他 feed 続行 / socket timeout 復元
- `tests/test_publisher_static_site.py` (8 ケース) — 1x1 PNG リテラルで実書き出し、5 ファイル生成 / 相対&絶対 URL / title&summary 含有 / date 重複 upsert / INDEX_LIMIT=30 切詰め / style.css 上書き禁止 / 拡張子保存
- `tests/test_batch_manifest.py` (6 ケース) — `monkeypatch.chdir(tmp_path)` で CWD 隔離、week=None / manifest 不在 / 一致 / 不一致 / 空 manifest / Step 7b の `retries[]` 同居でも `jobs[]` のみ参照
- `.github/workflows/ci.yml` — `astral-sh/setup-uv@v3` + `uv sync` + lint + test を 1 job 統合、Python matrix なし

**確定した設計判断**:
1. **dev deps は `[dependency-groups].dev` に統一** — `[project.optional-dependencies]` セクションごと削除。uv 流儀の単一ソース、PEP 735 準拠。
2. **`tests/` はフラット構成** — モジュール構造に揃えたサブディレクトリは作らず `tests/test_*.py` 直下。6 ファイルでは見通しが良い。
3. **`conftest.py` は作らない** — 共通 fixture は各ファイル内のローカルヘルパで十分、結合を増やさない。
4. **OpenAI mock は `MagicMock(spec=OpenAIClient)`** — `mocker.patch("...OpenAIClient.complete")` よりテスト主体が明確、spec で API ドリフト検知。
5. **feedparser patch 先は `yonkomatic.news.fetcher.feedparser.parse`** — import 元側を patch、ネットワーク漏れガード。
6. **`_load_batch_job_meta` テストは `monkeypatch.chdir(tmp_path)` 必須** — 関数が CWD 相対 (`Path("state/batches/...")`) なのでリポジトリ実 state を読む事故を回避。
7. **CI は PR + main push 両方をトリガー** — fork 利用者の PR でも作者の merge 後でも回る、OSS 慣習。
8. **`uv sync` は `--frozen` なし** — 本コミットで `uv.lock` も再生成するため初回 PR は frozen 不可、daily-publish 側 (`uv sync --frozen`) との整合は次以降の PR の責務外。

**未決事項の確定値**:
1. coverage 計測 → **未導入** (緑/赤判定で十分、CI を肥大化させない)
2. integration テスト (実 API) → **未導入** (`uv run yonkomatic test panel/slack/news` が既存の手動 integration)

#### ✅ Step 7e — README リライト + Quick Start + デモ画像 (2026-05-10)

**結果**: README を 6 節構成に全面書き換え。W21 ep4/ep5 の本番品質サンプル 2 枚を `assets/demo/` に配置。

**確定事項**:
- **章立て** = Status / Demo / Quick Start / How it works / このリポジトリの位置付け / リンク集 / ライセンス の 6 節 (ROADMAP 指示の 4 節 + 「位置付け (upstream vs fork 図解)」を残す方針で確定)
- **デモ画像** = W21 ep4 「静かな通知音」(キッチンタイマーの SFX「ピッ」) と ep5 「傘の待機列」(雨と保険オチ) の **2 枚並べ** (ROADMAP 推奨は 1 枚だったが、屋内 SFX × 屋外オチで雰囲気差を出すため 2 枚採用)。`output/preflight/2026-W21/ep{4,5}.png` から `assets/demo/2026-w21-ep{4,5}-{quiet-notification,umbrella-queue}.png` にコピー
- **Demo URL** = `https://<your-name>.github.io/yonkomatic/` の形で fork 後に有効化される URL 例として注記 (上流テンプレは cron 停止のため deploy されない旨を明記)
- **モデル名表記** = `config.yaml` 現行値 (gpt-5.4 / gpt-image-2) と整合確認済、How it works 節の表に統合
- **捨てた節** = 旧「content/ の構造」(SETUP.md と CLAUDE.md に詳述あり、How it works 内の小ブロックに統合して 1 ディレクトリの形だけ残す)
- **Status 行** = 「Step 7 着手中、7a〜7d 完了、本 README は 7e の成果物」表記。7g 完了後に「Step 7 完了」へ書き換える (Step 7g §完了条件に明記)

**影響ファイル**: `README.md` (全面書き換え、77 → 102 行), `assets/demo/2026-w21-ep4-quiet-notification.png` (新規 1.9MB), `assets/demo/2026-w21-ep5-umbrella-queue.png` (新規 2.0MB)

Python コード / config / workflow への変更なし、`uv run ruff check src/ tests/` 緑。

#### ⏳ Step 7f — SETUP.md 全面改訂 (0.5〜1 セッション)

**スコープ**: 7a で `.gitignore` 緩和が不要になった反映 + 7b のリトライ運用 + GitHub Pages の deploy 設定追加 + `.gitattributes` merge driver 登録手順 (既存 §11 の補強)。

**完了条件**:
- 旧 §7 「.gitignore を緩和」を **削除** (7a で main に運用パターンが書かれない前提)
- 新節「GitHub Pages の deploy source 設定」追加 (`Deploy from a branch: gh-pages /(root)`)
- 新節「batch リトライの自動化 (Step 6.7)」追加 — failed/expired 時の挙動説明
- §0 前提に **「fork は private 必須」** を強調
- §11 上流取り込みに「初回 1 度だけ `git config --add merge.ours.driver true` を fork で実行」
- §6 Workflow permissions の文言を gh-pages 体制に整合化 (push 先が gh-pages branch であることを明記)
- 全章で「branch 戦略」記述を 1 箇所に集約

**影響ファイル**: `SETUP.md`, `CLAUDE.md` (必要なら 1〜2 行同期)

#### ⏳ Step 7g — private fork 実運用検証 (1 週間観察、Step 6.6 から繰越)

**スコープ**: 7a/7b/7d/7f の成果が乗った main を private fork (例: `jumboly/yonkomatic-mine`) に取り込み、cron を有効化して 1 週間放置。preflight 利用率と batch 完走率を ROADMAP に記録。

**完了条件**:
- private fork で 7 日連続 daily-publish が緑 (Slack 投稿成功 + gh-pages push 成功)
- 期間中に最低 1 回 weekly-scenarios cron が走り gh-pages に scenarios + batch manifest が積まれる
- preflight 利用率 (= 7 話中、preflight ヒットした話数) を ROADMAP に記録 (期待値 7/7、batch 不調なら 5〜6/7)
- batch 完走率 (= 完走した batch / 投入した batch) を記録
- 7b のリトライが発火する障害ケースが観察できた場合、原因と挙動を Decisions Log に追記
- README の Status 行を「Step 7 完了」に書き換え + デモ URL を fork 先 (or 公開可能な範囲で) に更新

**影響ファイル**: `ROADMAP.md` (現在地 / Step 6.6 / Step 7 / Decisions Log), `README.md` (Status)

**未決事項**:
1. 観察中に Step 7 修正が必要になった場合の扱い → **推奨: 致命的でなければ観察継続、致命的なら仕切り直し**
2. cron 観察ログ → **推奨: `tmp/step7-live-log.md` に手書きメモ、ROADMAP には要点のみ転記**

#### ⏳ Step 7h — GitHub Template Repository 化 (0.1 セッション、儀式的)

**スコープ**: `gh repo edit jumboly/yonkomatic --template` で Template Repository 化、リポジトリ description / topics を OSS 向けに整える。

**完了条件**:
- GitHub UI のリポジトリ右上に「Use this template」ボタンが出る
- description / topics (`yonkoma`, `manga`, `openai`, `slack-bot`, `github-actions`, `template`) が設定されている
- README に「Use this template ボタンから始められる」一文を追加 (SETUP の fork 手順と併存)

**影響ファイル**: README の 1 行追記、リポジトリ設定 (UI/CLI)

**未決事項**: なし (儀式的)

---

## 直近の決定事項 (Decisions Log)

新しい決定が出たら頭に追加。古いものは削除せず残す。

- **2026-05-10 (Step 7e 実装完了)** README を全面リライトし、本番品質サンプル 2 枚を `assets/demo/` に配置。**確定した方針**: (1) **章立ては 6 節構成** = Status (1 行) / Demo (画像 2 枚 + Demo URL 注記) / Quick Start (5 ステップ) / How it works (パイプライン図 + 技術スタック表 + content 構造) / このリポジトリの位置付け (upstream vs fork 図解、現行維持) / リンク集 / ライセンス。ROADMAP §7e 指示の「Quick Start / Demo / How it works / リンク集」4 節に「位置付け」節を残す形で着地、(2) **デモ画像は W21 ep4 + ep5 を 2 枚並べ** — ROADMAP 推奨の「ep4 or ep5」を両方採用 (屋内 SFX「ピッ」× 屋外オチ「ぽつ」で雰囲気差)。`output/preflight/2026-W21/` から `assets/demo/2026-w21-ep{4,5}-{quiet-notification,umbrella-queue}.png` にコピー、Markdown table 2 列で並べてキャプションは「summary_no_spoiler」原文流用、(3) **Demo URL は fork 後 URL 例で注記** — `https://<your-name>.github.io/yonkomatic/` の形で示し、上流テンプレは cron 停止のため deploy されない旨を明記。`jumboly.github.io/yonkomatic/` を直書きせず汎用例にしたのは fork 利用者が自分の URL に置き換えやすくするため、(4) **モデル名は config.yaml と整合確認** — text=`gpt-5.4` / image=`gpt-image-2`、現 config.yaml と一致を grep で確認してから記載、(5) **「content/ の構造」節は廃止** — How it works 内の小ブロック (`prompt.md` + `images/` だけ) に圧縮、詳細は SETUP.md/CLAUDE.md に委譲、(6) **Status 行は暫定表記** — 「Step 7 着手中、7a/7b/7c/7d 完了、本 README は 7e の成果物」。7g 完了後に「Step 7 完了」へ書き換える運用を §7g 完了条件に既に明記済み、(7) **How it works に技術スタック表を統合** — 旧「アーキテクチャ概要」節を廃止し、パイプライン ASCII 図の直下に表を置く形で重複を排除、`Publisher Protocol で抽象化、Discord は将来対応` も保持、(8) **Discord 将来対応の文言は維持** — Step 7 のスコープ外だが、Publisher Protocol 設計の意図を示すため残す。**新規ファイル**: `assets/demo/2026-w21-ep4-quiet-notification.png` (1.9MB) / `assets/demo/2026-w21-ep5-umbrella-queue.png` (2.0MB)。**修正**: `README.md` (77 → 102 行、6 節再構成)。`uv run ruff check src/ tests/` 緑。Python コード / config / workflow 変更なし。
- **2026-05-10 (Step 7d 実装完了)** `tests/` をフラット構成で新設、6 ファイル 44 ケースの pytest を追加。**確定した方針**: (1) **dev deps は `[dependency-groups].dev` に統一** — `[project.optional-dependencies]` セクションを削除し pytest/pytest-mock/ruff を移動 (uv 流儀の単一ソース、PEP 735 準拠)、(2) **`tests/` フラット構成** — モジュール構造に揃えたサブディレクトリは作らず `tests/test_*.py` 直下で見通し確保、(3) **`conftest.py` 作らない** — 共通 fixture は各ファイル内のローカルヘルパで十分、結合を避ける、(4) **OpenAI mock は `MagicMock(spec=OpenAIClient)`** — `mocker.patch("...complete")` よりテスト主体が明確、spec で API ドリフト検知、(5) **feedparser patch 先は `yonkomatic.news.fetcher.feedparser.parse`** (import 元側) — ネットワーク漏れ防止のためテスト全本で統一、(6) **`_load_batch_job_meta` テストは `monkeypatch.chdir(tmp_path)` 必須** — 関数が CWD 相対 (`Path("state/batches/...")`) のためリポジトリ実 state を読む事故を回避、(7) **CI は PR + main push 両トリガー** — fork 利用者の PR でも作者の merge 後でも回る、(8) **`uv sync` は `--frozen` なし** — 本コミットで `uv.lock` も再生成、daily-publish 側の frozen 整合は次以降の責務外、(9) **`[tool.pytest.ini_options]` に `testpaths = ["tests"]` のみ** — `addopts` / `asyncio_mode` / `filterwarnings` は最小起動で。**新規ファイル**: `tests/test_scenario_schema.py` (7) / `test_state_repo.py` (7) / `test_panel_description.py` (8) / `test_news_fetcher.py` (8) / `test_publisher_static_site.py` (8) / `test_batch_manifest.py` (6) / `.github/workflows/ci.yml`。**修正**: `pyproject.toml` (groups 統一 + pytest config) / `uv.lock` (再生成) / `CONTRIBUTING.md` §3-4,7 (lint コマンド + テスト節 + PR 流儀) / `CLAUDE.md` (lint+test コマンド例)。`uv run pytest` 0.46s で 44 passed、`uv run ruff check src/ tests/` 緑。**Step 7b retries 同居テスト 1 ケース追加** — `_load_batch_job_meta` が retries[].results 配下の custom_id を誤返却しない契約を固定。
- **2026-05-10 (Step 7c 実装完了)** `CONTRIBUTING.md` を新規作成し、上流テンプレへの貢献ガイドを明文化。**確定した方針**: (1) **9 章構成** = 位置付けと貢献の範囲 / 開発環境 (uv) / Lint (`uv run ruff check src/`) / テスト (Step 7d 完了後追記の placeholder + 既存 `test slack/panel` を手動 integration として案内) / コーディング規約 (CLAUDE.md からの噛み砕き — WHY のみコメント / Step 番号は code に書かない / `typer.Exit` / `_fail_on` / `PublishResult(ok=False)`) / コミットメッセージ規約 (Conventional Commits 風 + **Co-Authored-By 禁止** を再掲、出典 §2026-05-08) / PR 流儀 (説明テンプレ「何を / なぜ / 動作確認」、lint 緑前提、レビュアー指名不要) / Issue & Discussions (バグのみ Issue、要望・質問は Discussions) / ライセンスと行動規範 (MIT + Contributor Covenant 相当を inline)、(2) **Issue / PR テンプレートは置かない** (テンプレ専用リポゆえ流入を絞る)、(3) **Code of Conduct は inline** (別ファイル化しない)、(4) **PR 流儀は contributor 向け基本ルールのみ** (ROADMAP/SPEC 更新義務は課さない、メンテナ向け規約は CLAUDE.md 既載)、(5) **Issue は再現性あるバグのみ受付**。`README.md` の「ライセンス」直前に「貢献」節 (CONTRIBUTING へのリンク 1 段落) を追加。新規 / 改修ファイルは `CONTRIBUTING.md` (新規) と `README.md` のみ、Python コード変更なし、`uv run ruff check src/` 緑。
- **2026-05-10 (Step 7b 実装完了)** OpenAI image batch の自動リトライパスを実装。`batch-resubmit-missing --week W` CLI を新規追加 (`cli.py` `batch-submit-images` の上)、`batch-fetch-images` を retries 併用ポーリングに拡張、`daily-publish.yml` の `Publish today's episode` 直後に `continue-on-error: true` で best-effort step を挿入。**確定した設計判断**: (1) **manifest 構造は配列追記方式**: 既存 `state/batches/{week}.yaml` に `retries: [{batch_id, submitted_at, custom_ids, status, fetched_at, results}]` を append (オプション B のバージョン分割は採らず、1 ファイル完結で flatten 1 段)、(2) **prompt は再生成しない**: 初回の `jobs[].rendered_image_prompt` を reuse して `BatchImageJob` を作る (text LLM コスト追加なし、archive metadata 整合)、(3) **上限 2 回 (`_MAX_BATCH_RETRIES = 2`)**: 3 回目以降は warn + exit 0 で sync フォールバックに任せる、(4) **pending 判定は episode_number 基準** (date 列挙はしない): `state.history` × week filter で published 集合を作り、`_find_preflight_image` 不在の AND で pending を抽出。`publish-today` の挙動 (`state.last_published_episode + 1`) は ep_n と weekday n が一致しないため date マッピングは無意味と判断、(5) **main 未完了時のガード**: `manifest.status != "completed"` のときは exec せず `batch-fetch-images` が main を completed にした次回 cron まで待つ (二重投入防止)、(6) **`_drain_batch_results` ヘルパ抽出**: `batch-fetch-images` の result-saving loop を関数化、初回 batch と retry batch で同じ schema を manifest に書く。`_load_batch_job_meta` / `_find_preflight_image` は無改修 (top-level `jobs[]` から prompt メタが引け、preflight パスは固定。配列追記方式採用により「複数 manifest 対応」の必要が消えた)。**ローカル 5 ケース目視 OK**: (a) manifest 不在 → silent no-op、(b) main 未完了 → skip、(c) cap reached (2/2) → warn、(d) 全 published → "nothing to resubmit"、(e) ep5 preflight 存在 + ep1-4 published → "resubmitting 2 episode(s) (ep6, ep7) as retry #1 of 2" (実 API 投入は本番 / Step 7g に持越し)。`uv run ruff check src/` 緑。
- **2026-05-10 (Step 7a 実装完了)** cron 生成物 (`scenarios/`, `state/`, `output/`, `docs/`) を main から完全分離し、orphan branch `gh-pages` に push する体制に切替。**実装手段は案 A: git worktree + ルート直下 symlink** を採用 (案 B working-directory 切替は `uv --project ..` 検証コストで却下、案 C `--data-root` flag は ROADMAP 完了条件 2 「Python 側に gh-pages の概念を漏らさない」原則違反で却下)。両 workflow に `Prepare gh-pages worktree` step を追加: `git fetch origin gh-pages` の有無で分岐し、無ければ `index.html` プレースホルダ 1 個で orphan commit + push (= フォークでの初回 dispatch で自動初期化、SETUP に手動 init 手順は書かない方針)。続く `Wire runtime symlinks` step で `scenarios -> .gh-pages/scenarios` 等を root 直下に張り、CLI は完全無改修で symlink 経由 `.gh-pages/` に書き込む。bot commit/push は `cd .gh-pages && git push origin gh-pages`、`pull --rebase --autostash` で weekly+daily の race を吸収 (`concurrency` group は Step 7g 観察で必要なら追加検討、今は入れない)。`fetch-depth: 0` を両 workflow に追加 (rebase に full clone が要る)。`.gitignore` は旧運用パターン 8 行削除 + `/.gh-pages/` と末尾なしの `/scenarios` `/state` `/output` `/docs` (symlink 捕捉) 追加。CLAUDE.md に「CI 上の出力 (gh-pages worktree)」節追加 + L74 末尾スラッシュ挙動の説明補強。**ローカル開発は symlink 不在のままで従来動作維持** (root 直下に書き込まれるが `.gitignore` が全部無視するため `git status` を汚さない)。**未確認**: private fork での workflow_dispatch 動作確認は Step 7g 検証手順 1-5 に統合 (本セッションでは git 環境がないため未実施)。
- **2026-05-10 (Step 7 サブステップ分割確定)** Step 7 (OSS 公開準備) を **7a〜7h の 8 サブステップ** に分割し、着手順序と各サブステップの完了条件・影響ファイル・未決事項を ROADMAP §Step 7 に明文化。Step 4/5 と同じ粒度 (1 セッション = 1 commit + ROADMAP 更新) に揃えた。順序: 7a (gh-pages 分離) → 7b (Step 6.7 自動リトライ) / 7c (CONTRIBUTING.md) / 7d (ユニットテスト + CI) / 7e (README リライト + デモ) / 7f (SETUP.md 全面改訂) → 7g (private fork で 1 週間観察) → 7h (Template Repository 化)。**gh-pages は 1 本に統合**することで確定 (`run-data` 別建てはしない、Pages 公開対象は `gh-pages /(root)`)。実装手段は **`git worktree` 直書きを推奨** (Action 依存ゼロ)。manifest 構造は **`retries: [...]` 配列追記方式を推奨** (1 manifest = 1 週で flatten 1 段)。再投入の上限は **2 回** (3 回目以降は sync フォールバックのみ)。Step 6.7 セクション (L361-) は本サブステップ計画への pointer を残しつつ既存スコープ記述を維持 (= 7b の参照元)。
- **2026-05-10 (W21 全 7 話 batch で 7/7 完全一致を確証 — 3 件の懸案を一括クリア)** scenarios/2026-W21 全 7 話を `batch-submit-images` → `batch-fetch-images` で生成 (実コスト $0.6102、submit から完了観測まで約 11 分 22 秒)。preflight 7 枚を Read で目視確認した結果、**完全一致 7/7 (100%) / 致命的 0/7 / 軽微 1/7 (ep3 で dialogue が鉤括弧付き吹出装飾)**。Step 6.5 W19 の 6/7 を上回る品質。これにより Step 6.5 余波の 3 懸案を一度に確証: **(1) 新ガイダンス (Verbatim キャラ anchor / SFX 指示 / Sequential panel labels / Literal text in double quotes / Negative constraints 末尾集約) の効果 — ep1/ep5 の 2 サンプルから 7 サンプル完走へ**、**(2) 960x1280 サイズで W19 並み以上の品質を実証 (1536x2048 比 -33% コスト)**、**(3) 参考画像の reference_images_block 配線が実 batch 経由で機能 (キャラ造形が全話で一貫、ヨンコの黒髪ボブ+丸眼鏡+白セーター+藍オーバーオール、マチカの茶髪ポニテ+赤パーカ)**。dialogue 56/56 一字一句一致、SFX 7 種 (「さらっ」「ぴらっ」「ひや〜」「しーん」「ゴトン…」「ピッ/ぴっ…」「ぽつ」) 全描画。本番運用の品質基準としてこの構成 (gpt-image-2 + 960x1280 + 新ガイダンス + 参考画像配線 + batch) を確定。
- **2026-05-10 (test-slack workflow で動作確認成功)** Step 7 着手前のテンプレ品質確認として `gh workflow run test-slack.yml -R jumboly/yonkomatic` を 1 回 trigger (`run 25623050101`)、11 秒で緑、Slack に test 画像投稿成功。workflow_dispatch / Secrets (SLACK_BOT_TOKEN + SLACK_CHANNEL_ID) / `uv sync --frozen` / `yonkomatic test slack` コマンドの経路すべて健全。Annotations に Node.js 20 deprecation 警告と GitHub のキャッシュサービス一時障害 (test 本体には影響なし) が出ているが、後者は GitHub 側、前者は別途対応 (下記 Gotchas)。weekly-scenarios / daily-publish の本格動作確認は Step 7 (gh-pages 分離) 後。
- **2026-05-10 (Step 7 のスコープを「運用ディレクトリ集約」→「生成物の別ブランチ分離 (gh-pages)」に置換)** 当初案では `scenarios/state/output/docs` を 1 ディレクトリ (`runtime/` 等) に集約する計画だったが、それより一歩進んで **main = コードのみ、生成物は gh-pages 等の別ブランチに orphan push** する方針に切替。理由: (a) main の diff が cron 生成物で汚れず上流追従が綺麗、(b) fork 利用者の `.gitignore` 緩和が不要になる (生成物は別ブランチに行くため)、(c) GitHub Pages は gh-pages ブランチを直接公式 deploy 対象にできる。トレードオフは workflow が二段階 commit (main にコード / gh-pages に生成物) になる複雑度だが、`peaceiris/actions-gh-pages` 等の既製 Action で吸収可能。state.yaml は workflow が gh-pages を sparse checkout → 読み書き → push する形にする。1 ブランチ (gh-pages) でまとめるか、static-site 用 (`gh-pages`) と運用データ用 (`run-data`) に分けるかは Step 7 着手時に確定。
- **2026-05-10 (`examples/minimal` を `content/` に統合)** 動作確認用サンプル素材 (`prompt.md` / `images/*.png` / `sample-scenario.yaml`) を `content/` に直接置く構造に変更 (commit `c4492bd`)。`cp -R examples/minimal/* content/` の手順が不要になり、テンプレ → fork → カスタマイズの流れが simpler。`.gitattributes` に `content/* merge=ours` を設定し、fork 先で利用者カスタムが upstream 更新と衝突しないようにした (利用者は `git config --add merge.ours.driver true` で driver を一度有効化する必要あり)。`cli.py` の 6 箇所のデフォルト Path も `examples/minimal` → `content` に変更、SPEC/CLAUDE/README/SETUP のディレクトリ記述も一新。
- **2026-05-10 (運用方針転換: 上流テンプレ専用化 + fork 運用)** 同日中に「main → live → main」と Default branch を行き来した試行を経て、最終方針を「**上流リポ (`jumboly/yonkomatic`) はテンプレ専用、自前運用は private fork で行う**」に確定。理由: live と main の二重運用は手動 sync / `.gitignore` 緩和の merge 競合 / 二重の責務管理が面倒で、利用者と作者が同じパターン (fork → main で運用) で動かせる方が README/SETUP が単純化される。本コミットで実施: (a) live ブランチ削除 (remote + local)、Default = main、(b) 両 workflow (`weekly-scenarios.yml` / `daily-publish.yml`) の `schedule:` をコメントアウトして上流での cron 自動実行を停止 (`workflow_dispatch` は残し手動実行は可)、(c) 上流テンプレでは Slack API コール / OpenAI API コール共に走らない暫定運用が確立。次のステップ: Step 7 で README/SETUP に fork 前提の運用フロー (Secrets 設定 / `.gitignore` 緩和 / cron 有効化) を記述、その後 private fork を作成して動作確認。
- **2026-05-10 (Default branch を live に切り戻した)** 上記の「Default = main」直後に Default を live に切り戻した (`gh repo edit --default-branch live`)。cron は live の workflow で走る運用に戻り、main は OSS テンプレ的に「fork されて使われる基本形」、live は「自前の cron 運用先」として位置付けを分離。新 live は main と同じ HEAD で `.gitignore` 緩和もなし、bot commit は引き続き skip され Slack API コールのみ走る暫定運用は変わらない (Step 7 で運用ディレクトリ集約 + .gitignore 設計と一緒に再構築)。
- **2026-05-10 (Step 6.6 整合化 + Step 6.7 切り出し + Step 7 拡張)** Step 6.6 のスコープ 4 項目は実装としては Step 6.5 と同時 (`c829994` 「feat: 週次バッチ生成 + 日次 publish の preflight 自動採用」) に組み込まれていたため ROADMAP を実態に合わせて ✅ に整合化。残課題「batch 失敗時のリトライ」を Step 6.7 に切り出し、ユーザー指定方針 (当日無ければ sync、翌日以降を batch 再投入) をスコープとして明文化。実装は実運用で失敗ケースの実態を見てから着手する。Step 7 (OSS 公開準備) のスコープに「運用ディレクトリ集約」(`scenarios/state/output/docs` を 1 ディレクトリにまとめる) を追加。
- **2026-05-10 (live ブランチを履歴ごと削除 + 新規作成、Default = main)** 旧 live が Step 5d 時代の汚れた状態 (config: text_rendering / anthropic+google deps / 旧 4 フォルダ content) で残っていたため、`gh repo edit --default-branch main` → `git push origin --delete live` → `git branch -D live` で remote + local + Default branch 設定を整理。直後に main 起点で `git checkout -b live && git push -u origin live` で新規 live を作成 (HEAD は main と同一)。利用者カスタム (`.gitignore` 緩和等) は Step 7 (運用ディレクトリ集約) で再設計してから乗せる。Default branch は main のままなので、cron は main の workflow で走り、main の `.gitignore` で scenarios/state/output/docs が ignore のため bot commit は skip される (Slack 投稿の API コールは走る点に注意、Step 7 まで暫定)。
- **2026-05-10 (画像サイズ 960x1280 を本番採用)** ep1 を 768/960/1152/1536 (px) で sync 生成して比較 (計 $0.53)、**960x1280 を本番デフォルトに採用** (`config.yaml` 反映済み)。sync $0.18 / batch 推定 $0.09、Slack 表示で全 dialogue + SFX 視認可、1536x2048 比 -33% コスト。768x1024 は Slack で文字が潰れて不採用、1152x1536 は SFX「ぶいーん」が矢印アイコン化される現象が 1 例で出たため将来の印刷向け候補として保留、1536x2048 は印刷品質が必要な場合のみ opt-in。実コストは output_tokens に比例し、ピクセル数 4x でも tokens は 1.85x 程度しか増えないことが判明 (Step 6.5 当時の見積より乖離小)。
- **2026-05-10 (Step 6.6 追加)** GitHub Actions も batch 画像生成に切り替える Step 6.6 を追加。weekly-scenarios で scenarios 生成→batch-submit-images、daily-publish で batch-fetch-images→publish-today (画像再生成 skip)。週次 $1.89 → $0.95 (50% off)。batch 失敗時の sync フォールバックは別途設計。
- **2026-05-10 (CLI 拡張)** `test panel` に `--image-size` フラグを追加 (`_apply_cli_overrides` を image_size 対応に拡張)。サイズ比較用途を想定。publish/publish-today/batch-submit-images にも将来同様のフラグ追加余地あり (現時点では config.yaml の編集で十分)。
- **2026-05-10 (新ガイダンス効果評価 ep1/ep5)** モデル別ガイダンス (Verbatim キャラ anchor / SFX 指示 / Sequential panel labels / Literal text in double quotes / Negative constraints 末尾集約) が **Step 6.5 ベースラインの品質水準を維持しつつ SFX 描画を明確に改善** することを 2 話で確認。ep1 では「さわ」「ぶいーん」、ep5 では「りーん」を Panel 1/2/3 連続描画。dialogue 17/17 一字一句一致、4 panel 厳守、話者スワップ 0/2。サンプル数が少ないため本番デフォルト化判定は ep2-4/6-7 を batch 投入して 7 話完走後に確定する。
- **2026-05-10 (Step 6.5 検証で確定)** **gpt-image-2 + 1536x2048 (真の 3:4) を本番採用**。W19 全 7 話で完全一致 6/7 (86%) / 致命的 0/7 / 軽微 1/7 (話者スワップのみ)。Step 6 の gpt-image-1 (0/7 完全一致 / 7/7 致命的) から劇的改善。1024x1536 は実 2:3 でアスペクト比ミスマッチが「パネル数違反」「誤字幻覚」の主因と判明。gpt-image-2 はカスタムサイズ可 (各辺 16 の倍数 / 最大 3840px / 比率 3:1 以下) で comics をユースケース筆頭に謳っており、テキスト描画精度・指示遵守ともに gpt-image-1 比で一段上。
- **2026-05-10 (Step 6.5)** OpenAI コール毎の token usage + コスト推定を実装。`UsageTracker` をクライアントに渡すと `complete` / `complete_structured` / `generate_image` の各レスポンスから `usage` を吸い上げ、`_PRICES` (2026-05-10 時点の標準料金) でコスト推定。`publish` 系は archive YAML の `usage` キーに per-model 集計を永続化。価格表は openai_client.py の冒頭にハードコード、料金改定時はそこを更新。
- **2026-05-10 (Step 6.5)** **OpenAI Batch API は `/v1/images/generations` をサポート、料金は 50% off、completion window 24h** を確認。`yonkomatic batch-submit-images --week W` / `batch-fetch-images --week W` の 2-step を実装。submit と fetch を分離する設計理由: (a) batch は最大 24h 待つので 1 コマンドで block するとプロセスが弱い、(b) cron で「Sun submit / Mon fetch」のように分けやすい、(c) 失敗時の再試行が独立しやすい。reference image (`images.edit`) は multipart 専用で batch 非対応 → batch 経路では参考画像をスキップ。
- **2026-05-10 (Step 6.5)** `ai.aspect_ratio` フィールドは API には渡らず archive metadata 専用かつ値が誤り (1024x1536 = 実 2:3 を "3:4" と誤記) だったので削除。同時に `schedule.publish_time` / `schedule.scenario_generation_dow` / `schedule.scenario_generation_time` (cron は workflow YAML 直書き、Python は読まない) と `news.language` (未参照) と `StateStore.auto_commit` メソッド (workflow が shell git で代替済み) も棚卸しして削除 (commit `88771d8`)。
- **2026-05-10 (Step 6 着手)** 4 軸の方針転換:
  1. **model_render 採用**: Step 5e の見送り判断 (29% 完全一致 / 14% 致命的バグ) は Flash 限定。OpenAI gpt-image-1/2 への切替と「8 割達成できていた」運用印象を踏まえ、デフォルトを `model_render` に倒し `pil_overlay` 系を完全廃止。検証は実装後に再実施。
  2. **AI ベンダー OpenAI 集約**: Anthropic + Google の 2 SDK → OpenAI 1 SDK。認証・課金・SDK を 1 社に。Structured Output で ScenarioWeek を JSON Schema 強制 → Pydantic validate → YAML 保存。`text_model: gpt-5.4`, `image_model: gpt-image-1` をデフォルト (`config.yaml` で上書き可)。
  3. **テンプレート外出し**: 埋め込み SYSTEM_PROMPT を `src/yonkomatic/templates/{scenario_prompt.md,panel_prompt.md}` (YAML frontmatter で system + body) に外出し。`{{var}}` 単純置換 (依存ゼロ、条件分岐は yonkomatic 側で前処理して吸収)。`content/` に同名ファイルを置けば利用者が上書き可能 (フォールバック方式)。
  4. **content/ 構造刷新**: 旧 4 フォルダ (`characters/world/samples/themes/`) → `prompt.md` + `images/` の 2 要素のみ。フォルダ名・ファイル名は AI に伝わらないため整理は意味がない、利用者の整理用は `images/` 配下のサブディレクトリ自由で吸収。月別テーマはシナリオ自動生成内で吸収して廃止。
  - **JSON → YAML 全面切替**: `scenarios/{week}.yaml`, `output/archive/{date}.yaml`, `state/state.yaml`。利用者編集対象 (scenarios) の可読性向上 + フォーマット統一。
  - **削除一括**: `panel/composer.py`, `panel/validator.py`, `assets/fonts/`, `scripts/install_fonts.py`, `text_rendering` config 全体, `Dialogue.kind` フィールド, CLI `--text-mode` オプション。互換性は破棄 (利用者ゼロ前提)。
- **2026-05-09 (Step 5e 検証で確定)** AI 描画モード (model_render) の本番採用は **見送り**。Flash + 7 話で完全一致 29% / 致命的バグ 14% (例: 「収穫はあった」→「収穫はお前あった」)。プロンプトを否定文で強化すると逆に重複・挿入が増える LLM の症状を観測 (v2 で悪化)。デフォルト `pil_overlay` 維持、`model_render` は実装として温存 (CLI フラグで opt-in 可)。Gemini 側のモデル世代が上がったタイミングで再検証。
- **2026-05-09 (Step 5e 実装で確定)** `text_rendering.mode` の literal を `pil_overlay` / `model_render` に改名。旧 `always` / `fallback` / `never` は廃止 (開発段階につき後方互換不要、利用者ブランチは pydantic validation で fail-fast)。AI 描画モードでは `Dialogue.kind` を Gemini に渡さない (AI のレイアウト判断に任せる + 複数吹き出し x kind 分岐の同時要求を避ける)。`gemini-3-pro-image-preview` を本命モデルとして検証する (公式にテキスト描画精度向上を謳う)。Imagen 4 は 2026-06-24 シャットダウン予定のため対象外。
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

- **GitHub Actions runner の Node.js 20 deprecation**: `actions/checkout@v4`, `astral-sh/setup-uv@v3` は Node.js 20 ベースで、2026-09-16 に runner から Node.js 20 が除去される。それまでに各 action を Node.js 24 対応版に上げる必要 (Step 7 の workflow 改修時に併せて対応推奨)。暫定的に `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` を env で設定して opt-in も可能。
- **OpenAI SDK バージョン**: `openai>=1.50.0` を使用 (`chat.completions` + `beta.chat.completions.parse` + `images.generate` / `images.edit`)。
- **OpenAI 画像 size の表記**: Gemini の "1K"/"2K" tier ではなく px 表記 (`"1024x1024"` / `"1024x1536"` / `"1536x1024"`)。yonkomatic の縦長 4 コマは `1024x1536` (3:4) が native。
- **gpt-image-1 のレート制限と料金**: 実装着手時 (2026-05-10) 詳細未調査。初回呼び出し時に確認しここに追記する。
- **MIME 自動補正**: 画像 API が JPEG を返す場合に拡張子を `.jpg` に補正するロジックは `cli.py:_save_image` に維持 (archive と static_site の両方で連動)。
- **(履歴 / 2026-05-09)** Gemini NO_IMAGE / Free Tier 制約 / Anthropic 529 overloaded / `text_rendering.mode = model_render` 実験的扱いといった旧 gotchas は Step 5e までの記録。Step 6 で AI ベンダー切替 + model_render 採用に伴い無効化。

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
