"""8小節単位のArrangementを構築する(仕様書17章, 19章)。

仕様書のBAR1-8テンプレート(ビルド)を1ブロックとして繰り返す簡略版。
BAR9-16の"Full Drop"(シンセリード/ボーカルチョップ/Amen/DJカウント)は
対応する音源・処理が未実装のため、MVPでは全ブロックをBAR1-8テンプレート
として扱う(仮定として明記)。同一Seedなら同一Arrangementを再現できる。
"""
import random

_LAYER_ADDITIONS = {
    0: {"main_kick", "short_kick", "snare", "hat_closed"},
    1: {"cowbell"},
    2: {"woodblock"},
    3: {"tom"},
    4: set(),
    5: set(),
    6: set(),
    7: set(),
}
_FILL_BAR = {3: "tom", 7: "snare_roll"}


def build_arrangement(n_bars: int, seed: int = 0) -> list[dict]:
    rng = random.Random(seed)  # 将来のランダム要素(ヴァリエーション選択等)用に確保
    bars = []
    active_layers: set[str] = set()

    for bar in range(n_bars):
        pos_in_block = bar % 8
        if pos_in_block == 0:
            active_layers = set()  # 新しい8小節ブロックの頭でリセット

        active_layers |= _LAYER_ADDITIONS[pos_in_block]

        bars.append({
            "bar": bar,
            "layers": set(active_layers),
            "fill": _FILL_BAR.get(pos_in_block),
            "bass_active": pos_in_block >= 4,
            "bass_variation": pos_in_block >= 5,
        })

    _ = rng  # 現状未使用だがSeed再現性のIFとして保持
    return bars
