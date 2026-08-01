# ROBOLINGUAL

ブラウザ上で動く楽器。`index.html` 一枚で完結していて、外部依存はない。
Windows 版は `desktop/` で Tauri に包んでいる。

## バージョンの上げ方

**「Windows アプリを作って」は「版を上げて出して」の意味。** 試し焼きではない。
言われたら、版を上げてから Actions を回すこと。上げずに焼くのは間違い。

刻みは 1.0.1 → 1.0.2 と1つずつ。ただし更新材料がそこそこ溜まるまでやらない。
「もうこれ以上ないな」というタイミングで出す。無駄打ちはしない。

版を書いてある場所は6ファイル。全部揃える。

| ファイル | 箇所 |
|---|---|
| `index.html` | `<title>` と `<div class="version">` |
| `manual.html` | `<title>` / `description` / 見出しコメント / `.badge` / フッタ |
| `MANUAL_v1.0.md` | 1行目の見出し |
| `desktop/src-tauri/tauri.conf.json` | `version` |
| `desktop/package.json` | `version` |

`MANUAL_v1.0.md` はファイル名に版が入っているが、`docs/images/README.md` から
参照しているので名前は変えない。中身だけ直す。

## Windows 版のビルド

`.github/workflows/desktop.yml` を workflow_dispatch で回す。
成果物は Actions の Artifacts に `ROBOLINGUAL-windows`(msi と NSIS の exe)。
ワークスペースなので成果物は `desktop/target/` に出る。`src-tauri/target/` ではない。

回す前に `cargo test --manifest-path desktop/core/Cargo.toml` を通しておく。

## 書き方

コメントも commit メッセージも日本語。
コメントは「何をしているか」ではなく「なぜそうしたか」を書く。
数字で決めたことは、測った値を添える。
