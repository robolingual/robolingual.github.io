"""生成結果を自己検証する。

耳で指摘される前に機械で気づくための仕組み。過去に起きた不具合:

  - ハットの実質長が2.24msしかなく、ハイハットではなく
    高域だけのクリック音になっていた
  - ハットを16分裏(偶数step)に置いてしまい、表拍とも8分裏とも
    一致しない位置で鳴っていた

どちらも「鳴らして測る」だけで検出できたもの。音を書き出す前にここを通す。

使い方:
    python verify.py
"""
import sys

import numpy as np
from scipy.signal import butter, find_peaks, sosfilt

import drums
import patterns
from arrangement import build_arrangement
from clock import ClockGrid

SR = 44100

# 各音色の妥当な長さ(-20dBまで、ms)。範囲外なら設計ミスを疑う。
_DURATION_LIMITS = {
    "main_kick": (60.0, 250.0),
    "short_kick": (20.0, 120.0),
    "snare": (40.0, 250.0),
    "hat_closed": (15.0, 120.0),
    "hat_open": (60.0, 400.0),
    "cowbell": (30.0, 250.0),
    "woodblock": (10.0, 100.0),
    "tom": (50.0, 300.0),
}

# 拍との関係。1始まりの16step。
BEAT_STEPS = (1, 5, 9, 13)          # 表拍
EIGHTH_OFFBEAT_STEPS = (3, 7, 11, 15)   # 8分裏
SIXTEENTH_OFFBEAT_STEPS = tuple(range(2, 17, 2))  # 16分裏


def _effective_ms(x: np.ndarray, sr: int = SR) -> float:
    """ピークから-20dBまで落ちるまでの長さ(ms)。"""
    env = np.abs(x)
    peak = env.max()
    if peak <= 0:
        return 0.0
    idx = np.where(env > peak * 0.1)[0]
    return float((idx[-1] - idx[0]) / sr * 1000)


def check_voice_durations() -> list[str]:
    problems = []
    voices = {
        "main_kick": drums._main_kick(SR),
        "short_kick": drums._short_kick(SR),
        "snare": drums._snare(SR),
        "hat_closed": drums._hat(SR),
        "hat_open": drums._hat(SR, open_hat=True),
        "cowbell": drums._cowbell(SR, 0),
        "woodblock": drums._woodblock(SR),
        "tom": drums._tom(SR),
    }
    print("--- 音色の長さ(-20dBまで) ---")
    for name, wave in voices.items():
        ms = _effective_ms(wave)
        lo, hi = _DURATION_LIMITS[name]
        ok = lo <= ms <= hi
        print(f"  {name:11}: {ms:6.1f} ms   期待 {lo:.0f}〜{hi:.0f}   {'OK' if ok else '*** 範囲外 ***'}")
        if not ok:
            problems.append(
                f"{name} の長さ {ms:.1f}ms が想定範囲 {lo:.0f}〜{hi:.0f}ms から外れている"
            )
    return problems


def describe_placement(steps) -> str:
    """打点が拍のどこに乗っているかを言葉で返す。"""
    s = set(steps)
    if s and s <= set(BEAT_STEPS):
        return "表拍"
    if s and s <= set(EIGHTH_OFFBEAT_STEPS):
        return "8分裏"
    if s and s <= set(SIXTEENTH_OFFBEAT_STEPS):
        return "16分裏(表拍とも8分裏とも一致しない)"
    if s <= set(BEAT_STEPS) | set(EIGHTH_OFFBEAT_STEPS):
        return "8分(表拍+8分裏)"
    return "混在"


def check_pattern_placement() -> list[str]:
    problems = []
    print("\n--- 打点の位置 ---")
    named = {
        "main_kick": patterns.MAIN_KICK,
        "short_kick": patterns.SHORT_KICK,
        "snare": patterns.SNARE,
        "hat_closed": patterns.HAT_CLOSED,
        "cowbell": patterns.COWBELL,
    }
    for name, pat in named.items():
        if not pat:
            continue
        steps = sorted(pat)
        print(f"  {name:11}: step {steps}  -> {describe_placement(steps)}")

    hat = sorted(patterns.HAT_CLOSED)
    if hat and set(hat) <= set(SIXTEENTH_OFFBEAT_STEPS):
        problems.append(
            "hat_closed が16分裏だけに乗っている。"
            "表拍(1,5,9,13)とも8分裏(3,7,11,15)とも重ならず、拍が掴めない鳴り方になる"
        )
    return problems


def check_rendered_hits(bpm: float = 190.0) -> list[str]:
    """実際にレンダリングした波形から打点を拾い、宣言と一致するか確かめる。"""
    problems = []
    print("\n--- レンダリング結果の実測 ---")

    arr = [{"bar": b, "layers": {"main_kick"}, "fill": None, "break": None,
            "bass_active": False, "bass_variation": False} for b in range(4)]
    stems, _ = drums.generate_drum_stems(bpm, arr, sr=SR)
    audio = stems.get("main_kick")
    if audio is None:
        return ["main_kick のステムが生成されなかった"]

    clock = ClockGrid(bpm, SR)
    sos = butter(4, [30, 200], btype="bandpass", fs=SR, output="sos")
    env = np.abs(sosfilt(sos, audio))
    w = int(SR * 0.004)
    env = np.convolve(env, np.ones(w) / w, mode="same")
    d = np.maximum(np.diff(env, prepend=env[0]), 0)
    pk, _ = find_peaks(d, height=d.max() * 0.3, distance=int(SR * 0.06))

    # 低域のリンギングで1発が複数回検出されるため、同一step内は1つに畳む
    detected = sorted({int(round((p / SR / clock.step_sec) % 16)) % 16 + 1 for p in pk})
    expected = sorted(patterns.MAIN_KICK)
    print(f"  main_kick 宣言: {expected}")
    print(f"  main_kick 実測: {detected}")
    missing = set(expected) - set(detected)
    if missing:
        problems.append(f"main_kick の宣言 {sorted(missing)} が実測で見つからない")
    return problems


def main() -> int:
    problems = []
    problems += check_voice_durations()
    problems += check_pattern_placement()
    problems += check_rendered_hits()

    print()
    if problems:
        print(f"*** {len(problems)}件の問題 ***")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("問題なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
