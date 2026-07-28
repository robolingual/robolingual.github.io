"""8小節単位のArrangementを構築する(仕様書17章, 19章)。

style="loop"(既定):
    ループ素材向け。8小節を通して同じ編成で鳴らし、
    4小節目に小さいブレイク、8小節目に大きいブレイクで変化をつける。

style="build":
    仕様書17.1のBAR1-8テンプレート。1小節ずつレイヤーを足していく。
    曲の頭から組み上げたいときに使う。

BAR9-16の"Full Drop"(シンセリード/ボーカルチョップ/Amen/DJカウント)は
対応する音源・処理が未実装のため未対応(仮定として明記)。
同一Seedなら同一Arrangementを再現できる。
"""
import random

_LOOP_LAYERS = {"main_kick", "short_kick", "snare", "hat_closed", "hat_ghost", "cowbell"}

# style="build" 用。位置ごとに新規追加されるレイヤー(前の小節までの分は積み上がる)。
_BUILD_ADDITIONS = {
    0: {"main_kick", "short_kick", "snare", "hat_closed"},
    1: {"cowbell"},
    2: {"woodblock", "hat_ghost"},
    3: {"tom"},
    4: set(),   # BAR5: bassの追加はbass_activeで表現
    5: set(),   # BAR6: bass variation
    6: set(),   # BAR7: 本来はVoice追加だが声ネタ素材が未対応
    7: set(),
}

# 4小節目に小さいブレイク、8小節目に大きいブレイク。
# ブレイクは小節の途中から通常パターンを乗っ取る形で入る。
_BREAK_BAR = {3: "small", 7: "large"}


def build_arrangement(n_bars: int, seed: int = 0, style: str = "loop") -> list[dict]:
    if style not in ("loop", "build"):
        raise ValueError(f"unknown style: {style}")

    rng = random.Random(seed)  # 将来のヴァリエーション選択用。現状は未使用。
    bars = []
    active_layers: set[str] = set()

    for bar in range(n_bars):
        pos_in_block = bar % 8

        if style == "loop":
            active_layers = set(_LOOP_LAYERS)
        else:
            if pos_in_block == 0:
                active_layers = set()
            active_layers |= _BUILD_ADDITIONS[pos_in_block]

        bars.append({
            "bar": bar,
            "layers": set(active_layers),
            "fill": None,
            "break": _BREAK_BAR.get(pos_in_block),
            "bass_active": True if style == "loop" else pos_in_block >= 4,
            "bass_variation": pos_in_block >= 5,
        })

    _ = rng
    return bars
