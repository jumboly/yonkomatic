# content/

このディレクトリは **利用者の素材置き場** です。`main` ブランチでは空 (`.gitkeep` のみ) で、利用者が自分のブランチで以下を配置します。

```
content/
├── characters/
│   ├── settings.md             # キャラクター設定書
│   └── refs/{character_name}/{*.png}  # 参照画像 3〜5 枚 (Step 2 以降で使用)
├── world/
│   └── settings.md             # 世界観設定書
├── samples/
│   ├── STYLE.md                # 画風・トーンの基準
│   └── episodes/sample-*.png   # 過去の良作サンプル (任意)
└── themes/
    └── 2026-05.md              # 月別テーマ (任意)
```

すぐ動かしたい場合は `examples/minimal/` をそのままコピーして使い始められます。

```bash
cp -R examples/minimal/* content/
```

`main` の更新を取り込むときは、`content/` 配下に main 側ファイルが無いため衝突しません。
