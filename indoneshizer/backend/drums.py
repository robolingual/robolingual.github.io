"""ファンコットの多層ドラムを合成する(仕様書5〜9章)。

打点定義は patterns.py 側に分離してある(耳で詰めながら差し替えるため)。
生サンプル素材は使わず、全パートを波形合成する。
Amen/ブレイクビーツ(9章)はサンプル素材前提のためMVPでは未実装。
"""
import numpy as np
from scipy.signal import butter, sosfilt

import patterns
import tone
from clock import ClockGrid

# 有効化できるレイヤー名。ArrangementGeneratorが小節ごとに部分集合を渡す。
ALL_LAYERS = frozenset({
    "main_kick", "short_kick", "snare",
    "hat_closed", "hat_ghost", "hat_open",
    "cowbell", "woodblock", "tom",
})


def _env(n: int, decay: float) -> np.ndarray:
    t = np.arange(n)
    return np.exp(-t / (decay * n))


def _sine_sweep(sr: int, n: int, f_start: float, f_end: float, tau: float) -> np.ndarray:
    t = np.arange(n) / sr
    freq = f_end + (f_start - f_end) * np.exp(-t / tau)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    return np.sin(phase)


def _main_kick(sr: int, pitch_semi: float = 0.0) -> np.ndarray:
    """短く硬いキック(仕様書6章: Decay 80〜160ms, 基音50〜70Hz, クリック有り)。

    pitch_semi を上げると音程が上がる。高くなるほど尾も短くする
    (ビルドで詰めて撃つとき、長い尾が残ると団子になるため)。
    """
    f = 2 ** (pitch_semi / 12)
    n = int(sr * 0.15 / (1 + pitch_semi / 24))
    body = _sine_sweep(sr, n, 320 * f, 58 * f, 0.028) * _env(n, 0.13)
    click = np.random.uniform(-1, 1, n) * _env(n, 0.006)
    return tone.saturate(body * 1.35 + click * 0.35, tone.DRIVE["main_kick"])


def _short_kick(sr: int) -> np.ndarray:
    """補助キック(仕様書6章: HPF 60〜100Hz, Decay 40〜100ms, メインより高音)。"""
    n = int(sr * 0.07)
    body = _sine_sweep(sr, n, 240, 95, 0.013) * _env(n, 0.08)
    sos = butter(2, 75, btype="highpass", fs=sr, output="sos")
    return tone.saturate(sosfilt(sos, body), tone.DRIVE["short_kick"])


def _snare(sr: int, pitch_semi: float = 0.0, decay: float = 0.11) -> np.ndarray:
    n = int(sr * 0.15)
    body = _sine_sweep(sr, n, 190 * (2 ** (pitch_semi / 12)), 140, 0.02) * _env(n, decay * 0.6)
    noise = np.random.uniform(-1, 1, n)
    sos = butter(4, [800, 6000], btype="bandpass", fs=sr, output="sos")
    noise = sosfilt(sos, noise) * _env(n, decay)
    return tone.saturate(body * 0.6 + noise * 0.9, tone.DRIVE["snare"])


def _hat(sr: int, open_hat: bool = False) -> np.ndarray:
    n = int(sr * (0.26 if open_hat else 0.04))
    noise = np.random.uniform(-1, 1, n)
    sos = butter(4, 7500, btype="highpass", fs=sr, output="sos")
    hat = sosfilt(sos, noise) * _env(n, 0.3 if open_hat else 0.05)
    return tone.saturate(hat, tone.DRIVE["hat"])


def _shaker(sr: int) -> np.ndarray:
    """16分ゴースト用の細かいシェイカー。ハットより柔らかく短い。"""
    n = int(sr * 0.03)
    noise = np.random.uniform(-1, 1, n)
    sos = butter(4, [5000, 12000], btype="bandpass", fs=sr, output="sos")
    return tone.saturate(sosfilt(sos, noise) * _env(n, 0.12), tone.DRIVE["shaker"])


def _cowbell(sr: int, pitch_semi: float) -> np.ndarray:
    """金属的な倍音を持つカウベル。基音は低めで、ハードクリップで歪ませる。"""
    n = int(sr * 0.11)
    f0 = 420 * (2 ** (pitch_semi / 12))
    t = np.arange(n) / sr
    # 非整数倍の2音を重ねて金属感を出す
    osc = (np.sign(np.sin(2 * np.pi * f0 * t)) * 0.45
           + np.sin(2 * np.pi * f0 * 1.48 * t) * 0.35
           + np.sin(2 * np.pi * f0 * 2.67 * t) * 0.2)
    sos = butter(2, 300, btype="highpass", fs=sr, output="sos")
    # 歪ませてから減衰させる(先に減衰させると尻尾だけ歪みが薄くなる)
    return tone.distort(sosfilt(sos, osc)) * _env(n, 0.09)


