# content/

このディレクトリは **作品素材置き場** です。fork 先で自分のキャラクター・世界観・参考画像に書き換えて使います。

```
content/
├── prompt.md             # キャラクター / 世界観 / 画風を 1 ファイルにまとめる
├── images/               # キャラ参考画像 (画像モデルに渡される)
│   ├── 01-*.png          # numeric prefix で順序を制御 (alphabetical sort)
│   ├── 02-*.png
│   └── README.md         # 各画像の意味を説明
└── sample-scenario.yaml  # `test panel` 等の検証用シナリオ (任意)
```

上流テンプレ (`jumboly/yonkomatic`) には**動作確認用のサンプル素材**が同梱されています。そのまま `uv run yonkomatic test panel` で動きます。fork 先では自分の作品に置き換えてください。

## カスタマイズ手順

1. `content/prompt.md` を自分のキャラ・世界観・画風で書き直す
2. `content/images/*.png` を自分の参考画像に差し替える (PNG/JPEG/WebP 可、サブディレクトリ自由)
3. `content/sample-scenario.yaml` は削除 or 上書き OK (検証用なので必須ではない)

`prompt.md` の `# 参考画像` セクションには `Image 1 (01-yonko-front.png): ヨンコの正面立ち絵...` のように各画像の意味を書きます。LLM はファイル名 alphabetical sort で受け取るので、`01-` などの numeric prefix を付けると順序が安定します。

## プロンプトテンプレ自体のカスタマイズ (上級者)

`content/scenario_prompt.md` / `content/panel_prompt.md` をここに置けば組み込みデフォルト (`src/yonkomatic/templates/`) を上書きできます (フォールバック方式)。

## 上流からの更新を取り込むときの衝突回避

リポジトリルートの `.gitattributes` に `content/* merge=ours` を設定すると、上流テンプレの `content/` 更新が fork 先で衝突せず自分のカスタムが保持されます。
