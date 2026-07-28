# Indoneshizer

全自動ファンコット(Funkot)リミックスメイカー。任意の楽曲を読み込ませると、
ボーカルを抽出し、テンポ・キーを解析した上でファンコット特有の
「ジェダグジェダグ」ビートを新規生成し、原曲ボーカルをそのビートに
乗せ替えたリミックスを自動で吐き出す。

> このディレクトリは `robolingual/Indoneshizer` リポジトリへ切り出す前の
> 仮開発場所。`robolingual.github.io` 本体とは独立したプロジェクト。

## パイプライン

```
入力曲(mp3/wav)
  → [separate]  ボーカル/伴奏の音源分離 (Demucs)
  → [analyze]   ボーカルのBPM・キー検出 (librosa)
  → [funkot]    目標BPM(既定160)のファンコットビートを新規合成
  → [mix]       ボーカルを目標BPMへタイムストレッチしてビートと合成
  → 出力: リミックスwav
```

## ディレクトリ構成

- `backend/` — Python製の変換パイプライン一式
  - `separate.py` — Demucsによるボーカル/伴奏分離
  - `analyze.py` — BPM・キー検出
  - `funkot.py` — ファンコットビート生成(キック/パーカッション/ベース)
  - `mix.py` — タイムストレッチ + ミックス
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
python pipeline.py input.mp3 --bpm 160 --out remix.wav
```

## 使い方 (サーバー)

```bash
uvicorn app:app --reload
```

`frontend/index.html` をブラウザで開き、曲をアップロードするとサーバー経由で
リミックスが生成される。

## 現状の制約

- Demucsはモデルダウンロードとそれなりの計算資源(できればGPU)を必要とする。
- ビート生成は現状シンセ波形によるプロシージャル生成で、生サンプル素材は未使用。
- キー変換(ピッチシフト)は未実装、テンポ合わせ(タイムストレッチ)のみ対応。