def _woodblock(sr: int, pitch_semi: float = 0.0) -> np.ndarray:
    n = int(sr * 0.045)
    f0 = 950 * (2 ** (pitch_semi / 12))
    t = np.arange(n) / sr
    osc = np.sin(2 * np.pi * f0 * t) + 0.3 * np.sin(2 * np.pi * f0 * 2.4 * t)
    return tone.saturate(osc * _env(n, 0.028), tone.DRIVE["woodblock"])


def _tom(sr: int, pitch_semi: float = 0.0) -> np.ndarray:
    n = int(sr * 0.17)
    f = 2 ** (pitch_semi / 12)
    body = _sine_sweep(sr, n, 230 * f, 115 * f, 0.05) * _env(n, 0.14)
    return tone.saturate(body, tone.DRIVE["tom"])


def _mix_at(track: np.ndarray, sound: np.ndarray, pos: int, gain: float = 1.0) -> None:
    end = min(pos + len(sound), len(track))
    if end <= pos:
        return
    track[pos:end] += sound[: end - pos] * gain


def _snare_roll(sr: int, bpm: float) -> np.ndarray:
    """1小節ビルド(仕様書7章): 8分->16分->16分->32分、ピッチとベロシティが上昇。"""
    beat_sec = 60.0 / bpm
    track = np.zeros(int(beat_sec * 4 * sr), dtype=np.float64)

    subdivisions = [2, 4, 4, 8]
    total_hits = sum(subdivisions)
    hit_index = 0

    for beat, n_hits in enumerate(subdivisions):
        for i in range(n_hits):
            # 最後の1/4拍は無音にしてドロップへの間を作る
            if beat == 3 and i >= n_hits - 2:
                hit_index += 1
                continue
            t = beat * beat_sec + i * (beat_sec / n_hits)
            progress = hit_index / max(1, total_hits - 1)
            _mix_at(track, _snare(sr, pitch_semi=progress * 7, decay=0.07),
                    int(t * sr), gain=0.35 + 0.65 * progress)
            hit_index += 1

    return track


def _tom_fill(sr: int, bpm: float) -> np.ndarray:
    """4小節目用のタムフィル(仕様書17.1 BAR4)。後半2拍で下降するタム連打。"""
    beat_sec = 60.0 / bpm
    step_sec = beat_sec / 4
    track = np.zeros(int(beat_sec * 4 * sr), dtype=np.float64)

    # 後半2拍(step 8〜15)を16分で下降
    for i, step in enumerate(range(8, 16)):
        pitch = 4 - i * 1.5
        _mix_at(track, _tom(sr, pitch), int(step * step_sec * sr),
                gain=0.6 + 0.05 * i)
    return track


# ブレイクが小節のどのstep(0始まり)から通常パターンを乗っ取るか。
# "large" は0=小節まるごと差し替え。
_BREAK_TAKEOVER_STEP = {"small": 12, "large": 0}


def _small_break(sr: int, bpm: float) -> np.ndarray:
    """4小節目用の小さいブレイク。最後の1拍だけ下降タム+クラップで区切る。"""
    step_sec = 60.0 / bpm / 4
    track = np.zeros(int(step_sec * 4 * sr), dtype=np.float64)

    # 4つの16分で下降するタム
    for i in range(4):
        _mix_at(track, _tom(sr, 3 - i * 2.5), int(i * step_sec * sr),
                gain=0.75 + 0.05 * i)
    # 頭にスネアを重ねてフィルの入りを明確にする
    _mix_at(track, _snare(sr), 0, gain=0.7)
    return track


def _large_break(sr: int, bpm: float) -> np.ndarray:
    """8小節目用の大きいブレイク。小節まるごとキックだけで刻む。

        拍1「どん」 拍2「どん」 拍3「どんどん」(1/2拍)
        拍4「どど」(1/4拍) +「どどどど」(1/8拍)

    最後の1拍(6発)でピッチが段階的に1オクターブ上がる。
    """
    beat_sec = 60.0 / bpm
    track = np.zeros(int(beat_sec * 4 * sr), dtype=np.float64)

    # (拍位置, ピッチ, 音量)
    hits: list[tuple[float, float, float]] = [
        (0.0, 0.0, 1.00),   # 拍1 どん
        (1.0, 0.0, 1.00),   # 拍2 どん
        (2.0, 0.0, 0.95),   # 拍3 どん
        (2.5, 0.0, 0.95),   # 拍3 どん (1/2拍)
    ]

    # 拍4: 1/4拍を2発 → 1/8拍を4発。この6発で1オクターブ上昇。
    offsets = [0.0, 0.25, 0.5, 0.625, 0.75, 0.875]
    for i, off in enumerate(offsets):
        pitch = 12.0 * i / (len(offsets) - 1)
        hits.append((3.0 + off, pitch, 0.85 + 0.15 * i / (len(offsets) - 1)))

    for beat_pos, pitch, gain in hits:
        _mix_at(track, _main_kick(sr, pitch_semi=pitch),
                int(beat_pos * beat_sec * sr), gain)

    return track


