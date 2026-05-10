# SETUP

yonkomatic を **自分のリポジトリ (fork) で運用する** ためのセットアップ手順です。

上流リポジトリ (`jumboly/yonkomatic`) は **テンプレート専用** で cron は停止しています。実運用するには fork が必要です。

---

## 0. 前提

- GitHub アカウント
- Python 3.12 以上
- [uv](https://github.com/astral-sh/uv) (推奨インストール: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [gh CLI](https://cli.github.com/) (任意、`gh secret set` などを使う場合)
- OpenAI API キー (<https://platform.openai.com/api-keys>)
- Slack Bot Token + Channel ID (Slack に投稿する場合、後述)
- **fork は private を強く推奨** (Bot Token を Secrets に置く運用 + 生成物に含まれる Slack 投稿履歴・キャラ素材の機密性のため。詳細は §1)

## 1. fork する

GitHub の標準 fork は public になります。以下の理由で **private 化を強く推奨**します:

- 生成物 (`scenarios/`, `state/`, `output/archive/`) は CI が orphan `gh-pages` branch に push します。これらには 4 コマ画像・台詞・state.yaml の publish 履歴が含まれ、自分の作品として外部に出すまでは非公開にしておきたい
- Bot Token (`SLACK_BOT_TOKEN`) は Secrets に置きますが、public リポジトリでは workflow 改変による token 漏洩リスクが pull request 経由で増える
- 上流テンプレに改善が入った際の `merge upstream/main` が public でも private でも同じく動く

### A. Public fork でよい場合

GitHub UI → 上流リポジトリの "Fork" → 自分のアカウントを選択。

CLI:

```bash
gh repo fork jumboly/yonkomatic --clone --remote
```

### B. Private fork にしたい場合 (推奨)

```bash
# 上流をローカルに bare clone してから、private 新規リポジトリに push
git clone --bare https://github.com/jumboly/yonkomatic.git
cd yonkomatic.git
gh repo create <YOUR_USER>/yonkomatic-mine --private --source=. --push
cd ..
rm -rf yonkomatic.git

# 作業用ディレクトリで再度 clone、上流を upstream として登録
git clone https://github.com/<YOUR_USER>/yonkomatic-mine.git
cd yonkomatic-mine
git remote add upstream https://github.com/jumboly/yonkomatic.git
```

以降の手順は fork 先 (`<YOUR_USER>/yonkomatic-mine`) で実施します。

## 2. ローカル環境

```bash
uv sync
uv run yonkomatic --help
```

`yonkomatic` コマンドが表示されれば OK。

## 3. Slack Bot を作る

1. <https://api.slack.com/apps> から **Create New App** → **From scratch**
2. App 名 (例: `yonkomatic`) と投稿先ワークスペースを選択
3. 左メニューの **OAuth & Permissions** → *Scopes* セクションで **Bot Token Scopes** に追加:
   - `chat:write`
   - `files:write`
   - `channels:read`
4. 同ページ上部の **Install to Workspace** → 承認
5. インストール後の **Bot User OAuth Token** (`xoxb-...`) を控える
6. 投稿先チャンネルで `/invite @yonkomatic` (Bot 名) してチャンネルに参加させる
7. Slack でチャンネル名を右クリック → *Copy link*、URL 末尾の `Cxxxxxxxxxx` がチャンネル ID

## 4. .env を作ってローカル動作確認

```bash
cp .env.example .env
# 以下を埋める:
#   OPENAI_API_KEY=sk-...
#   SLACK_BOT_TOKEN=xoxb-...
#   SLACK_CHANNEL_ID=Cxxxxxxxxxx

uv run yonkomatic test slack       # Slack 疎通
uv run yonkomatic test panel       # シナリオ → text LLM → 画像生成 (実 API)
```

`test panel` の出力は `tmp/verify/panel/<timestamp>/` に保存されます。

## 5. GitHub Actions Secrets を設定

GitHub UI: 自分の fork → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** で以下を登録:

- `OPENAI_API_KEY`
- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL_ID`

CLI (gh):

```bash
gh secret set OPENAI_API_KEY -R <YOUR_USER>/yonkomatic-mine
gh secret set SLACK_BOT_TOKEN -R <YOUR_USER>/yonkomatic-mine
gh secret set SLACK_CHANNEL_ID -R <YOUR_USER>/yonkomatic-mine
```

## 6. Workflow permissions を有効化

cron は `scenarios/`, `state/`, `output/archive/`, `output/preflight/`, `docs/` を **orphan `gh-pages` branch (worktree)** に commit + push します。Actions に書き込み権限を与えてください。

GitHub UI: 自分の fork → **Settings** → **Actions** → **General** → **Workflow permissions**:

- ☑️ **Read and write permissions** を選択
- **Allow GitHub Actions to create and approve pull requests** はチェック不要

push 先は **fork 先リポジトリ内の `gh-pages` branch のみ** で、`main` は変更されません (workflow が `git worktree add .gh-pages gh-pages` で orphan branch をぶら下げ、CLI が symlink 経由で書き込んだ後に `gh-pages` 側で `git push origin gh-pages` する)。`gh-pages` branch が存在しない初回 dispatch では、workflow がプレースホルダで自動初期化します。

## 7. cron schedule を有効化

`.github/workflows/weekly-scenarios.yml` と `daily-publish.yml` の `schedule:` 行はテンプレ側でコメントアウトされています。fork 先で有効化:

```diff
# .github/workflows/weekly-scenarios.yml
on:
- # schedule:
- #   - cron: "0 14 * * 0"
+ schedule:
+   - cron: "0 14 * * 0"
  workflow_dispatch:
```

```diff
# .github/workflows/daily-publish.yml
on:
- # schedule:
- #   - cron: "0 0 * * *"
+ schedule:
+   - cron: "0 0 * * *"
  workflow_dispatch:
```

cron は **fork 先のデフォルトブランチ** にある workflow を読みます。デフォルト = main 推奨。

## 8. 自前のキャラ素材を持ち込む

`content/prompt.md` と `content/images/` を自分の作品に置き換えます。上流リポには動作確認用の AI 生成サンプル素材が同梱されているので、最初はそのままでも動作確認できます。

- `content/prompt.md`: キャラクター / 世界観 / 画風を 1 ファイルにまとめる (Markdown 自由形式)
- `content/images/*.png`: キャラ参考画像。順序を制御したければ `01-front.png` のような numeric prefix を使う
- `content/sample-scenario.yaml`: `test panel` 等の検証用シナリオ。任意で削除/上書き可

```bash
# 自分の作品に書き換える例
rm content/images/*.png
cp ~/your-art/*.png content/images/
$EDITOR content/prompt.md
```

リポジトリルートの `.gitattributes` には `content/* merge=ours` が設定されているため、上流から更新を取り込んでも自分のカスタムは保護されます。

## 9. GitHub Actions で動作確認

`workflow_dispatch` で 1 回手動実行して動くか確認します。

```bash
# 翌週分のシナリオ生成 + 画像 batch 投入
gh workflow run weekly-scenarios.yml -R <YOUR_USER>/yonkomatic-mine

# 1 日後 (batch 完走後) に daily publish を試す
gh workflow run daily-publish.yml -R <YOUR_USER>/yonkomatic-mine
```

GitHub UI の **Actions** タブで実行ログを確認、Slack に投稿されれば成功。

成功したら cron に任せて毎日の自動投稿が回ります。

## 10. GitHub Pages を有効化 (任意)

cron が回り始めると 4 コマアーカイブを静的サイトとして公開できます。Slack 投稿だけで済ませたい場合はスキップして構いません (gh-pages branch は CI が常に使うため、削除しないでください)。

**前提**: §9 の `workflow_dispatch` を 1 回成功させ、`gh-pages` branch が自動初期化済みであること (Pages の Branch ドロップダウンに `gh-pages` が出ない場合は branch 未作成、まず workflow を 1 回回す)。

GitHub UI: 自分の fork → **Settings** → **Pages** → **Build and deployment**:

- **Source**: `Deploy from a branch`
- **Branch**: `gh-pages` / `(root)`
- **Save**

数分後、`https://<YOUR_USER>.github.io/yonkomatic-mine/` (リポジトリ名に応じて変わる) で `docs/index.html` が公開されます。以降の cron run のたびに最新エピソードが追加されます。

## 11. batch 失敗時の自動リトライ

週次 `batch-submit-images` は OpenAI image batch API を使って 7 話分を一括生成します (sync 比 50% off / completion window 24h)。infra 起因で expire や個別 job の失敗が発生した場合、以下の **3 段階で自動リカバリ** されます。利用者の手動介入は不要です。

1. **当日朝**: `daily-publish` の `Fetch weekly image batch (best-effort)` step が `batch-fetch-images` で preflight 取得を試みる
2. **preflight 不在の話は sync フォールバック**: `publish-today` がその話だけ通常 API で生成して投稿 (1 話あたりコスト 2x だが投稿は止まらない)
3. **publish 後の再投入**: `Resubmit missing batch jobs (best-effort)` step が **未投稿 + preflight 不在のエピソードのみ** を新しい batch に投入。初回の prompt を再利用するため text LLM 追加コストなし。**上限 2 回**

3 wave (初回 + リトライ 2 回) を消化しても画像が揃わない話は、以降ずっと sync フォールバックで投稿継続されます (cron は止まらない)。

### 観測方法

- `gh-pages` branch の `state/batches/{week}.yaml` の `retries[]` 配列で再投入履歴を確認
- Actions ログで `resubmitting N episode(s) (epX, epY) as retry #M of 2` を grep
- 再投入が走らない正常パターンは `nothing to resubmit — all pending episodes have preflight`

## 12. 上流から更新を取り込む

上流テンプレに改善が入ったら fork 先に取り込みます。リポジトリルートの `.gitattributes` で `content/` 配下が `merge=ours` 指定されているので、**fork 直後 (clone した作業ディレクトリで) 1 度だけ** merge driver を有効化します (リポジトリ単位の git config なので、別マシンで clone し直したらそのマシンでも 1 度実行):

```bash
git config --add merge.ours.driver true
```

以降、上流取り込みは:

```bash
git fetch upstream
git merge upstream/main
# content/ は merge=ours で自分のカスタムが保持される
# workflow の schedule: 行は fork 側で uncomment しているため衝突しうる、手動解決
git push origin main
```

定期的に取り込むのが推奨。長く放置すると merge が大変になります。

---

## トラブルシューティング

### `not_in_channel`

Bot をチャンネルに `/invite @yonkomatic` していない。

### `missing_scope`

Slack Scope を追加した後にワークスペースに **再インストール** していない。

### `invalid_auth`

トークンの貼り間違い (改行混入など)。

### cron が走らない

- fork 先の `.github/workflows/*.yml` の `schedule:` がコメントアウトされたままになっていないか確認
- GitHub の fork 先 → **Actions** タブで Actions が enabled になっているか確認 (fork 先は初期状態で disabled の場合あり)
- 60 日間 commit が無い fork は GitHub が cron を自動停止する (定期的に commit があれば問題なし、bot commit でカウントされる)

### batch 失敗時の挙動

§11 を参照。3 段階の自動リカバリ (sync フォールバック + 上限 2 回の再投入) が CI に組み込まれており、cron は止まりません。
