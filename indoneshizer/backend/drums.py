"""ファンコットの多層ドラムを合成する(仕様書5〜9章)。

打点定義は patterns.py 側に分離してある(耳で詰めながら差し替えるため)。
生サンプル素材は使わず、全パートを波形合成する。
Amen/ブレイクビーツ(9章)はサンプル素材前提のためMVPでは未実装。
"""
import numpy as np
from scipy.signal import butter, sosfilt

import bus
import patterns
import tone
from clock import ClockGrid

# 有効化できるレイヤー名。ArrangementGeneratorが小節ごとに部分集合を渡す。
ALL_LAYERS = frozenset({
    "main_kick", "short_kick", "snare",
    "hat_closed", "hat_open",
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
    tone.KICK_PITCH_SEMI が全体の基準ピッチとして常に加算される。
    """
    pitch_semi = pitch_semi + tone.KICK_PITCH_SEMI
    f = 2 ** (pitch_semi / 12)
    n = int(sr * 0.15 / (1 + max(pitch_semi, 0.0) / 24))
    body = _sine_sweep(sr, n, 320 * f, 58 * f, 0.028) * _env(n, 0.13)
    click = np.random.uniform(-1, 1, n) * _env(n, 0.006)
    raw = body * 1.4 + click * 0.45

    # 速いアタックのコンプで頭を潰し、メイクアップで胴体を持ち上げる。
    # 1発ごとに掛けるので、包絡線そのものが変形して密度が上がる。
    hit = bus.compress(raw, sr, **tone.KICK_COMP)
    return tone.saturate(hit, tone.DRIVE["main_kick"])


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
    """ディストーションを掛けたハット。

    歪ませてから減衰させる。順序が逆だと尾の部分だけ歪みが浅くなる。
    長さと減衰は tone.py 側で調整する。
    """
    len_ms = tone.HAT_OPEN_LEN_MS if open_hat else tone.HAT_CLOSED_LEN_MS
    tau_ms = tone.HAT_OPEN_TAU_MS if open_hat else tone.HAT_CLOSED_TAU_MS
    n = max(1, int(sr * len_ms / 1000))

    noise = np.random.uniform(-1, 1, n)
    sos = butter(4, tone.HAT_HPF_HZ, btype="highpass", fs=sr, output="sos")
    hat = tone.distort(sosfilt(sos, noise), tone.HAT_DRIVE, tone.HAT_CLIP)
    # _env は n に対する比で時定数を取るので、msから換算する
    return hat * _env(n, (tau_ms / 1000) / (n / sr))


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


# ブレイクは (レイヤー名, 音, 小節頭からの秒数, 音量) の並びで返す。
# レイヤーごとに別バッファへ書き込めるようにするため
# (カウベルだけリバーブを掛ける、といった処理をブレイク中にも効かせる)。
BreakEvent = tuple[str, np.ndarray, float, float]


def _small_break(sr: int, bpm: float) -> list[BreakEvent]:
    """4小節目用の小さいブレイク。最後の1拍だけ下降タムで区切る。"""
    step_sec = 60.0 / bpm / 4
    events: list[BreakEvent] = [("snare", _snare(sr), 0.0, 0.7)]
    for i in range(4):
        events.append(("tom", _tom(sr, 3 - i * 2.5), i * step_sec, 0.75 + 0.05 * i))
    return events


def _large_break(sr: int, bpm: float) -> list[BreakEvent]:
    """8小節目用の大きいブレイク。小節まるごと差し替える。

        キック    拍1「どん」拍2「どん」拍3「どんどん」(1/2拍)
                  拍4「どど」(1/4拍) +「どどどど」(1/8拍)
        ハット    各拍の表に「じゃん」x4 (オープンハット、ピッチ変化なし)
        カウベル  最後の拍を半々に割って「カンカン」

    キック最後の1拍(6発)でピッチが段階的に1オクターブ上がる。
    """
    beat_sec = 60.0 / bpm
    events: list[BreakEvent] = []

    kicks: list[tuple[float, float, float]] = [
        (0.0, 0.0, 1.00),   # 拍1 どん
        (1.0, 0.0, 1.00),   # 拍2 どん
        (2.0, 0.0, 0.95),   # 拍3 どん
        (2.5, 0.0, 0.95),   # 拍3 どん (1/2拍)
    ]
    # 拍4: 1/4拍を2発 → 1/8拍を4発。この6発で1オクターブ上昇。
    offsets = [0.0, 0.25, 0.5, 0.625, 0.75, 0.875]
    for i, off in enumerate(offsets):
        pitch = 12.0 * i / (len(offsets) - 1)
        kicks.append((3.0 + off, pitch, 0.85 + 0.15 * i / (len(offsets) - 1)))

    for beat_pos, pitch, gain in kicks:
        events.append(("main_kick", _main_kick(sr, pitch_semi=pitch),
                       beat_pos * beat_sec, gain))

    for beat_pos in range(4):
        events.append(("hat_open", _hat(sr, open_hat=True),
                       beat_pos * beat_sec, 0.55))

    for off, pitch in ((0.0, 0), (0.5, -4)):
        events.append(("cowbell", _cowbell(sr, pitch),
                       (3.0 + off) * beat_sec, 0.7))

    return events


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


def generate_drum_stems(bpm: float, arrangement: list[dict], sr: int = 44100,
                        groove: "Groove | None" = None
                        ) -> tuple[dict[str, np.ndarray], list[int]]:
    """Arrangementに従い、レイヤーごとに分けた波形を返す。

    戻り値は ({レイヤー名: 波形}, キック発音位置)。
    レイヤーを分けておくと、パートごとに別のエフェクトを掛けられる
    (仕様書22章のバス構成)。キック位置はサイドチェイン(10.5)用。
    正規化はここでは行わない(合算側の責務)。
    """
    groove = groove or _STRAIGHT
    clock = ClockGrid(bpm, sr)
    total_samples = clock.bar_samples() * len(arrangement)
    stems: dict[str, np.ndarray] = {}
    kick_hits: list[int] = []

    def buf(name: str) -> np.ndarray:
        if name not in stems:
            stems[name] = np.zeros(total_samples, dtype=np.float64)
        return stems[name]

    for bar_info in arrangement:
        bar = bar_info["bar"]
        layers = bar_info["layers"]
        fill = bar_info.get("fill")
        brk = bar_info.get("break")
        bar_start = clock.step_to_sample(bar, 0)

        # フィル小節は通常パターンを差し替える
        if fill == "snare_roll":
            _mix_at(buf("snare"), _snare_roll(sr, bpm), bar_start)
            continue

        takeover = _BREAK_TAKEOVER_STEP.get(brk, 16)

        for step in range(16):
            # ブレイク区間は通常パターンを鳴らさず、下でブレイクを重ねる
            if step >= takeover:
                continue
            # patterns.py は1始まり(DAWのステップ表示に合わせている)
            n = step + 1
            pos = max(0, clock.step_to_sample(bar, step)
                      + groove.offset_samples(step, clock.step_sec, sr))
            g = groove.gain

            if "main_kick" in layers and n in patterns.MAIN_KICK:
                _mix_at(buf("main_kick"), _main_kick(sr), pos, g(patterns.MAIN_KICK[n]))
                kick_hits.append(pos)
            if "short_kick" in layers and n in patterns.SHORT_KICK:
                _mix_at(buf("short_kick"), _short_kick(sr), pos, g(patterns.SHORT_KICK[n]))
            if "snare" in layers and n in patterns.SNARE:
                _mix_at(buf("snare"), _snare(sr), pos, g(patterns.SNARE[n]))
            if "hat_closed" in layers and n in patterns.HAT_CLOSED:
                _mix_at(buf("hat_closed"), _hat(sr), pos, g(patterns.HAT_CLOSED[n]))
            if "hat_open" in layers and n in patterns.HAT_OPEN:
                _mix_at(buf("hat_open"), _hat(sr, open_hat=True), pos,
                        g(patterns.HAT_OPEN[n]))
            if "cowbell" in layers and n in patterns.COWBELL:
                gain, pitch = patterns.COWBELL[n]
                _mix_at(buf("cowbell"), _cowbell(sr, pitch), pos, g(gain))
            if "woodblock" in layers and n in patterns.WOODBLOCK:
                _mix_at(buf("woodblock"), _woodblock(sr), pos, g(patterns.WOODBLOCK[n]))
            if "tom" in layers and n in patterns.TOM:
                gain, pitch = patterns.TOM[n]
                _mix_at(buf("tom"), _tom(sr, pitch), pos, g(gain))

        # タムフィルは通常パターンに重ねる(仕様書17.1 BAR4)
        if fill == "tom":
            _mix_at(buf("tom"), _tom_fill(sr, bpm), bar_start, 0.8)

        break_events = None
        if brk == "small":
            break_events = _small_break(sr, bpm)
        elif brk == "large":
            break_events = _large_break(sr, bpm)

        if break_events:
            offset = clock.step_to_sample(bar, takeover)
            for layer, sound, t, gain in break_events:
                pos = offset + int(t * sr)
                _mix_at(buf(layer), sound, pos, gain)
                if layer == "main_kick":
                    kick_hits.append(pos)

    return stems, kick_hits


def mix_stems(stems: dict[str, np.ndarray], sr: int,
              reverb_layers: "tuple[str, ...] | None" = None,
              reverb_params: "dict | None" = None) -> np.ndarray:
    """レイヤーを合算する。指定レイヤーにだけリバーブを掛ける。"""
    import reverb as reverb_mod

    reverb_layers = tuple(reverb_layers or ())
    reverb_params = reverb_params or {}

    total = None
    for name, audio in stems.items():
        part = audio
        if name in reverb_layers:
            part = reverb_mod.apply_reverb(part, sr, **reverb_params).astype(np.float64)
            # apply_reverb は内部で正規化するので、元のピークに戻してから混ぜる
            src_peak = np.max(np.abs(audio)) or 1.0
            new_peak = np.max(np.abs(part)) or 1.0
            part = part * (src_peak / new_peak)
        total = part.copy() if total is None else total + part

    if total is None:
        return np.zeros(0, dtype=np.float32)

    peak = np.max(np.abs(total)) or 1.0
    return (total / peak * 0.9).astype(np.float32)


def generate_drum_layers(bpm: float, arrangement: list[dict], sr: int = 44100,
                          groove: "Groove | None" = None
                          ) -> tuple[np.ndarray, list[int]]:
    """レイヤーを合算した波形と、キック発音位置を返す。

    リバーブは tone.REVERB_LAYERS で指定したレイヤーにだけ掛かる。
    """
    stems, kick_hits = generate_drum_stems(bpm, arrangement, sr, groove)
    mixed = mix_stems(stems, sr, tone.REVERB_LAYERS, tone.REVERB)
    return mixed, kick_hits