class Groove:
    """打点を機械的な等間隔・等音量から外すための揺らぎ。

    完全にクオンタイズされ音量も一定だと「打ち込み臭さ」が強く出るため、
    スウィング(16分の裏を後ろへずらす)、微小なタイミング揺れ、
    ベロシティの揺れを掛ける。同一Seedなら同じ揺らぎを再現する。
    """

    def __init__(self, swing: float = 0.5, humanize_ms: float = 0.0,
                 velocity_jitter: float = 0.0, seed: int = 0):
        # swing=0.5 でストレート。0.5〜0.7 で跳ねる。
        self.swing = swing
        self.humanize_ms = humanize_ms
        self.velocity_jitter = velocity_jitter
        self._rng = np.random.default_rng(seed)

    def offset_samples(self, step: int, step_sec: float, sr: int) -> int:
        shift = 0.0
        if step % 2 == 1:
            # 16分裏を後ろへ。swing=0.5なら移動なし。
            shift += (self.swing - 0.5) * 2 * step_sec
        if self.humanize_ms:
            shift += self._rng.normal(0, self.humanize_ms / 1000.0)
        return int(shift * sr)

    def gain(self, base: float) -> float:
        if not self.velocity_jitter:
            return base
        g = base * (1.0 + self._rng.normal(0, self.velocity_jitter))
        return float(np.clip(g, 0.05, 1.5))


_STRAIGHT = Groove()


def generate_drum_layers(bpm: float, arrangement: list[dict], sr: int = 44100,
                          groove: "Groove | None" = None
                          ) -> tuple[np.ndarray, list[int]]:
    """Arrangementに従いドラムを合成し、(波形, キック発音位置) を返す。

    キック位置はサイドチェイン(仕様書10.5)を掛けるために呼び出し側へ渡す。
    """
    groove = groove or _STRAIGHT
    clock = ClockGrid(bpm, sr)
    total_samples = clock.bar_samples() * len(arrangement)
    track = np.zeros(total_samples, dtype=np.float64)
    kick_hits: list[int] = []

    for bar_info in arrangement:
        bar = bar_info["bar"]
        layers = bar_info["layers"]
        fill = bar_info.get("fill")
        brk = bar_info.get("break")

        # フィル小節は通常パターンを差し替える
        if fill == "snare_roll":
            _mix_at(track, _snare_roll(sr, bpm), clock.step_to_sample(bar, 0))
            continue

        takeover = _BREAK_TAKEOVER_STEP.get(brk, 16)

        for step in range(16):
            # ブレイク区間は通常パターンを鳴らさず、下でブレイクを重ねる
            if step >= takeover:
                continue
            # patterns.py は1始まり(DAWのステップ表示に合わせている)
            n = step + 1
            pos = clock.step_to_sample(bar, step) + groove.offset_samples(
                step, clock.step_sec, sr)
            pos = max(0, pos)
            g = groove.gain

            if "main_kick" in layers and n in patterns.MAIN_KICK:
                _mix_at(track, _main_kick(sr), pos, g(patterns.MAIN_KICK[n]))
                kick_hits.append(pos)
            if "short_kick" in layers and n in patterns.SHORT_KICK:
                _mix_at(track, _short_kick(sr), pos, g(patterns.SHORT_KICK[n]))
            if "snare" in layers and n in patterns.SNARE:
                _mix_at(track, _snare(sr), pos, g(patterns.SNARE[n]))
            if "hat_closed" in layers and n in patterns.HAT_CLOSED:
                _mix_at(track, _hat(sr), pos, g(patterns.HAT_CLOSED[n]))
            if "hat_ghost" in layers and n in patterns.HAT_GHOST:
                _mix_at(track, _shaker(sr), pos, g(patterns.HAT_GHOST[n]))
            if "hat_open" in layers and n in patterns.HAT_OPEN:
                _mix_at(track, _hat(sr, open_hat=True), pos, g(patterns.HAT_OPEN[n]))
            if "cowbell" in layers and n in patterns.COWBELL:
                gain, pitch = patterns.COWBELL[n]
                _mix_at(track, _cowbell(sr, pitch), pos, g(gain))
            if "woodblock" in layers and n in patterns.WOODBLOCK:
                _mix_at(track, _woodblock(sr), pos, g(patterns.WOODBLOCK[n]))
            if "tom" in layers and n in patterns.TOM:
                gain, pitch = patterns.TOM[n]
                _mix_at(track, _tom(sr, pitch), pos, g(gain))

        # タムフィルは通常パターンに重ねる(仕様書17.1 BAR4)
        if fill == "tom":
            _mix_at(track, _tom_fill(sr, bpm), clock.step_to_sample(bar, 0), 0.8)

        if brk == "small":
            _mix_at(track, _small_break(sr, bpm),
                    clock.step_to_sample(bar, takeover))
        elif brk == "large":
            _mix_at(track, _large_break(sr, bpm),
                    clock.step_to_sample(bar, takeover))

    peak = np.max(np.abs(track)) or 1.0
    return (track / peak * 0.9).astype(np.float32), kick_hits
