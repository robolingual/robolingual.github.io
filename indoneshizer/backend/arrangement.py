"""8小節単位のArrangementを構築する(仕様書17章, 19章)。

仕様書17.1のBAR1-8テンプレート(ビルド)を1ブロックとして繰り返す簡略版。
BAR9-16の"Full Drop"(シンセリード/ボーカルチョップ/Amen/DJカウント)は
対応する音源・処理が未実装のため、MVPでは全ブロックをBAR1-8テンプレート
として扱う(仮定として明記)。同一Seedなら同一Arrangementを再現できる。
"""
import random

# 8小節ブロック内の位置ごとに「新規に追加される」レイヤー。
# 前の小節までの分は積み上がる(累積)。仕様書17.1に対応。
_LAYER_ADDITIONS = {
    0: {"main_kick", "short_kick", "snare", "hat_closed"},
    1: {"cowbell", "hat_open"},
    2: {"woodblock", "hat_ghost"},
    3: {"tom"},
    4: set(),   # BAR5: bassの追加はbass_activeで表現
    5: set(),   # BAR6: bass variation
    6: set(),   # BAR7: 本来はVoice追加だが声ネタ素材が未対応
    7: set(),   # BAR8: snare rollで上書き
}
_FILL_BAR = {3: "tom", 7: "snare_roll"}


def build_arrangement(n_bars: int, seed: int = 0) -> list[dict]:
    rng = random.Random(seed)  # 将来のヴァリエーション選択用。現状は未使用。
    bars = []
    active_layers: set[str] = set()

    for bar in range(n_bars):
        pos_in_block = bar % 8
        if pos_in_block == 0:
            active_layers = set()  # 8小節ブロックの頭でリセット

        active_layers |= _LAYER_ADDITIONS[pos_in_block]

        bars.append({
            "bar": bar,
            "layers": set(active_layers),
            "fill": _FILL_BAR.get(pos_in_block),
            "bass_active": pos_in_block >= 4,
            "bass_variation": pos_in_block >= 5,
        })

    _ = rng
    return bars
