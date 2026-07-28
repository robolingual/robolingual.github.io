"""ファンコット(Funkot)特有のビートをプロシージャルに合成する。

サンプル素材は使わず、キック/ハイハット/クラップを波形合成し、
定番の「ジェダグジェダグ」パターン(4つ打ちキック+裏打ちの二連キック)で
指定BPM・指定尺のバッキングトラックを生成する。
"""
import numpy as np
from scipy.signal import butter, sosfilt


def _envelope(n: int, decay: float) -> np.ndarray:
    t = np.arange(n)
    return np.exp(-t / (decay * n))


def _kick(sr: int, dur: float = 0.22) -> np.ndarray:
    n = int(sr * dur)
    t = np.arange(n) / sr
    freq = 150 * np.exp(-t / 0.05) + 45  # 150Hz -> 45Hz へピッチ降下
    phase = 2 * np.pi * np.cumsum(freq) / sr
    body = np.sin(phase) * _envelope(n, 0.18)
    click = np.random.uniform(-1, 1, n) * _envelope(n, 0.01)
    return np.tanh((body * 1.4 + click * 0.3) * 1.5)


def _hihat(sr: int, dur: float = 0.06, open_hat: bool = False) -> np.ndarray:
    n = int(sr * dur * (4 if open_hat else 1))
    noise = np.random.uniform(-1, 1, n)
    sos = butter(4, 7000, btype="highpass", fs=sr, output="sos")
    filtered = sosfilt(sos, noise)
    return filtered * _envelope(n, 0.25 if open_hat else 0.06)


def _clap(sr: int, dur: float = 0.15) -> np.ndarray:
    n = int(sr * dur)
    noise = np.random.uniform(-1, 1, n)
    sos = butter(4, [1200, 6000], btype="bandpass", fs=sr, output="sos")
    filtered = sosfilt(sos, noise)
    return filtered * _envelope(n, 0.12)


def _mix_at(track: np.ndarray, sound: np.ndarray, sample_pos: int) -> None:
    end = min(sample_pos + len(sound), len(track))
    if end <= sample_pos:
        return
    track[sample_pos:end] += sound[: end - sample_pos]


def generate_funkot_beat(bpm: float, duration_sec: float, sr: int = 44100) -> np.ndarray:
    """指定BPM・尺のファンコットバッキングトラック(モノラル)を生成する。"""
    n_samples = int(duration_sec * sr)
    track = np.zeros(n_samples, dtype=np.float64)

    sixteenth = 60.0 / bpm / 4.0
    n_steps = int(duration_sec / sixteenth) + 1

    kick = _kick(sr)
    hihat_closed = _hihat(sr, open_hat=False)
    hihat_open = _hihat(sr, open_hat=True)
    clap = _clap(sr)

    for step in range(n_steps):
        pos = int(step * sixteenth * sr)
        beat_in_bar = step % 16  # 4/4拍子、16分刻み

        # 4つ打ち + 裏の二連キック(ジェダグジェダグ)
        if beat_in_bar % 4 == 0:
            _mix_at(track, kick, pos)
        if beat_in_bar % 8 == 6:
            _mix_at(track, kick, pos)

        # ハイハット: 8分裏でクローズ、4小節ごとの最後にオープン
        if beat_in_bar % 2 == 1:
            _mix_at(track, hihat_closed, pos)
        if beat_in_bar == 14:
            _mix_at(track, hihat_open, pos)

        # クラップ: 2拍目・4拍目
        if beat_in_bar in (4, 12):
            _mix_at(track, clap, pos)

    peak = np.max(np.abs(track)) or 1.0
    return (track / peak * 0.9).astype(np.float32)
