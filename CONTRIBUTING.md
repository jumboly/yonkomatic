# Contributing to yonkomatic

このリポジトリ (`jumboly/yonkomatic`) は **OSS テンプレート専用** です。実運用は fork で行い、上流リポには **テンプレ + フレームワーク本体への改善** のみ PR で戻してください。

セットアップ手順 (uv インストール / Slack Bot 作成 / Secrets 設定 / cron 有効化) は [`SETUP.md`](SETUP.md)、進捗管理と設計判断の経緯は [`ROADMAP.md`](ROADMAP.md) / [`SPEC.md`](SPEC.md) を参照してください。

---

## 1. このリポジトリの位置付けと貢献の範囲

歓迎する変更:

- フレームワーク本体のバグ修正
- パイプライン / Publisher / AI クライアントの機能追加
- ドキュメント (README / SETUP / 本ファイル) の改善

上流に戻さない変更:

- fork 先固有の運用カスタム (`content/` の差し替え / `.gitignore` 緩和 / cron schedule の有効化 / 自前の Secrets)
- 特定ワークスペース固有の Slack 設定や個人スタイルの commit

機能要望・運用相談・質問は **Discussions**、再現手順つきのバグは **Issues** へお願いします (§8 参照)。

## 2. 開発環境

- Python 3.12 以上
- [uv](https://github.com/astral-sh/uv) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

```bash
uv sync                    # 依存関係インストール
uv run yonkomatic --help   # CLI 確認
```

`.env` の準備 (OpenAI / Slack のキー) は [`SETUP.md`](SETUP.md) §4 を参照してください。

## 3. Lint

コミット前に必ず緑にしてください。

```bash
uv run ruff check src/ tests/
```

## 4. テスト

ユニットテスト (Pydantic スキーマ / 状態ストア / プロンプト構築 / RSS 取得 / 静的サイト Publisher / バッチ manifest 読み出し) は `tests/` 配下にあります。

```bash
uv run pytest
```

外部 API (OpenAI / Slack / RSS) はすべて `pytest-mock` で mock 化されているのでオフラインで完走します。

実 API を叩く手動 integration テストは以下:

```bash
uv run yonkomatic test slack       # Slack 疎通
uv run yonkomatic test panel       # シナリオ → text LLM → 画像生成
```

## 5. コーディング規約

- **コメントは WHY のみ**。WHAT は識別子で表現する (well-named identifiers)
- Step 番号やタスク参照は code に書かない (PR 説明 / `ROADMAP.md` に書く)
- CLI の終了は `raise typer.Exit(code=N)`。`sys.exit` を混ぜない
- `try/except + メッセージ + Exit` の繰り返しは `_fail_on(action)` コンテキストマネージャ (`src/yonkomatic/cli.py`) に集約する
- Publisher の障害は **例外ではなく `PublishResult(ok=False)`** で返す (1 つの障害が他の Publisher に波及しない設計)

詳細な設計原則は [`CLAUDE.md`](CLAUDE.md) の「コーディング規約 / コミット」節を参照してください。

## 6. コミットメッセージ規約

- Conventional Commits 風プレフィクスを推奨: `feat:` / `fix:` / `docs:` / `refactor:` / `chore:` / `test:`
- **`Co-Authored-By:` トレーラは付けない**。リポジトリの commit hook が捏造判定で拒否します (出典: `ROADMAP.md` Decisions Log §2026-05-08)
- 1 コミット = 1 論理変更を心がけてください (レビューしやすさ + revert しやすさのため)

## 7. PR 流儀

- `main` への直接 push は不可、必ず PR を切ってください
- PR 説明には以下を含めてください:
  - **何を**: 変更の概要
  - **なぜ**: 関連する Issue / Discussions リンク、または背景
  - **動作確認**: 手元で走らせたコマンドと結果 (`uv run yonkomatic test panel` のログなど)
- lint (`uv run ruff check src/ tests/`) と pytest (`uv run pytest`) が緑であることが前提です
- レビュアーの指名は不要、Maintainer が拾います

## 8. Issue / Discussions

- **Issue**: 再現手順つきのバグ報告に絞ります
  - 再現に必要な最小手順 / 期待動作 / 実際の動作 / 環境 (Python / uv / OS) を記載してください
- **Discussions**: 機能要望・運用相談 (fork 先での挙動など)・質問・アイデア
- Issue / PR テンプレートは置いていません (テンプレ専用リポゆえ流入は絞っています)

## 9. ライセンスと行動規範

- 本リポジトリは [MIT License](LICENSE) です。Contribution は同ライセンス下で受け入れられます
- 貢献者は相互尊重・建設的議論を心がけてください。差別的・攻撃的・嫌がらせに該当する言動は受け付けません (Contributor Covenant 相当の精神を共有します)
