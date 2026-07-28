"""バス処理(仕様書22章)。ドラムを太くするためのコンプ/サチュレーション。

仕様書22章のPercussion Bus想定値:
  Ratio 2:1〜4:1 / Attack 10〜30ms / Release 30〜100ms
  Gain Reduction 1〜4dB / 軽いSaturation
"""
import numpy as np
from scipy.ndimage import maximum_filter1d
from scipy.signal import butter, lfilter, sosfilt


def _db_to_lin(db: float) -> float:
    return float(10 ** (db / 20))


def compress(x: np.ndarray, sr: int, threshold_db: float = -18.0, ratio: float = 3.0,
             attack_ms: float = 15.0, release_ms: float = 70.0,
             makeup_db: float = 0.0) -> np.ndarray:
    """フィードフォワード型のピークコンプレッサー。

    包絡線は「アタック窓での移動最大値 → リリース時定数の1次平滑」で近似する。
    サンプル単位のループだと数分の音源で現実的な速度にならないため。
    """
    thr = _db_to_lin(threshold_db)

    absx = np.abs(x)
    attack_n = max(1, int(sr * attack_ms / 1000.0))
    env = maximum_filter1d(absx, size=attack_n, mode="nearest")

    rel = float(np.exp(-1.0 / (sr * release_ms / 1000.0)))
    env = lfilter([1.0 - rel], [1.0, -rel], env)

    over = np.maximum(env, 1e-9) / thr
    gain = np.ones_like(over)
    mask = over > 1.0
    # 超過分を ratio で圧縮
    gain[mask] = over[mask] ** (1.0 / ratio - 1.0)

    return x * gain * _db_to_lin(makeup_db)


def saturate(x: np.ndarray, drive: float = 1.5) -> np.ndarray:
    """tanhによるソフトクリップ。倍音を足して音量感を稼ぐ。"""
    return np.tanh(x * drive) / np.tanh(drive)


def low_shelf(x: np.ndarray, sr: int, freq: float = 90.0, gain_db: float = 3.0) -> np.ndarray:
    """低域だけ持ち上げて重心を下げる(簡易ローシェルフ)。"""
    sos = butter(2, freq, btype="lowpass", fs=sr, output="sos")
    return x + sosfilt(sos, x) * (_db_to_lin(gain_db) - 1.0)


def fatten(x: np.ndarray, sr: int, amount: float = 0.6) -> np.ndarray:
    """パラレルコンプ + サチュレーション + 低域補強で太くする。

    amount 0.0 で素通し、1.0 で最も太い。
    アタックは潰さずに胴体だけ持ち上げたいので、
    強く潰したコピーを原音に混ぜるパラレル方式にしている。
    """
    amount = float(np.clip(amount, 0.0, 1.0))
    if amount <= 0.0:
        return x.astype(np.float32)

    dry = x.astype(np.float64)

    # 強めに潰したコピー(仕様書のGR 1〜4dBより深くかけ、混ぜる量で調整する)
    wet = compress(dry, sr, threshold_db=-24.0, ratio=6.0,
                   attack_ms=12.0, release_ms=80.0, makeup_db=6.0)
    wet = saturate(wet, drive=1.4)

    y = dry * (1.0 - 0.45 * amount) + wet * (0.65 * amount)
    y = low_shelf(y, sr, freq=90.0, gain_db=2.5 * amount)
    y = saturate(y, drive=1.0 + 0.5 * amount)

    peak = np.max(np.abs(y)) or 1.0
    return (y / peak * 0.95).astype(np.float32)
