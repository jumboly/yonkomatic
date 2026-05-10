# SETUP

Step 1 (Slack 疎通確認) までのセットアップ手順です。Step 2 以降で必要になる Anthropic / Google AI Studio のキーは、このフェーズではまだ不要です。

## 1. ローカル環境の準備

### 必要なもの

- Python 3.12 以上
- [uv](https://github.com/astral-sh/uv) (推奨インストール: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### セットアップ

```bash
git clone <YOUR_FORK_URL> yonkomatic
cd yonkomatic
uv sync
```

`uv run yonkomatic --help` が表示されれば OK。

## 2. Slack Bot を作成する

1. <https://api.slack.com/apps> から **Create New App** → **From scratch**
2. App 名 (例: `yonkomatic`) と投稿先ワークスペースを選択
3. 左メニューの **OAuth & Permissions** → *Scopes* セクションで **Bot Token Scopes** に以下を追加:
   - `chat:write`
   - `files:write`
   - `channels:read`
4. 同ページ上部の **Install to Workspace** → 承認
5. インストール後に表示される **Bot User OAuth Token** (`xoxb-...`) を控える
6. 投稿先チャンネルで `/invite @yonkomatic` (Bot 名) してチャンネルに参加させる
7. Slack デスクトップアプリでチャンネル名を右クリック → *Copy link* で URL の末尾の英数字 (`Cxxxxx`) がチャンネル ID

## 3. ローカルで動作確認する

```bash
cp .env.example .env
# .env を編集
#   SLACK_BOT_TOKEN=xoxb-...
#   SLACK_CHANNEL_ID=Cxxxxxxxxxx

uv run yonkomatic test slack
```

成功すると Slack の指定チャンネルにテスト用 4 コマ風画像が投稿され、permalink が標準出力されます。

失敗時の代表的な原因:

- `not_in_channel`: Bot をチャンネルに `/invite` していない
- `missing_scope`: Scope を追加した後、ワークスペースに **再インストール** していない
- `invalid_auth`: トークンの貼り間違い (改行混入など)

## 4. GitHub Actions で動作確認する

1. リポジトリを GitHub に push
2. **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
   - `SLACK_BOT_TOKEN` = 上で取得した Bot Token
   - `SLACK_CHANNEL_ID` = チャンネル ID
3. **Actions** タブ → `test-slack` → **Run workflow**
4. ジョブが緑になり、Slack に投稿されれば Step 1 完了

## 次のステップ

シナリオ生成 + 画像生成を動かすには以下のキーが必要になります:

- `OPENAI_API_KEY` (<https://platform.openai.com/api-keys>) — テキスト (gpt-5.4) と画像 (gpt-image-1) の両方で使用
