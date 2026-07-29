"""各音色の歪み設定。

バス段(bus.py)のサチュレーションは音が合算された後に掛かるが、
ここは1音ずつに掛ける。個別に倍音を足してから足し算した方が
各パートの輪郭が残ったまま太くなる。

DRIVE を上げるほど歪む。1.0 でほぼ素通し。
"""
import numpy as np

# ソフトサチュレーション量(tanh)。音色ごとに調整する。
DRIVE = {
    "main_kick": 7.0,
    "short_kick": 4.5,
    "snare": 5.0,
    "hat": 3.0,
    "woodblock": 4.0,
    "tom": 4.5,
}

# カウベルとハットはソフトではなくハードクリップで歪ませる。
COWBELL_DRIVE = 14.0
COWBELL_CLIP = 0.35

HAT_DRIVE = 13.0
HAT_CLIP = 0.35

# キックを凶悪にするためのコンプ設定。
# アタックを速く・レシオを深くして頭を潰し、メイクアップで胴体を持ち上げる。
KICK_COMP = {
    "threshold_db": -28.0,
    "ratio": 14.0,
    "attack_ms": 0.5,
    "release_ms": 50.0,
    "makeup_db": 10.0,
}

# メインキックの基準ピッチ(半音)。全体を下げたいときにここを触る。
KICK_PITCH_SEMI = -2.0

# リバーブは全体に掛けると濁るので、カウベルにだけ掛ける。
REVERB_LAYERS = ("cowbell",)
REVERB = {
    "wet": 0.30,
    "decay_sec": 0.6,
    "predelay_ms": 12.0,
}


def saturate(x: np.ndarray, drive: float) -> np.ndarray:
    """tanhによるソフトクリップ。奇数次倍音が乗って太くなる。

    drive で割り戻して、歪み量を変えても音量が大きく変わらないようにする。
    """
    if drive <= 1.0:
        return x
    return np.tanh(x * drive) / np.tanh(drive)


def distort(x: np.ndarray, drive: float = COWBELL_DRIVE,
            clip: float = COWBELL_CLIP) -> np.ndarray:
    """ハードクリップ主体の歪み。tanhより荒く、金属的な倍音が出る。"""
    y = np.clip(x * drive, -clip, clip) / clip
    # 完全な角を少しだけ丸めて、デジタル臭い折り返しを抑える
    return np.tanh(y * 1.3) / np.tanh(1.3)
