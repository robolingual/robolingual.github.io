"""ボーカルを目標BPMへタイムストレッチし、ファンコットビートと合成する。"""
import librosa
import numpy as np
import soundfile as sf

from funkot import generate_funkot_beat


def build_remix(vocals_path: str, source_bpm: float, target_bpm: float, out_path: str) -> str:
    y, sr = librosa.load(vocals_path, sr=None, mono=True)

    rate = target_bpm / source_bpm
    y_stretched = librosa.effects.time_stretch(y, rate=rate)

    duration_sec = len(y_stretched) / sr
    beat = generate_funkot_beat(target_bpm, duration_sec, sr=sr)

    n = min(len(y_stretched), len(beat))
    mixed = y_stretched[:n] * 0.9 + beat[:n] * 0.8

    peak = np.max(np.abs(mixed)) or 1.0
    mixed = mixed / peak * 0.95

    sf.write(out_path, mixed, sr)
    return out_path
