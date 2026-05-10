# Roadmap & Progress

このファイルは yonkomatic 実装進捗の **ライブステータス** です。Step 完了ごと・重要決定ごとに更新します。新セッションは必ずこのファイルを読んでから着手してください。

設計の原典は [`SPEC.md`](SPEC.md)。本ファイルは「いま何ができていて、次に何をやるか」のサマリ。

---

## 現在地

- **完了**: Step 1〜4, **Step 5 全部** (5a/5b/5c/5d + simplify), **Step 5e** (実装 + A/B 検証、本番採用見送り), **Step 6** (テンプレ化 + OpenAI 切替 + 構造刷新), **Step 6.5** (gpt-image-2 → 960x1280 本番採用、**W21 全 7 話で 7/7 完全一致を確証**), **Step 6.6** (Actions の batch 化 — 実装は Step 6.5 と一体で完了済み), **Step 7a** (生成物の gh-pages 分離 — workflow を gh-pages worktree + symlink 経由に切替、main からランタイムを完全分離), **Step 7b** (`batch-resubmit-missing` CLI + manifest `retries[]` + daily-publish への best-effort step 配線、上限 2 回・prompt reuse、ローカル 5 ケース目視 OK), **Step 7c** (CONTRIBUTING.md 新規作成 — fork 運用前提 + 開発ルール明文化、README から「貢献」節経由でリンク), **Step 7d** (pytest 6 ファイル / 44 ケース新設 — schema / state / panel / news / static_site / batch manifest をオフラインモック化、`.github/workflows/ci.yml` で PR + main push に lint+test、`[dependency-groups].dev` に統一), **Step 7e** (README 全面リライト — 6 節構成 = Status/Demo/Quick Start/How it works/位置付け/リンク集、W21 ep4+ep5 を `assets/demo/` に並べて本番品質サンプル提示、章立て表で gpt-5.4 / gpt-image-2 / Publisher Protocol を要約), **Step 7f** (SETUP.md 全面改訂 — 旧 §7 「.gitignore 緩和」を削除して 12 節構成に再整理、§6 を gh-pages 体制に整合化、新 §10 GitHub Pages deploy + 新 §11 batch リトライ運用を追加、§0/§1 で private fork 推奨理由を機密性ベースに更新、§12 で `merge.ours.driver true` を「fork 後 1 度だけ」と明記)、batch CLI、モデル別ガイダンス機構 (scenario / panel-prompt 両 LLM)、参考画像 LLM 告知配線
- **次**: **Step 7g 観察期間** — 公開ライブデモ `jumboly/yonkomatic-demo` の運用観察。当初 fork 化を試みたが GitHub の制約 (同一アカウントが親と fork を両方持てない) で不可と判明、**upstream を mirror した独立 repo として再構築** (旧 repo は `yonkomatic-demo-old` に rename、main + gh-pages を新 repo に移植、scenarios/2026-W20.yaml + state/batches/2026-W20.yaml も引き継ぎ済)。新 repo に secrets / workflow permissions を再投入して 1 週間放置 → preflight 利用率 / batch 完走率を集計
- **ブロッカー**: 新 demo repo の secrets (`OPENAI_API_KEY` / `SLACK_BOT_TOKEN` / `SLACK_CHANNEL_ID`) と `workflow permissions=write` を user 操作で再投入する必要あり。それが済めば 5/11 (月) の daily-publish cron が W20 ep1 で動き始める

