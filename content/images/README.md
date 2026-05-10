# content/images/

`content/prompt.md` と一緒に画像モデルに渡される **キャラ参考画像** を置くディレクトリです。

## 同梱サンプル画像

上流テンプレ (`jumboly/yonkomatic`) には動作確認用の AI 生成リファレンス画像が同梱されています:

| ファイル | 内容 |
|---|---|
| `01-yonko-front.png` | ヨンコ (主人公) の設定資料: 正面立ち絵 + 表情 4 種 |
| `02-machika-front.png` | マチカ (相棒) の設定資料: 正面立ち絵 + 後ろ姿 + 表情 3 種 + 衣装ディテール |
| `03-hidamari-apt.png` | ひだまり荘 (舞台) の設定資料: 正面外観 + 裏手 + 玄関/ベランダ/自転車置き場 |

各画像は `../prompt.md` の `# 参考画像` セクションと alphabetical sort 順 (numeric prefix `01-` / `02-` / `03-`) で対応します。

## ライセンス

これらの画像は AI 画像生成モデルで作成されたもので、yonkomatic プロジェクトが本リポジトリ全体と同じ **MIT License** (`/LICENSE` 参照) の下で配布しています。フォーク・再配布・改変いずれも自由です。

## fork 先で自分の画像に差し替える

```bash
rm content/images/*.png
cp ~/your-art/*.png content/images/
# content/prompt.md の `# 参考画像` セクションも自分の画像の説明に書き換える
```

ファイル名は何でも構いませんが、`01-` のような numeric prefix を付けると LLM への告知時に順序が安定します (`_collect_images` は alphabetical sort)。対応する画像形式は `.png` / `.jpg` / `.jpeg` / `.webp`。サブディレクトリ自由 (再帰 glob)。
