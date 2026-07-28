"""ボーカル/原曲のBPMとキーを検出する。"""
import librosa
import numpy as np

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Schmuckler のキープロファイル
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def detect_bpm(path: str) -> float:
    y, sr = librosa.load(path, sr=None, mono=True)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    return float(tempo)


def detect_key(path: str) -> str:
    y, sr = librosa.load(path, sr=None, mono=True)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    profile = chroma.mean(axis=1)
    profile = profile / (np.linalg.norm(profile) + 1e-9)

    best_score, best_name = -np.inf, "C major"
    for shift in range(12):
        major = np.roll(_MAJOR_PROFILE, shift)
        minor = np.roll(_MINOR_PROFILE, shift)
        major = major / np.linalg.norm(major)
        minor = minor / np.linalg.norm(minor)

        major_score = float(np.dot(profile, major))
        minor_score = float(np.dot(profile, minor))

        if major_score > best_score:
            best_score, best_name = major_score, f"{_NOTE_NAMES[shift]} major"
        if minor_score > best_score:
            best_score, best_name = minor_score, f"{_NOTE_NAMES[shift]} minor"

    return best_name
