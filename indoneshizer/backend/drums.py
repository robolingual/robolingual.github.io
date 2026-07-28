"""ファンコットの多層ドラムを合成する(仕様書 5〜9章)。

生サンプル素材は使わず、全パートをプロシージャル合成する。
Amen/ブレイクビーツ(9章)はサンプル素材前提のためMVPでは未実装
(仮定として明記: 将来サンプル素材が用意でき次第対応)。
"""
import numpy as np
from scipy.signal import butter, sosfilt

from clock import ClockGrid

# 各8小節ブロック内でのバー番号(0-indexed, 8で割った余り)ごとに
# 新規追加されるレイヤー。前のバーまでの追加は積み上げる(累積)。
# 仕様書17.1 BAR1-8テンプレートに対応。
_BAR_TEMPLATE_ADDITIONS = {
    0: {"main_kick", "short_kick", "snare", "hat_closed"},
    1: {"cowbell"},
    2: {"woodblock"},
    3: {"tom"},
    4: set(),   # bassはArrangementGenerator側で管理
    5: set(),
    6: set(),   # 本来Voice追加(仕様書 BAR7)だが声ネタ素材未対応のため何もしない
    7: set(),
}
_FILL_BAR = {3: "tom", 7: "snare_roll"}


def _env(n: int, decay: float) -> np.ndarray:
    t = np.arange(n)
    return np.exp(-t / (decay * n))


def _sine_sweep(sr: int, n: int, f_start: float, f_end: float, tau: float) -> np.ndarray:
    t = np.arange(n) / sr
    freq = f_end + (f_start - f_end) * np.exp(-t / tau)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    return np.sin(phase)


def _main_kick(sr: int) -> np.ndarray:
    n = int(sr * 0.16)
    body = _sine_sweep(sr, n, 300, 55, 0.03) * _env(n, 0.14)
    click = np.random.uniform(-1, 1, n) * _env(n, 0.008)
    return np.tanh((body * 1.3 + click * 0.4) * 1.4)


def _short_kick(sr: int) -> np.ndarray:
    n = int(sr * 0.08)
    body = _sine_sweep(sr, n, 220, 90, 0.015) * _env(n, 0.09)
    sos = butter(2, 60, btype="highpass", fs=sr, output="sos")
    body = sosfilt(sos, body)
    return np.tanh(body * 1.2)


def _snare(sr: int, pitch_semi: float = 0.0, decay: float = 0.11) -> np.ndarray:
    n = int(sr * 0.15)
    tone = _sine_sweep(sr, n, 190 * (2 ** (pitch_semi / 12)), 140, 0.02) * _env(n, decay * 0.6)
    noise = np.random.uniform(-1, 1, n)
    sos = butter(4, [800, 6000], btype="bandpass", fs=sr, output="sos")
    noise = sosfilt(sos, noise) * _env(n, decay)
    return np.tanh(tone * 0.6 + noise * 0.9)


def _hat(sr: int, open_hat: bool = False) -> np.ndarray:
    n = int(sr * (0.28 if open_hat else 0.05))
    noise = np.random.uniform(-1, 1, n)
    sos = butter(4, 7500, btype="highpass", fs=sr, output="sos")
    return sosfilt(sos, noise) * _env(n, 0.3 if open_hat else 0.05)


def _cowbell(sr: int, pitch_semi: float) -> np.ndarray:
    n = int(sr * 0.12)
    f0 = 540 * (2 ** (pitch_semi / 12))
    t = np.arange(n) / sr
    tone = np.sign(np.sin(2 * np.pi * f0 * t)) * 0.5 + np.sin(2 * np.pi * f0 * 1.48 * t) * 0.5
    return np.tanh(tone * _env(n, 0.1) * 1.1)


def _woodblock(sr: int, pitch_semi: float = 0.0) -> np.ndarray:
    n = int(sr * 0.05)
    f0 = 900 * (2 ** (pitch_semi / 12))
    t = np.arange(n) / sr
    tone = np.sin(2 * np.pi * f0 * t)
    return tone * _env(n, 0.03)


def _tom(sr: int, pitch_semi: float = 0.0) -> np.ndarray:
    n = int(sr * 0.18)
    body = _sine_sweep(sr, n, 220 * (2 ** (pitch_semi / 12)), 110 * (2 ** (pitch_semi / 12)), 0.05)
    return body * _env(n, 0.15)


