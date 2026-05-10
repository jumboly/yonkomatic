# examples/minimal/images/

このディレクトリには `examples/minimal/` で動作確認するためのリファレンス画像が含まれます。

## 含まれる画像

| ファイル | 内容 |
|---|---|
| `01-yonko-front.png` | ヨンコ (主人公) の設定資料: 正面立ち絵 + 表情 4 種 |
| `02-machika-front.png` | マチカ (相棒) の設定資料: 正面立ち絵 + 後ろ姿 + 表情 3 種 + 衣装ディテール |
| `03-hidamari-apt.png` | ひだまり荘 (舞台) の設定資料: 正面外観 + 裏手 + 玄関/ベランダ/自転車置き場 |

各画像は `prompt.md` と alphabetical sort 順 (numeric prefix `01-` / `02-` / `03-`) で対応。

## ライセンス

これらの画像は AI 画像生成モデルで作成されたもので、yonkomatic プロジェクトが本リポジトリ全体と同じ **MIT License** (`/LICENSE` 参照) の下で配布しています。フォーク・再配布・改変いずれも自由です。

## 利用者へ

`examples/minimal/` はあくまで **動作確認用のサンプル**です。本番運用 (利用者ブランチ) では、自分のオリジナルキャラ・世界観に合わせた画像に差し替えてください:

```bash
# 利用者ブランチで
rm examples/minimal/images/*.png
cp ~/your-art/*.png examples/minimal/images/
# prompt.md の `# 参考画像` セクションも自分の画像の説明に書き換える
```

ファイル名は何でも構いませんが、`01-` のような numeric prefix を付けると LLM への告知時に順序が安定します (`_collect_images` は alphabetical sort)。対応する画像形式は `.png` / `.jpg` / `.jpeg` / `.webp`。
