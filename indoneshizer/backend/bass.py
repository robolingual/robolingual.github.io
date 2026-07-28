"""Moog/エレキベース風のファンコットベースラインを合成する(仕様書10章)。"""
import numpy as np
from scipy.signal import butter, sosfilt

from clock import ClockGrid

# 仕様書10.3のSTEPパターン(A minor tetrad: Root/m3/P5/m7)を
# 度数インデックス(0=Root,1=m3,2=P5,3=m7)で表現。
_STEP_DEGREES = {0: 0, 2: 0, 3: 2, 5: 0, 7: 3, 8: 0, 10: 1, 11: 2, 13: 3, 14: 2}
# バリエーション用(bass_variation): 終盤の動きを変える(仕様書「Bass末尾変更」)
_STEP_DEGREES_VARIATION = {**_STEP_DEGREES, 13: 1, 14: 3, 15: 2}

_DEGREE_SEMITONES = [0, 3, 7, 10]  # Root, minor3rd, perfect5th, minor7th


def _bass_note(sr: int, freq: float, duration_sec: float, gate: float = 0.5) -> np.ndarray:
    n = int(sr * duration_sec)
    if n <= 0:
        return np.zeros(0, dtype=np.float64)
    t = np.arange(n) / sr

    saw = 2 * (t * freq - np.floor(0.5 + t * freq))
    square = np.sign(np.sin(2 * np.pi * (freq / 2) * t))
    sub = np.sin(2 * np.pi * (freq / 2) * t)
    osc = saw * 0.5 + square * 0.3 + sub * 0.3

    sos = butter(4, min(900, sr / 2 - 100), btype="lowpass", fs=sr, output="sos")
    osc = sosfilt(sos, osc)

    gate_n = max(1, int(n * gate))
    attack_n = max(1, int(gate_n * 0.08))
    decay_n = max(1, int(gate_n * 0.4))
    release_n = max(1, n - gate_n)

    env = np.zeros(n)
    env[:attack_n] = np.linspace(0, 1, attack_n)
    sustain_level = 0.35
    decay_end = min(n, attack_n + decay_n)
    env[attack_n:decay_end] = np.linspace(1, sustain_level, decay_end - attack_n)
    env[decay_end:gate_n] = sustain_level
    release_start = min(n, gate_n)
    env[release_start:] = np.linspace(sustain_level, 0, max(0, n - release_start))

    return np.tanh(osc * env * 1.6)


def generate_bass(bpm: float, arrangement: list[dict], sr: int = 44100, root_freq: float = 110.0):
    """Arrangementの bass_active/bass_variation に従いベースラインを合成する。

    戻り値は (waveform, note_onsets) — note_onsets はサイドチェイン参考用。
    """
    clock = ClockGrid(bpm, sr)
    n_bars = len(arrangement)
    total_samples = clock.bar_samples() * n_bars
    track = np.zeros(total_samples, dtype=np.float64)
    note_onsets: list[int] = []

    step_dur = clock.step_sec

    for bar_info in arrangement:
        if not bar_info["bass_active"]:
            continue
        bar = bar_info["bar"]
        degrees = _STEP_DEGREES_VARIATION if bar_info["bass_variation"] else _STEP_DEGREES

        steps = sorted(degrees.keys())
        for i, step in enumerate(steps):
            next_step = steps[i + 1] if i + 1 < len(steps) else 16
            note_len_steps = next_step - step
            duration_sec = note_len_steps * step_dur

            degree = degrees[step]
            freq = root_freq * (2 ** (_DEGREE_SEMITONES[degree] / 12))

            pos = clock.step_to_sample(bar, step)
            note = _bass_note(sr, freq, duration_sec, gate=0.55)
            end = min(pos + len(note), len(track))
            if end > pos:
                track[pos:end] += note[: end - pos]
                note_onsets.append(pos)

    peak = np.max(np.abs(track)) or 1.0
    return (track / peak * 0.9).astype(np.float32), note_onsets
