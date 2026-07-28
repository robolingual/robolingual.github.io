"""入力曲からファンコットリミックスを一気通貫で生成するCLI。

使い方:
    python pipeline.py input.mp3 --bpm 180 --out remix.wav
    python pipeline.py vocal_only.wav --no-separate --source-bpm 120 --bpm 180
"""
import argparse
import tempfile
from pathlib import Path

from analyze import detect_bpm
from mix import build_remix
from separate import separate_vocals


def run(input_path: str, target_bpm: float, out_path: str,
        source_bpm: float | None = None, do_separate: bool = True, seed: int = 0) -> str:
    with tempfile.TemporaryDirectory() as work_dir:
        if do_separate:
            print("[1/3] ボーカル分離中...")
            vocals_path, _ = separate_vocals(input_path, work_dir)
        else:
            print("[1/3] 分離スキップ(入力をボーカルとして扱う)")
            vocals_path = input_path

        if source_bpm is None:
            print("[2/3] BPM検出中...")
            source_bpm = detect_bpm(vocals_path)
        else:
            print(f"[2/3] BPM手動指定: {source_bpm}")
        print(f"  元BPM: {source_bpm:.1f} -> 目標BPM: {target_bpm}")

        print("[3/3] ファンコットビート生成 + ミックス中...")
        build_remix(vocals_path, source_bpm, target_bpm, out_path, seed=seed)

    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="全自動ファンコットリミックスメイカー")
    parser.add_argument("input", help="入力曲のパス(mp3/wav等、ボーカルのみ推奨)")
    parser.add_argument("--bpm", type=float, default=180.0, help="目標BPM(既定180)")
    parser.add_argument("--source-bpm", type=float, default=None, help="元BPMを手動指定(省略時は自動検出)")
    parser.add_argument("--no-separate", action="store_true", help="ボーカル分離をスキップし、入力をそのままボーカルとして扱う")
    parser.add_argument("--seed", type=int, default=0, help="Arrangement再現用シード")
    parser.add_argument("--out", default="remix.wav", help="出力先パス")
    args = parser.parse_args()

    out_path = run(
        args.input, args.bpm, args.out,
        source_bpm=args.source_bpm, do_separate=not args.no_separate, seed=args.seed,
    )
    print(f"完成: {Path(out_path).resolve()}")


if __name__ == "__main__":
    main()