_SHORT_KICK_STEPS = {2, 6, 7, 10, 14, 15}
_WOODBLOCK_STEPS = {1, 3, 5, 9, 11, 13, 15}
_COWBELL_STEPS = {2, 5, 7, 10, 13, 14}
_TOM_STEPS = {2, 6, 7, 10, 13, 14}
_HAT_CLOSED_STEPS = {0, 2, 4, 6, 8, 10, 12, 14}
_HAT_OPEN_STEPS = {2, 6, 10, 14}
_SNARE_STEPS = {4, 12}
_MAIN_KICK_STEPS = {0, 4, 8, 12}

_COWBELL_PITCHES = [7, 0, -5]  # High / Mid / Low (semitone)


def _mix_at(track: np.ndarray, sound: np.ndarray, pos: int, gain: float = 1.0) -> None:
    end = min(pos + len(sound), len(track))
    if end <= pos:
        return
    track[pos:end] += sound[: end - pos] * gain


def _snare_roll(sr: int, bpm: float) -> np.ndarray:
    """仕様書7章: 1小節ビルド(8分->16分->16分->32分), ピッチ/ベロシティ上昇。"""
    beat_sec = 60.0 / bpm
    n_samples = int(beat_sec * 4 * sr)
    track = np.zeros(n_samples, dtype=np.float64)

    subdivisions = [2, 4, 4, 8]  # 拍ごとの打数(8分, 16分, 16分, 32分)
    total_hits = sum(subdivisions)
    hit_index = 0

    for beat, n_hits in enumerate(subdivisions):
        for i in range(n_hits):
            # 最後の拍(32分)の最終ヒットは無音にする(仕様書: 最後の1/4拍を無音)
            if beat == 3 and i == n_hits - 1:
                hit_index += 1
                continue
            t = beat * beat_sec + i * (beat_sec / n_hits)
            pos = int(t * sr)
            progress = hit_index / max(1, total_hits - 1)
            pitch = progress * 7  # 0 -> +7 semitone
            velocity = 0.35 + 0.65 * progress
            _mix_at(track, _snare(sr, pitch_semi=pitch, decay=0.08), pos, gain=velocity)
            hit_index += 1

    return track


def generate_drum_layers(bpm: float, arrangement, sr: int = 44100) -> np.ndarray:
    """ArrangementGenerator の出力(バーごとの有効レイヤー)に従いドラムを合成する。"""
    clock = ClockGrid(bpm, sr)
    n_bars = len(arrangement)
    total_samples = clock.bar_samples() * n_bars
    track = np.zeros(total_samples, dtype=np.float64)

    kick_hits: list[int] = []  # サイドチェイン用にキック発音位置を記録

    for bar_info in arrangement:
        bar = bar_info["bar"]
        layers = bar_info["layers"]
        fill = bar_info.get("fill")

        if fill == "snare_roll":
            pos = clock.step_to_sample(bar, 0)
            roll = _snare_roll(sr, bpm)
            _mix_at(track, roll, pos)
            continue  # このバーは通常パターンを上書き

        for step in range(16):
            pos = clock.step_to_sample(bar, step)

            if "main_kick" in layers and step in _MAIN_KICK_STEPS:
                _mix_at(track, _main_kick(sr), pos)
                kick_hits.append(pos)
            if "short_kick" in layers and step in _SHORT_KICK_STEPS:
                velocity = 0.85 if step in (6, 14) else 0.6
                _mix_at(track, _short_kick(sr), pos, gain=velocity)
            if "snare" in layers and step in _SNARE_STEPS:
                _mix_at(track, _snare(sr), pos)
            if "hat_closed" in layers and step in _HAT_CLOSED_STEPS:
                _mix_at(track, _hat(sr), pos, gain=0.5)
            if "hat_open" in layers and step in _HAT_OPEN_STEPS:
                _mix_at(track, _hat(sr, open_hat=True), pos, gain=0.4)
            if "cowbell" in layers and step in _COWBELL_STEPS:
                pitch = _COWBELL_PITCHES[step % len(_COWBELL_PITCHES)]
                _mix_at(track, _cowbell(sr, pitch), pos, gain=0.8)
            if "woodblock" in layers and step in _WOODBLOCK_STEPS:
                _mix_at(track, _woodblock(sr), pos, gain=0.6)
            if "tom" in layers and step in _TOM_STEPS:
                pitch = -4 if step in (13, 14) else 0
                _mix_at(track, _tom(sr, pitch), pos, gain=0.75)

    peak = np.max(np.abs(track)) or 1.0
    return (track / peak * 0.9).astype(np.float32), kick_hits
