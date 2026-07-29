"""簡易コンボリューションリバーブ。

指数減衰させたノイズを擬似インパルス応答として畳み込む。
仕様書11章に「高速BPMなので残響を長くしすぎない」とあるとおり、
190BPM前後では減衰0.5〜1.0秒程度に留めないと隙間が埋まって
グルーヴが濁る。
"""
import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt


def make_ir(sr: int, decay_sec: float = 0.8, predelay_ms: float = 15.0,
            damping_hz: float = 6000.0, seed: int = 0) -> np.ndarray:
    """擬似インパルス応答を作る。"""
    rng = np.random.default_rng(seed)
    n = max(1, int(sr * decay_sec))
    tail = rng.uniform(-1.0, 1.0, n) * np.exp(-np.arange(n) / (sr * decay_sec / 5.0))

    # 高域を落として自然な減衰に寄せる
    sos = butter(2, min(damping_hz, sr / 2 - 500), btype="lowpass", fs=sr, output="sos")
    tail = sosfilt(sos, tail)

    pre = int(sr * predelay_ms / 1000.0)
    ir = np.concatenate([np.zeros(pre), tail])

    energy = np.sqrt(np.sum(ir ** 2)) or 1.0
    return ir / energy


def apply_reverb(x: np.ndarray, sr: int, wet: float = 0.12,
                 decay_sec: float = 0.8, predelay_ms: float = 15.0,
                 seed: int = 0) -> np.ndarray:
    """wet 0.0(ドライのみ) 〜 1.0(ウェットのみ)。"""
    wet = float(np.clip(wet, 0.0, 1.0))
    if wet <= 0.0:
        return x.astype(np.float32)

    dry = x.astype(np.float64)
    ir = make_ir(sr, decay_sec, predelay_ms, seed=seed)
    tail = fftconvolve(dry, ir)[: len(dry)]

    # 畳み込み後の音量はIRの長さに依存するので、ドライのRMSに合わせてから混ぜる
    dry_rms = np.sqrt(np.mean(dry ** 2)) or 1.0
    tail_rms = np.sqrt(np.mean(tail ** 2)) or 1.0
    tail *= dry_rms / tail_rms

    y = dry * (1.0 - wet) + tail * wet
    peak = np.max(np.abs(y)) or 1.0
    return (y / peak * 0.95).astype(np.float32)
