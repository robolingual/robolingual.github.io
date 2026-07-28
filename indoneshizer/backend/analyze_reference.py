"""参照音源(ファンコット実演)から16stepの打点パターンを帯域別に抽出する。"""
import numpy as np
import librosa
from scipy.signal import butter, sosfilt

BPM = 190.0
SR = 44100

BANDS = {
    "kick":     (35, 110),
    "snare":    (180, 450),
    "cowbell":  (600, 2500),
    "hat":      (7000, 15000),
}


def band_env(y, sr, lo, hi):
    sos = butter(4, [lo, hi], btype="bandpass", fs=sr, output="sos")
    b = sosfilt(sos, y)
    env = np.abs(b)
    # 5ms smoothing
    w = int(sr * 0.005)
    env = np.convolve(env, np.ones(w) / w, mode="same")
    return env


def onset_strength_band(env, sr):
    """包絡線の正の微分＝アタック強度。"""
    d = np.diff(env, prepend=env[0])
    return np.maximum(d, 0)


def main():
    y, sr = librosa.load("funkot_ref.wav", sr=SR, mono=True)

    step_sec = 60.0 / BPM / 4.0
    bar_sec = step_sec * 16
    n_bars = int(len(y) / sr / bar_sec)

    envs = {name: onset_strength_band(band_env(y, sr, lo, hi), sr)
            for name, (lo, hi) in BANDS.items()}

    # 位相探索: キック帯域の強度が4分音符グリッドで最大になるオフセットを探す
    best_phase, best_score = 0.0, -1
    for phase in np.arange(0, step_sec * 4, 0.002):
        score = 0.0
        for bar in range(n_bars):
            for q in range(4):
                t = phase + bar * bar_sec + q * step_sec * 4
                i = int(t * sr)
                if 0 <= i < len(y):
                    score += envs["kick"][max(0, i - 300):i + 900].max()
        if score > best_score:
            best_score, best_phase = score, phase

    print(f"BPM={BPM}  bar={bar_sec:.4f}s  step={step_sec*1000:.1f}ms  bars={n_bars}")
    print(f"検出位相オフセット: {best_phase*1000:.0f} ms\n")

    # 各16stepの平均アタック強度
    results = {}
    for name, env in envs.items():
        step_vals = np.zeros(16)
        for step in range(16):
            vals = []
            for bar in range(n_bars):
                t = best_phase + bar * bar_sec + step * step_sec
                i = int(t * sr)
                win = env[max(0, i - 200):i + int(step_sec * sr * 0.7)]
                if len(win):
                    vals.append(win.max())
            step_vals[step] = np.mean(vals) if vals else 0.0
        # 正規化
        step_vals = step_vals / (step_vals.max() or 1)
        results[name] = step_vals

    header = "STEP:  " + " ".join(f"{i+1:>2}" for i in range(16))
    print(header)
    print("       " + " ".join(" 1" if i % 4 == 0 else "  " for i in range(16)) + "   <- 拍頭")
    print()
    for name, vals in results.items():
        bars_str = " ".join(f"{int(round(v*9))}" if v > 0.12 else "." for v in vals)
        bars_str = " ".join(f"{c:>2}" for c in bars_str.split(" "))
        print(f"{name:>8}: {bars_str}")

    print("\n--- 強い打点(0.45以上)をstep番号(0-index)で ---")
    for name, vals in results.items():
        strong = [i for i in range(16) if vals[i] >= 0.45]
        print(f"{name:>8}: {strong}")


if __name__ == "__main__":
    main()
