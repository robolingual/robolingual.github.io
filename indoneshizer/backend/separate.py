"""Demucsで入力曲をボーカル/伴奏に分離する。"""
import subprocess
import sys
from pathlib import Path


def separate_vocals(input_path: str, out_dir: str, model: str = "htdemucs") -> tuple[str, str]:
    """入力曲を分離し、(vocals_path, no_vocals_path) を返す。"""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            sys.executable, "-m", "demucs",
            "--two-stems", "vocals",
            "-n", model,
            "-o", str(out_dir),
            input_path,
        ],
        check=True,
    )

    stem = Path(input_path).stem
    track_dir = out_dir / model / stem
    vocals_path = track_dir / "vocals.wav"
    no_vocals_path = track_dir / "no_vocals.wav"

    if not vocals_path.exists():
        raise FileNotFoundError(f"Demucs出力が見つからない: {vocals_path}")

    return str(vocals_path), str(no_vocals_path)
