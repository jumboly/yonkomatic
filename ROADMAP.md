# Roadmap & Progress

このファイルは yonkomatic 実装進捗の **ライブステータス** です。Step 完了ごと・重要決定ごとに更新します。新セッションは必ずこのファイルを読んでから着手してください。

設計の原典は [`SPEC.md`](SPEC.md)。本ファイルは「いま何ができていて、次に何をやるか」のサマリ。

---

## 現在地

- **完了**: Step 1, Step 2, Step 3, Step 4, **Step 5 (5a/5b/5c/5d 全て + simplify)**, **Step 5e (実装 + A/B 検証完了)**, **Step 6 (実装完了 — テンプレ化 + OpenAI 切替 + 構造刷新)**, **Step 6.5 (gpt-image-2 + 1536x2048 採用、6/7 完全一致 / 0/7 致命的)**, **batch CLI (週単位 50% off)**, **モデル別ガイダンス機構 (scenario / panel-prompt 両 LLM)**
- **次**: 下記「次セッションの再開タスク」を片付けてから **Step 6.6 (Actions の batch 化)** → Step 7 (OSS 公開準備)
- **ブロッカー**: なし

最終更新: 2026-05-10 (新ガイダンス効果評価 ep1/ep5 + 画像サイズ最適化で **960x1280 を本番デフォルト採用**。Step 6.6 (Actions の batch 化) を追加。**参考画像を両 LLM ステージに告知する配線を実装** — 実 API 検証は残)

### 次セッションの再開タスク (Step 6.5 余波)

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

`pack.images` (`content/images/*`) を両 LLM ステージにも告知する配線を追加 (commit TBD)。

- **A 完了**: `ContentPack` に `reference_images_block` プロパティを追加 (空 list 時は空文字、画像ありなら `# 参考画像 (画像モデルに N 枚渡される)` セクション + Image 1: filename リスト + 「Image N 順序参照する」一文)。両テンプレ (`scenario_prompt.md` / `panel_prompt.md`) の system frontmatter に `{{reference_images_block}}` を差し込み (`news_block` と同パターン)
- **B 完了**: Image N 順序参照の guidance は block 内に集約 (`## 要件` に同じ bullet を重複させない方針 — block が画像ありのときだけ guidance を出すのでノイズが少ない)
- **C (将来)**: gpt-5.4 のマルチモーダル機能で実画像を LLM に見せる — 未着手

`examples/minimal/prompt.md` の `# 参考画像` セクションも書式例付きに差し替え (`Image 1 (01-yonko-front.png)`: ヨンコの正面立ち絵... のように利用者が各画像の意味を書ける書式)。

**残検証** (実 API):
- `uv run yonkomatic test panel --content examples/minimal --prompt "..."` で出力英語プロンプトに `Image 1:` 等のインデックス参照が出ることを目視
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

### ⏳ Step 6.6 — GitHub Actions も batch 画像生成に切替

**背景**: 現状の `daily-publish.yml` は毎朝 sync で 1 話ぶん画像生成 ($0.27/枚 × 7 = $1.89/週)。`batch-submit-images` / `batch-fetch-images` を使えば 50% off ($0.95/週)。週次で一括投入し、日次は fetch + publish のみで済む。

**スコープ**:
1. `weekly-scenarios.yml` を拡張: scenarios 生成直後に `batch-submit-images --week W` を実行 (24h cap で完走想定、月曜 09:00 JST には fetch 可能)
2. `daily-publish.yml` を改修: `publish-today` 内部で「preflight 画像が存在すれば再生成せず使う」分岐を追加 (画像 API コール skip)
3. preflight 画像が無いケース (batch 失敗 / 未投入) は従来通り sync で生成 (フォールバック)
4. 月曜の `daily-publish` で `batch-fetch-images` を先行実行する step を追加

**完了条件**:
- 通常運用で月〜日 7 日分の画像が batch 経由で生成され、daily-publish は fetch + publish のみで動く
- batch 失敗時は sync フォールバックで投稿は継続される (cron が止まらない)
- `state/batches/{week}.yaml` の status を見て分岐できる

**未決事項**: batch が 24h 以内に完走しなかった場合のリトライ戦略 (週途中で batch_id を再投入するか、その日だけ sync で繋ぐか)。

### ⏳ Step 7 — OSS 公開準備 (旧 Step 6) (次)

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
