"""ブートレグ感/古いサンプラー感を付与する(仕様書20章 Roughness)。

ファンコットは現代EDMのように整えすぎると弱くなる、と仕様書にある。
ビット深度の削減、サンプルレートの間引き、帯域制限で
「安いPCMサンプラーで鳴らした音」に寄せる。

間引きで生じるエイリアスノイズは除去せず残す(それが質感になる)。
ただし仕様書20章の但し書きどおり、低域のキックとベースだけは
濁らせすぎないよう、帯域制限は高域側だけに掛ける。
"""
import numpy as np
from scipy.signal import butter, sosfilt


def _bit_crush(x: np.ndarray, bits: int) -> np.ndarray:
    levels = 2 ** (bits - 1)
    return np.round(x * levels) / levels


def _decimate_hold(x: np.ndarray, factor: int) -> np.ndarray:
    """サンプル&ホールドで実効サンプルレートを下げる(補間しない)。"""
    if factor <= 1:
        return x
    n = len(x)
    idx = (np.arange(n) // factor) * factor
    return x[np.minimum(idx, n - 1)]


def apply_roughness(x: np.ndarray, amount: float, sr: int) -> np.ndarray:
    """amount 0.0(そのまま) 〜 1.0(最も粗い)。

    仕様書20章の Low / Mid / High に対応する連続パラメータ。
    """
    amount = float(np.clip(amount, 0.0, 1.0))
    if amount <= 0.0:
        return x.astype(np.float32)

    y = x.astype(np.float64)

    # ビット深度: 16bit -> 7bit
    bits = int(round(16 - 9 * amount))
    y = _bit_crush(y, max(4, bits))

    # 実効サンプルレート: 等倍 -> 約1/4 (44.1k なら 11k 相当)
    factor = int(round(1 + 3 * amount))
    y = _decimate_hold(y, factor)

    # 高域を削って古いサンプラーの帯域に寄せる
    cutoff = 16000 - 9000 * amount
    if cutoff < sr / 2 - 500:
        sos = butter(4, cutoff, btype="lowpass", fs=sr, output="sos")
        y = sosfilt(sos, y)

    # 軽いサチュレーション
    y = np.tanh(y * (1.0 + 0.5 * amount))

    peak = np.max(np.abs(y)) or 1.0
    return (y / peak * 0.95).astype(np.float32)
