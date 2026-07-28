"""ドラム+ベースのバッキングを合成し、ボーカルと合わせて書き出す(仕様書10.5, 21〜23章)。"""
import librosa
import numpy as np
import soundfile as sf

from arrangement import build_arrangement
from bass import generate_bass
from clock import ClockGrid
from drums import generate_drum_layers


def _sidechain_envelope(n_samples: int, kick_positions: list[int], sr: int,
                         depth: float = 0.6, attack_ms: float = 3, release_ms: float = 80) -> np.ndarray:
    """キック発音位置ごとにダッキングする包絡線を作る(仕様書10.5)。"""
    env = np.ones(n_samples, dtype=np.float64)
    attack_n = max(1, int(sr * attack_ms / 1000))
    release_n = max(1, int(sr * release_ms / 1000))

    dip = np.concatenate([
        np.linspace(1.0, 1.0 - depth, attack_n),
        np.linspace(1.0 - depth, 1.0, release_n),
    ])

    for pos in kick_positions:
        end = min(pos + len(dip), n_samples)
        if end <= pos:
            continue
        segment = dip[: end - pos]
        env[pos:end] = np.minimum(env[pos:end], segment)

    return env


def build_backing_track(bpm: float, duration_sec: float, sr: int = 44100, seed: int = 0):
    clock = ClockGrid(bpm, sr)
    n_bars = clock.bars_for_duration(duration_sec)

    arrangement = build_arrangement(n_bars, seed=seed)
    drums, kick_hits = generate_drum_layers(bpm, arrangement, sr=sr)
    bass, _ = generate_bass(bpm, arrangement, sr=sr)

    n = min(len(drums), len(bass))
    drums, bass = drums[:n], bass[:n]

    duck = _sidechain_envelope(n, kick_hits, sr)
    bass = (bass * duck).astype(np.float32)

    backing = drums * 0.9 + bass * 0.85
    peak = np.max(np.abs(backing)) or 1.0
    return (backing / peak * 0.95).astype(np.float32)


def build_remix(vocals_path: str, source_bpm: float, target_bpm: float, out_path: str,
                 seed: int = 0) -> str:
    y, sr = librosa.load(vocals_path, sr=None, mono=True)

    rate = target_bpm / source_bpm
    y_stretched = librosa.effects.time_stretch(y, rate=rate)

    duration_sec = len(y_stretched) / sr
    backing = build_backing_track(target_bpm, duration_sec, sr=sr, seed=seed)

    n = min(len(y_stretched), len(backing))
    mixed = y_stretched[:n] * 0.9 + backing[:n] * 0.85

    peak = np.max(np.abs(mixed)) or 1.0
    mixed = mixed / peak * 0.95

    sf.write(out_path, mixed, sr)
    return out_path
