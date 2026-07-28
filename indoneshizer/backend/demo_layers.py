"""レイヤーを一段ずつ積んだデモを書き出す(耳で確認しながら詰めるため)。

使い方:
    python demo_layers.py --bpm 190 --bars 4 --out-dir ./demo
"""
import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

from drums import generate_drum_layers

# 積み上げていく順序。各段でそれまでのレイヤーを全部含む。
_STAGES = [
    ("01_kick",        ["main_kick"]),
    ("02_snare",       ["main_kick", "snare"]),
    ("03_hat",         ["main_kick", "snare", "hat_closed"]),
    ("04_cowbell",     ["main_kick", "snare", "hat_closed", "cowbell"]),
    ("05_woodblock",   ["main_kick", "snare", "hat_closed", "cowbell", "woodblock"]),
    ("06_shaker",      ["main_kick", "snare", "hat_closed", "cowbell", "woodblock", "hat_ghost"]),
    ("07_shortkick",   ["main_kick", "snare", "hat_closed", "cowbell", "woodblock",
                        "hat_ghost", "short_kick"]),
    ("08_full",        ["main_kick", "snare", "hat_closed", "cowbell", "woodblock",
                        "hat_ghost", "short_kick", "hat_open", "tom"]),
]


def render(layers: list[str], bpm: float, n_bars: int, sr: int) -> np.ndarray:
    arrangement = [
        {"bar": b, "layers": set(layers), "fill": None,
         "bass_active": False, "bass_variation": False}
        for b in range(n_bars)
    ]
    audio, _ = generate_drum_layers(bpm, arrangement, sr=sr)
    return audio


def main() -> None:
    parser = argparse.ArgumentParser(description="レイヤー積み上げデモの書き出し")
    parser.add_argument("--bpm", type=float, default=190.0)
    parser.add_argument("--bars", type=int, default=4)
    parser.add_argument("--sr", type=int, default=44100)
    parser.add_argument("--out-dir", default="./demo")
    parser.add_argument("--only", default=None, help="特定の段だけ書き出す(例: 04_cowbell)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for name, layers in _STAGES:
        if args.only and args.only not in name:
            continue
        audio = render(layers, args.bpm, args.bars, args.sr)
        path = out_dir / f"{name}.wav"
        sf.write(path, audio, args.sr)
        print(f"{path}  ({len(audio)/args.sr:.1f}s, layers={len(layers)})")


if __name__ == "__main__":
    main()
