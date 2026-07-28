"""入力曲からファンコットリミックスを一気通貫で生成するCLI。

使い方:
    python pipeline.py input.mp3 --bpm 160 --out remix.wav
"""
import argparse
import tempfile
from pathlib import Path

from analyze import detect_bpm
from mix import build_remix
from separate import separate_vocals


def run(input_path: str, target_bpm: float, out_path: str) -> str:
    with tempfile.TemporaryDirectory() as work_dir:
        print("[1/3] ボーカル分離中...")
        vocals_path, _ = separate_vocals(input_path, work_dir)

        print("[2/3] BPM検出中...")
        source_bpm = detect_bpm(vocals_path)
        print(f"  検出BPM: {source_bpm:.1f} -> 目標BPM: {target_bpm}")

        print("[3/3] ファンコットビート生成 + ミックス中...")
        build_remix(vocals_path, source_bpm, target_bpm, out_path)

    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="全自動ファンコットリミックスメイカー")
    parser.add_argument("input", help="入力曲のパス(mp3/wav等)")
    parser.add_argument("--bpm", type=float, default=160.0, help="目標BPM(既定160)")
    parser.add_argument("--out", default="remix.wav", help="出力先パス")
    args = parser.parse_args()

    out_path = run(args.input, args.bpm, args.out)
    print(f"完成: {Path(out_path).resolve()}")


if __name__ == "__main__":
    main()
