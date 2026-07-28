# Indoneshizer

全自動ファンコット(Funkot)リミックスメイカー。任意の楽曲を読み込ませると、
ボーカルを抽出し、テンポ・キーを解析した上でファンコット特有の
「ジェダグジェダグ」ビートを新規生成し、原曲ボーカルをそのビートに
乗せ替えたリミックスを自動で吐き出す。

> このディレクトリは `robolingual/Indoneshizer` リポジトリへ切り出す前の
> 仮開発場所。`robolingual.github.io` 本体とは独立したプロジェクト。

個人PC専用のローカル実行を前提とする(GitHub Pages公開やiPhone Safari対応は考慮しない)。
`docs/FUNKOT_REMIX_APP_CLAUDE_SPEC.md` の仕様書に沿って設計している。

## パイプライン

```
入力曲(mp3/wav、ボーカルのみ推奨)
  → [separate]    ボーカル/伴奏の音源分離 (Demucs, --no-separateでスキップ可)
  → [analyze]     BPM検出 (librosa。手動指定も可)
  → [arrangement] 8小節単位のArrangementを構築 (Seed指定で再現可能)
  → [drums]       多層ファンコットドラムを合成
                   (Main/Short Kick, Snare, Hat, Cowbell, Woodblock, Tom, Snare Roll)
  → [bass]        Moog/エレキベース風ベースラインを合成 (キックでサイドチェイン)
  → [mix]         ボーカルを目標BPM(既定180)へタイムストレッチしてバッキングと合成
  → 出力: リミックスwav
```

## リズムの記法

打点は `backend/patterns.py` に置いてあり、**ステップ番号は1〜16の1始まり**
(DAWのステップシーケンサー表示に合わせている)。
1小節=4拍、1拍=4step、半拍(8分)=2step。

```
拍:      1           2           3           4
step:    1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
kick:    K  .  .  .  k  .  k  .  .  .  k  .  K  .  .  .
snare:   .  .  .  .  S  .  .  .  .  .  .  .  S  .  .  .
hat:     .  h  .  h  .  h  .  h  .  h  .  h  .  h  .  h
cowbell: .  .  .  .  カ .  コ .  .  .  .  .  カ .  コ  .
```

カナ表記で指示する場合は**カナ1文字＝半拍**。「ン」は余韻であって新しい打点
ではなく、「休」は休符。上のキックは「ドン」「ドド」「休ド」「ドン」、
カウベルは「休」「カコ」「休」「カコ」にあたる。

キックの打点は参照音源(190BPMのファンコット実演)の帯域別オンセット解析とも
整合する。解析では step1/7/11 が強く出て step5/13 は弱かったが、これは
スネアと重なって埋もれていたためで、打点自体は存在する。
`backend/analyze_reference.py` で同じ解析を再実行できる。

## ディレクトリ構成

- `backend/` — Python製の変換パイプライン一式
  - `separate.py` — Demucsによるボーカル/伴奏分離
  - `analyze.py` — BPM・キー検出
  - `clock.py` — BPMベースの16分刻みグリッド管理
  - `drums.py` — 多層ドラム合成(仕様書5〜9章)
  - `bass.py` — ベースライン合成(仕様書10章)
  - `arrangement.py` — 8小節Arrangement構築(仕様書17, 19章)
  - `mix.py` — サイドチェイン付きバッキング生成 + タイムストレッチ + ミックス
  - `pipeline.py` — 上記を通しで実行するCLIエントリポイント
  - `app.py` — アップロード→リミックスをHTTPで受け付けるFastAPIサーバー
- `frontend/` — アップロード用の簡易UI(静的HTML)

## セットアップ

```bash
cd indoneshizer/backend
pip install -r requirements.txt
```

## 使い方 (CLI)

```bash
python pipeline.py input.mp3 --bpm 180 --out remix.wav
# ボーカル単体音源で、分離をスキップしBPMも手動指定する場合
python pipeline.py vocal.wav --no-separate --source-bpm 120 --bpm 180 --seed 42
```

## 使い方 (サーバー)

```bash
uvicorn app:app --reload
```

`frontend/index.html` をブラウザで開き、曲をアップロードするとサーバー経由で
リミックスが生成される。

## 現状の制約・未実装(仕様書で明記された仮定)

- Demucsはモデルダウンロードとそれなりの計算資源(できればGPU)を必要とする。
- 全パートをシンセ波形でプロシージャル合成しており、生サンプル素材(仕様書24章)は未使用。
- Amen/ブレイクビーツ(9章)、Vocal Chop(15章)、DJボイス(16章)、Downbeat(18章)、
  Roughness(20章)は未実装。BAR9-16の"Full Drop"テンプレートも未実装で、
  全ブロックをBAR1-8の「ビルド」テンプレートとして繰り返している。
- キー自動検出は実装済みだが、ベースの調はA minor tetrad固定(Key連動は未実装)。
- ピッチ変換は未実装、テンポ合わせ(タイムストレッチ)のみ対応。