最終更新: 2026-05-10 (demo repo を fork 形態にできず独立 mirror で再構築 — **Step 7g 観察開始の前段整理**。初期に `git push` で立ち上げた `jumboly/yonkomatic-demo` が GitHub UI 上の fork ではないことが判明し、`gh repo fork` で fork 化を試みたが「同一ユーザーが親と fork を両方所有不可」の制約で失敗。判断: fork 関係を諦めて **upstream を mirror した独立 repo として再構築**。手順 = (1) 旧 repo を `yonkomatic-demo-old` に rename して退避、(2) `gh repo create` で新 `jumboly/yonkomatic-demo` を public で作成、(3) backup mirror から main を upstream/main に rebase で乗せ替えて push (commit `0bf726d`)、(4) gh-pages branch を mirror から push し scenarios/2026-W20.yaml + state/batches/2026-W20.yaml + index.html を引き継ぎ。Pages 設定 (gh-pages source + custom domain) は自動継承、custom_404 / cert / build 状態いずれも問題なし。**残り user 操作**: secrets 3 件 (`OPENAI_API_KEY` / `SLACK_BOT_TOKEN` / `SLACK_CHANNEL_ID`) を `gh secret set --repo jumboly/yonkomatic-demo` で再投入、`gh api -X PUT .../actions/permissions/workflow -f default_workflow_permissions=write` を実行。前ステップの JPEG q=90 PR (#1) は merge 済み (`5667f6b`)、demo の新 main は JPEG 化を含む。文書側は README §Demo を「独立 mirror」前提に修正済)

### Step 6.5 余波の懸案 — W21 batch で全件確証 (2026-05-10)

当初「次セッションでやる残課題」だった 3 件は W21 全 7 話 batch (7/7 完全一致, $0.6102) で一括確証済み:

1. **新ガイダンス効果** (Verbatim キャラ anchor / SFX 指示 / Sequential panel labels / Literal text in double quotes / Negative constraints 末尾集約) — ep1/ep5 の 2 サンプル評価 → W21 全 7 話で SFX 7 種 (「さらっ」「ぴらっ」「ひや〜」「しーん」「ゴトン…」「ピッ」「ぽつ」) が全描画、dialogue 56/56 一字一句一致
2. **画像サイズ最適化** — 768/960/1152/1536 比較で **960x1280 を本番採用** (`config.yaml` 反映済)、1536x2048 比 -33% コストで Slack/static_site の表示サイズに必要十分。実コストは output_tokens に比例し、ピクセル数 4x でも tokens は 1.85x のみ
3. **参考画像 LLM 告知配線** (commit `f445b74` + `efc225d`) — `ContentPack.reference_images_block` を追加、両テンプレ (`scenario_prompt.md` / `panel_prompt.md`) の system frontmatter に `{{reference_images_block}}` 挿入。W21 全 7 話でキャラ造形が一貫 (ヨンコの黒髪ボブ+丸眼鏡+白セーター+藍オーバーオール、マチカの茶髪ポニテ+赤パーカ)

---

## Step 進捗

### ✅ Step 1 — 土台 + Slack 疎通 (commit `2216b0a`)

uv ベースの Python パッケージ骨格 + typer CLI + Pydantic config + `Publisher` Protocol + `SlackPublisher` (`files_upload_v2`)。`workflow_dispatch` 専用の test-slack workflow でローカル・GHA 両方から疎通確認。

### ✅ Step 2 — 画像生成コア (commit `a3d6f70`)

scenario/schema (Pydantic) + Anthropic/Gemini クライアント + `panel/description.py` で英語統合プロンプト合成。`test gemini` / `test panel` で実 API による 4 コマ生成確認。

### ✅ Step 3 — E2E パイプライン + マルチパブリッシュ (commit `1eff27f`)

「1 コマンドでシナリオ → 画像 → 複数プラットフォーム同時投稿」を Slack + static_site で達成。`publisher/static_site.py` (Jinja2 で docs/ 出力)、`ThreadPoolExecutor` で Publisher 並列化、Publisher 失敗は `PublishResult(ok=False)` で独立伝播。アーカイブは `output/archive/{date}.{ext}` フラット構造。Discord publisher と PIL オーバーレイは Step 4/5 へ送り。

### ✅ Step 4 — 週次シナリオ + 時事ネタ + 自動化 (commits `76e8061` / `3a6a033` / `4b76c68` / `83bd54b`)

4a: `scenario/generator.py` + `generate-scenarios` CLI (1 コール 7 話一括、フェンス + ブレース平衡スキャンで前置き耐性)。4b: `news/fetcher.py` (feedparser, feed 単位例外吸収, 15s socket timeout)。4c: weekly/daily 両 workflow + `publish-today` ([--date] でなければ ISO 週逆算、`_publish_episode_pipeline` を `publish` と共有)。4d: `SlackPublisher.notify_failure` + `_notify_failure` ヘルパ、`publish-today` の 3 障害ポイント (scenarios 枯渇 / episode 不在 / pipeline 失敗) で通知。

### ✅ Step 5 — 日本語テキストオーバーレイ (PIL 後段合成) (commits `550edc6` / `4fba95f` / `9c04939` / `66b73b3` / `b6508b5` / `4c18d29` / `4ed0412`)

Step 4 ライブ検証で Gemini Flash が複数吹き出しの日本語を幻覚することが判明。SPEC 元設計の PIL オーバーレイ方式に戻して本実装。5a: Gemini プロンプトに「吹き出し・テキスト・空形状の禁止」明示 + `Dialogue.kind` (speech/thought/shout) 追加。5b: `panel/composer.py` PIL 本実装 (4 panel 縦等分 + 形状別 drawer + 横幅ラップ + 簡易禁則)。5c: config デフォルトを `always` に切替、GHA に Noto フォント cache + install。5d: live cron 検証で空吹き出し問題を追加 fix (`4c18d29`)。1K Gemini で 4 panel × 5 dialogue 全件一字一句一致を確認。

### ✅ Step 5e — AI 描画モード (model_render) 実装 + 見送り判断

PIL オーバーレイ vs AI 描画を `--text-mode pil_overlay|model_render` で切替可能にし、Gemini Flash で 7 話 A/B 検証。**結果**: 完全一致 2/7 (29%) / 致命的バグ 1/7 (例: 「収穫はあった」→「収穫はお前あった」) / 軽微逸脱 4/7。プロンプトを否定文で強化すると **悪化** (典型的な LLM 症状)。**判定**: デフォルト `pil_overlay` 維持、`model_render` は CLI フラグで opt-in。Step 6 で OpenAI 切替時に再評価 → 採用。

### ✅ Step 6 — 全面リファクタ (テンプレ化 + OpenAI + 構造刷新 + model_render 採用) (commit `1646742`)

(1) SYSTEM_PROMPT を `src/yonkomatic/templates/{scenario_prompt,panel_prompt}.md` に外出し (frontmatter Markdown + `{{var}}` 単純置換)、利用者は `content/` に同名ファイルで上書き可能。(2) content/ を旧 4 フォルダ → `prompt.md` + `images/` の 2 要素に刷新。(3) Anthropic + Google → OpenAI 1 SDK 集約 (text=gpt-5.4 / image=gpt-image-1、Structured Output で ScenarioWeek validate)。(4) `panel/composer.py` / `panel/validator.py` / `assets/fonts/` / `text_rendering` config / `Dialogue.kind` を一括削除。(5) JSON → YAML 全面切替。

**検証結果**: gpt-image-1 + 1024x1536 (= 実 2:3) では W19 全 7 話で 0/7 完全一致 / 7/7 致命的バグ (2-3 コマ生成 + 誤字幻覚)。**根本原因 = アスペクト比ミスマッチ** (gpt-image-1 は 2:3/1:1/3:2 のみ、真の 3:4 を提供しない) + gpt-image-1 の文字精度が Flash 同等以下。実装は完成しているが本番採用は保留 → Step 6.5 で gpt-image-2 に切替て再検証。

### ✅ Step 6.5 — gpt-image-2 採用 + batch CLI + cost tracking (commits `e7873a6` / `ef5a49f` / `a08c677` / `88771d8` / `c829994`)

config を `gpt-image-2` + `image_size: "1536x2048"` (真の 3:4) に切替。`UsageTracker` で per-model コスト集計を archive YAML の `usage` キーに永続化。`/v1/batches` 経由の週単位 batch CLI (`batch-submit-images` / `batch-fetch-images`、50% off / 24h window) を追加。

**検証結果**:
- W19 全 7 話 (1536x2048 sync, ~$2.04): **完全一致 6/7 / 致命的 0/7 / 軽微 1/7** (Step 6 の 0/7 → 6/7 と劇的改善、軽微 1 件は ep3 の話者スワップ)
- W21 全 7 話 (960x1280 batch + 新ガイダンス + 参考画像配線、$0.6102): **完全一致 7/7 / 致命的 0/7 / 軽微 1/7** (ep3 で dialogue が鉤括弧付き吹出装飾、テキストは完全一致)
- batch 完了時間: submit から **約 11 分 22 秒** (24h window に対して非常に高速)

**本番採用構成 (確定)**: gpt-image-2 + 960x1280 + 新ガイダンス (Verbatim キャラ anchor / SFX 指示 / Sequential panel labels / Literal text in double quotes / Negative constraints 末尾集約) + 参考画像 LLM 告知 + batch 投入。Step 6.5 W19 ベースラインを上回る品質を実証。

### ✅ Step 6.6 — GitHub Actions も batch 画像生成に切替 (commit `c829994`、Step 6.5 と一体)

weekly-scenarios で `batch-submit-images` 投入、daily-publish で `batch-fetch-images` 先行実行 (`continue-on-error: true`)、`publish-today` は preflight 存在時に再生成 skip / 不在時に sync フォールバック。週次コスト $1.89 → $0.95 (50% off) を実現。実運用検証は Step 7g (OSS 公開後の private fork 1 週間観察) に持越し。

### ✅ Step 6.7 → Step 7b として実装 (2026-05-10)

batch 失敗時の自動リトライは下記 §Step 7b で実装。`batch-resubmit-missing` CLI + manifest `retries[]` 配列 + daily-publish への best-effort step、上限 2 回、初回 prompt reuse。

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

#### ✅ Step 7a — 生成物の gh-pages 分離 (commit `4d10099`)

両 workflow が `git worktree add .gh-pages gh-pages` で orphan branch をぶら下げ、root 直下に 4 本の symlink (`scenarios -> .gh-pages/scenarios` 等) を張ってから CLI を実行。`cli.py` 完全無改修、main の `.gitignore` から `/scenarios/`, `/state/`, `/output/`, `/docs/*` を削除し `/.gh-pages/` + 末尾なしの `/scenarios` `/state` `/output` `/docs` (symlink 捕捉) に置換。gh-pages 初期化は workflow 内フォールバック (`git fetch origin gh-pages` の有無で分岐、無ければ `index.html` プレースホルダで orphan commit + push)。state.yaml race は `git pull --rebase --autostash origin gh-pages` で吸収、`concurrency` group は入れない。

#### ✅ Step 7b — batch 自動リトライ (commit `5f38429`)

`batch-resubmit-missing --week W` CLI 新規 + manifest `retries: [...]` 配列追記方式 + `daily-publish.yml` に best-effort step 追加。pending 判定は `state.history` × week filter (published 集合) ∧ `_find_preflight_image` 不在の AND。初回 `jobs[].rendered_image_prompt` を reuse (text LLM コストなし、archive metadata 整合)。上限 2 回 (`_MAX_BATCH_RETRIES = 2`)、3 回目以降は warn + exit 0 で sync フォールバック。main batch 未完了時はガード (`manifest.status != "completed"` で skip、二重投入防止)。`_drain_batch_results` ヘルパ抽出で result 書き出しを共用化。

#### ✅ Step 7c — CONTRIBUTING.md 新規作成 (commit `e528ab8`)

9 章構成で fork 運用前提 + 上流 PR 流儀 + 開発ルールを明文化。Issue/PR テンプレートは置かない (テンプレ専用リポゆえ流入を絞る)。Code of Conduct は inline。Issue は再現手順あるバグのみ、要望・質問は Discussions。README に「貢献」節 1 段落で導線。

#### ✅ Step 7d — ユニットテスト + CI lint (commit `be7d287`)

`tests/` フラット構成で 6 ファイル 44 ケース (schema / state / panel / news / static_site / batch manifest)、すべて `MagicMock(spec=...)` + `mocker.patch` でオフライン化、`uv run pytest` 約 0.5s 完走。`.github/workflows/ci.yml` を PR + main push トリガーで新設、`uv run ruff check src/ tests/` + `uv run pytest` を 1 job 統合。dev deps を `[dependency-groups].dev` に統一 (PEP 735 準拠)。`conftest.py` は作らず各ファイルでローカルヘルパ。`_load_batch_job_meta` テストは `monkeypatch.chdir(tmp_path)` で CWD 隔離必須。coverage / integration テストは未導入。

#### ✅ Step 7e — README リライト + Quick Start + デモ画像 (commit `c06a637`)

README を 6 節構成 (Status / Demo / Quick Start / How it works / 位置付け / リンク集 / ライセンス) に全面書き換え。W21 ep4 (静かな通知音) と ep5 (傘の待機列) の本番品質サンプル 2 枚を `assets/demo/` に配置 (屋内 SFX × 屋外オチで雰囲気差)。Demo URL は fork 後の `https://<your>.github.io/yonkomatic/` 例として注記 (上流テンプレは cron 停止のため deploy なし)。Status 行は「Step 7 着手中、7a〜7d 完了、本 README は 7e」表記、7g 完了後に「Step 7 完了」へ書き換え予定。

#### ✅ Step 7f — SETUP.md 全面改訂 (commit `a7ba45f`)

12 節構成に再整理。旧 §7「.gitignore 緩和」を **完全削除** (Step 7a の worktree + symlink で利用者編集不要に)、§6 を「push 先 = orphan gh-pages branch only」に整合化、新 §10 GitHub Pages 設定 + 新 §11 batch 失敗時の自動リトライを独立節として追加 (3 段階リカバリ + 観測方法)、§0/§1 で private fork 推奨理由を「Bot Token security + 生成物機密性」に書き換え、§12 で `merge.ours.driver true` を「fork 直後 1 度だけ」と明記。CONTRIBUTING.md:34 の `SETUP.md §4` (= `.env`) 参照は位置不変。Python コード / config / workflow 変更なし、ruff 緑。

#### ⏳ Step 7g — public demo repo (`jumboly/yonkomatic-demo`) で 1 週間観察 + 公開展示

**スコープ**: 7a/7b/7d/7f の成果が乗った main を **upstream の public demo fork** (`jumboly/yonkomatic-demo`) に取り込み、cron を有効化して 1 週間放置。upstream 訪問者が gh-pages でライブの bot 出力を確認できる状態にする。preflight 利用率と batch 完走率を ROADMAP に記録。

**当初の private fork 検証から public demo repo に格上げした理由** (2026-05-10): Step 7g 検証 + OSS テンプレートの「動いている実例」展示の両方を一石二鳥で達成するため。SETUP.md §1 の private fork 推奨は「自分の作品の機密性 + Bot Token 漏洩リスク」が根拠で、demo は upstream のサンプル素材 (W21 ep4/5 等) を使い機密性が低いため public で問題ない。upstream main との差分は workflow schedule の 2 行 × 2 ファイルのみ (片方向 sync で merge cost 限定)。ROADMAP L177 「テンプレ専用 main / fork で運用」方針とも整合 (= 二重運用 main+live で過去に廃止した live ブランチ路線とは別物)。

**完了条件**:
- demo repo で 7 日連続 daily-publish が緑 (Slack 投稿成功 + gh-pages push 成功)
- 期間中に最低 1 回 weekly-scenarios cron が走り gh-pages に scenarios + batch manifest が積まれる
- preflight 利用率 (= 7 話中、preflight ヒットした話数) を ROADMAP に記録 (期待値 7/7、batch 不調なら 5〜6/7)
- batch 完走率 (= 完走した batch / 投入した batch) を記録
- 7b のリトライが発火する障害ケースが観察できた場合、原因と挙動を Decisions Log に追記
- upstream README に demo URL (`https://jumboly.github.io/yonkomatic-demo/`) と demo repo URL (`https://github.com/jumboly/yonkomatic-demo`) が掲載済み (本コミットで対応)
- 観察完了後 upstream README の Status 行を「Step 7 完了」に書き換え

**初回 dispatch の挙動 (2026-05-10 日曜夜)**:
- weekly-scenarios `workflow_dispatch` (run 25626943475) → 翌週 `2026-W20` 7 話分のシナリオ + batch submit 成功
- daily-publish `workflow_dispatch` (run 25626995999) → 当日 `2026-W19` のシナリオ不在で `scenarios file not found` 失敗 (Slack に失敗通知が飛んだ)
- 原因 = 日曜は cron 設計上 *翌週* を作るタイミングなので、今日 W19 のシナリオが歴史的に存在しないだけ。月曜 09:00 JST の自動 cron で W20 day1 が初回 publish される予定 → 観察期間は実質月曜開始
- gh-pages branch は workflow 初期化フェーズで自動作成済み (placeholder `index.html` 1 個)
- GitHub Pages 設定済み (`gh api -X POST /repos/jumboly/yonkomatic-demo/pages` で `gh-pages /(root)`)。upstream user 全体に設定された custom domain `www.jumboly.jp` が継承され、公開 URL は `https://www.jumboly.jp/yonkomatic-demo/`

**影響ファイル**: `ROADMAP.md` (現在地 / Step 7g / Decisions Log), `README.md` (Demo 節は本コミットで demo URL を追加済み)

**未決事項**:
1. 観察中に致命的でない修正が必要になった場合は demo repo に直接 commit (upstream main との merge 競合は workflow yaml の schedule 行のみ、`merge.ours.driver true` で content/ は保護済み)
2. cron 観察ログ → **推奨: `tmp/step7-live-log.md` に手書きメモ、ROADMAP には要点のみ転記**
3. 観察で「一括 batch」の運用課題 (rate limit / 部分失敗時のリカバリ複雑度 / シナリオ差し替え不可など) が顕在化したらバックログ「ローリング batch」を Step 7i 候補に昇格

**demo repo 立ち上げの実施事項 (2026-05-10)**:
- ローカル `/Users/masa/src/yonkomatic` を起点に `/Users/masa/src/yonkomatic-demo` をローカル clone、upstream remote を `https://github.com/jumboly/yonkomatic.git` に設定、`merge.ours.driver true` を有効化
- `gh repo create jumboly/yonkomatic-demo --public --source=. --remote=origin --push` で GitHub に public 新規 repo を作成
- workflow schedule アンコメント (weekly: `0 14 * * 0` UTC、daily: `0 0 * * *` UTC) を demo 単独 commit (`5530f02 ci(demo): enable cron schedule for live demo`)
- secrets (`OPENAI_API_KEY` / `SLACK_BOT_TOKEN` / `SLACK_CHANNEL_ID`) を `gh secret set` で stdin 経由設定 (.env 流用、SLACK_CHANNEL_ID は upstream 共用テスト channel)
- workflow permissions を `default_workflow_permissions=write` に (`gh api -X PUT /repos/jumboly/yonkomatic-demo/actions/permissions/workflow`)
- 初回 `workflow_dispatch` で gh-pages branch 自動初期化 + Slack 疎通確認
- Pages を `gh-pages /(root)` に設定して `https://jumboly.github.io/yonkomatic-demo/` を公開

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

- **2026-05-10 (Step 7g 着手 — public demo repo `jumboly/yonkomatic-demo` 立ち上げ)** 当初の Step 7g 計画 (private fork 1 週間観察) を **public demo repo に格上げ**。理由: Step 7g 検証 + OSS テンプレートの「動いている実例」展示の両方を一石二鳥で達成できるため。SETUP.md §1 の private 推奨は「自分の作品の機密性 + Bot Token 漏洩リスク」が根拠で、demo は upstream のサンプル素材を使う + secrets は Repo Secrets として隠蔽されるため public で問題なし。**実施事項**: (1) ローカル `/Users/masa/src/yonkomatic` から `/Users/masa/src/yonkomatic-demo` にローカル clone → upstream remote を `https://github.com/jumboly/yonkomatic.git` に → `merge.ours.driver true` 有効化、(2) demo 側 `.github/workflows/{daily-publish,weekly-scenarios}.yml` の `schedule:` をアンコメント (1 commit `5530f02 ci(demo): enable cron schedule for live demo`)、(3) `gh repo create jumboly/yonkomatic-demo --public --source=. --remote=origin --push` で GitHub に public repo を新規作成 (fork 関係はつけない、独立 repo として管理)、(4) `gh secret set` 3 件 (`OPENAI_API_KEY` / `SLACK_BOT_TOKEN` / `SLACK_CHANNEL_ID`、stdin 経由で値を context に入れない、SLACK_CHANNEL_ID は upstream 共用テスト channel)、(5) `gh api -X PUT /repos/jumboly/yonkomatic-demo/actions/permissions/workflow` で `default_workflow_permissions=write` に、(6) `gh api -X POST /repos/jumboly/yonkomatic-demo/pages` で `gh-pages /(root)` を Pages source に。**未確定事項 — 採用しなかった案**: (a) `git repo fork` ではなく独立 repo にした (同一アカウント内での fork は GitHub の制約あり、また独立 repo の方が demo の workflow schedule 差分が clean)、(b) demo を private にしなかった (展示効果優先)、(c) ローリング batch 化 (週次は Day 1 のみ submit、daily で fetch fail なら sync + 翌日 submit) を **採用しない**: Step 7g「実証ベースで判断」原則に基づき、現状の「weekly 一括 batch + daily fetch」のまま 1 週間観察し、実際の運用課題が出てから設計変更を検討 (Step 7i 候補としてバックログ)。**初回 dispatch 結果**: weekly success (W20 シナリオ + batch submit 成功)、daily fail (W19 シナリオ不在 — 日曜実行の構造的制約、月曜以降の cron では発生しない)。Slack 通知は test channel に出たため運用問題なし。**修正ファイル**: `README.md` (Demo 節に live URL `https://www.jumboly.jp/yonkomatic-demo/` と demo repo URL を追加、`assets/demo/*.png` の本番品質サンプルはそのまま維持)、`ROADMAP.md` (現在地 / Step 7g 全体書き換え / Decisions Log)。Python コード / config / content / pyproject.toml / uv.lock 変更なし。
- **2026-05-10 (Step 7 まとめ /simplify)** Step 7 全体 (7a〜7f) を 5 エージェントで横断レビュー。FIX 2 件: (1) **`templates/panel_prompt.md` L14-17 のトリム** — 「各 dialogue 行を発言者ごとに白い吹き出しに入れ、入力された日本語テキスト...英訳しない」を削除し、L18-25 の英語 literal embedding (`do NOT paraphrase, translate, romanize, ...`) に責務統一。Step 5e 教訓「否定文を増やすと逆に失敗が増える」に整合、(2) **ROADMAP.md スリム化 720 → 272 行 (-62%)** — 完了 Step (1-7e) の検証表 / A/B 比較表 / サブステップ詳細を圧縮、Step 6.5 余波ログを 8 行に、Step 6.6/6.7 を参照ポインタに、Decisions Log の 2026-05-08〜09 古いエントリ全削除 (CLAUDE.md と本文 Step に集約済み、git log で追跡可)。**SKIP 判断**: prompt HIGH 2 (`content/prompt.md` 参考画像セクション削除) と MEDIUM 2 (scenario/generator.py L52「話者スワップ稀発」削除) は W21 7/7 達成構成への regression risk があり保留 — content/prompt.md の参考画像セクションは auto-generated `reference_images_block` と相補的 (semantic vs filename listing)、話者スワップ稀発記述は L57「話者の毎パネル再記述」mitigation の根拠。code 系 medium (manifest stringly-typed → Literal、test assertion メッセージ追加、workflow composite action) はすべて intentional / 効果に見合わず skip。`uv run ruff check src/ tests/` 緑、`uv run pytest` 44 passed (0.46s)。
- **2026-05-10 (Step 7f 実装完了)** SETUP.md を 12 節構成に全面改訂し、Step 7a (gh-pages worktree + symlink) と Step 7b (batch リトライ) の利用者向け運用ドキュメントを整備。**確定した方針**: (1) **§7「.gitignore を緩和」(L112-128, 17 行) を完全削除** — Step 7a で worktree + symlink により利用者の `.gitignore` 編集が不要になったため、旧手順は誤情報になる。後続節 (旧§8/§9/§10/§11) を 1 つずつ繰り上げ、(2) **GitHub Pages 設定は独立節 §10** として詳述 (§6 Permissions と一体化しない理由: Pages の Branch ドロップダウンに `gh-pages` が出るのは初回 workflow_dispatch 後で、§9 動作確認の直後に置くと時系列で依存関係が読める)。手順は Settings → Pages → Source = `Deploy from a branch`、Branch = `gh-pages` / `(root)`。Slack のみで済ます場合は skip 可だが gh-pages branch は CI が常に使うため削除しないことを明記、(3) **batch リトライは独立節 §11** として詳述 (§8 cron 設定や trouble shoot に分散させない)。3 段階リカバリ = `batch-fetch-images` (best-effort) → `publish-today` の sync フォールバック → `batch-resubmit-missing` (上限 2 回 / preflight 不在 + 未投稿のみ / 初回 prompt 再利用で text LLM 追加コストなし)。観測方法 = `state/batches/{week}.yaml` の `retries[]` 配列 + Actions ログで `resubmitting N episode(s) (epX, epY) as retry #M of 2` を grep、(4) **§0/§1 の private 推奨理由を更新** — 旧「Slack 投稿アーカイブを含む」→ 新「Bot Token security + 生成物の機密性 + workflow 改変による token 漏洩リスク削減」を 3 bullet で根拠提示、(5) **§6 Workflow permissions** を「push 先 = orphan `gh-pages` branch only、main は変更されない」に書き換え、初回 dispatch でのプレースホルダ自動初期化に言及、(6) **§12 上流取り込み** で `merge.ours.driver true` を「fork 直後 (clone した作業ディレクトリで) 1 度だけ」と明記、別マシンで clone し直したら再実行が必要なことを補足。衝突しうる箇所のリストから `.gitignore` を削除し `workflow の schedule:` のみに、(7) **CLAUDE.md 同期は不要** — CLAUDE は開発者向け、SETUP は利用者向けで責務分離が既に成立、(8) **CONTRIBUTING.md:34 への影響なし** — `SETUP.md §4` (= `.env`) を参照しているが、§7 削除後も §4 は位置不変。**修正**: `SETUP.md` (234 行近く維持、差分 -17 / +29 / 修正 ~30)。Python コード / config / workflow への変更なし、`uv run ruff check src/ tests/` 緑。Step 7g (private fork 実運用検証) が次。
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

> 2026-05-08〜09 の Step 1-5 実装期の Decisions は CLAUDE.md (運用ルール) と本文 Step セクション (設計判断) に集約済みのため削除。歴史的経緯が必要な場合は `git log` を参照。

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

- ローリング batch (Step 7g 観察で「一括 batch」の運用課題が顕在化したら検討) — 週次は Day 1 のみ submit、daily は fetch → なければ sync fallback → 翌日分を batch submit。利点: batch 失敗の影響が 1 日分に局所化、シナリオ差し替えの余地。欠点: daily の責務肥大化、連鎖故障時に sync 連発でコスト増 (50% off 失効)
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
