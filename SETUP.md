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

## 1. fork する

GitHub の標準 fork は public になります。**Slack 投稿アーカイブを含むので private 化を推奨**します。

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

cron が `state/`, `output/archive/`, `docs/` などに自動 commit + push するため、Actions に書き込み権限を与えます。

GitHub UI: 自分の fork → **Settings** → **Actions** → **General** → **Workflow permissions**:

- ☑️ **Read and write permissions** を選択
- **Allow GitHub Actions to create and approve pull requests** はチェック不要

## 7. .gitignore を緩和

上流の `.gitignore` は cron 生成物を ignore しています (テンプレ側に運用データを混ぜないため)。fork 先では履歴に残したいので緩和します:

```diff
# .gitignore
- /scenarios/
- /state/
- /output/
- /docs/*
+ # /scenarios/    # fork: track scenarios for archival
+ # /state/        # fork: track state across cron runs
+ # /output/       # fork: keep generated archives
+ # /docs/*        # fork: GitHub Pages source
```

代わりに `output/preflight/` だけは中間生成物なので、必要に応じて部分 ignore してもよい (好み)。

## 8. cron schedule を有効化

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

## 9. 自前のキャラ素材を持ち込む

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

## 10. GitHub Actions で動作確認

`workflow_dispatch` で 1 回手動実行して動くか確認します。

```bash
# 翌週分のシナリオ生成 + 画像 batch 投入
gh workflow run weekly-scenarios.yml -R <YOUR_USER>/yonkomatic-mine

# 1 日後 (batch 完走後) に daily publish を試す
gh workflow run daily-publish.yml -R <YOUR_USER>/yonkomatic-mine
```

GitHub UI の **Actions** タブで実行ログを確認、Slack に投稿されれば成功。

成功したら cron に任せて毎日の自動投稿が回ります。

## 11. 上流から更新を取り込む

上流テンプレに改善が入ったら fork 先に取り込みます。リポジトリルートの `.gitattributes` で `content/` 配下が `merge=ours` 指定されているので、まず一度だけ merge driver を有効化:

```bash
git config --add merge.ours.driver true
```

以降、上流取り込みは:

```bash
git fetch upstream
git merge upstream/main
# content/ は merge=ours で自分のカスタムが保持される
# .gitignore や workflow の schedule などは衝突しうるので手動解決
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

### batch 失敗時のフォールバック

batch 画像生成が 24h 以内に完走しなかった場合、`daily-publish.yml` は preflight 不在を検出して sync で生成にフォールバックします (cron は止まりません)。完全自動リトライは [Step 6.7](ROADMAP.md) で実装予定。
