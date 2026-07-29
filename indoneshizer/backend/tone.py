"""各音色の歪み設定。

バス段(bus.py)のサチュレーションは音が合算された後に掛かるが、
ここは1音ずつに掛ける。個別に倍音を足してから足し算した方が
各パートの輪郭が残ったまま太くなる。

DRIVE を上げるほど歪む。1.0 でほぼ素通し。
"""
import numpy as np

# ソフトサチュレーション量(tanh)。音色ごとに調整する。
DRIVE = {
    "main_kick": 3.2,   # 凶悪化のため他より深く歪ませる
    "short_kick": 1.7,
    "snare": 1.8,
    "hat": 1.4,
    "shaker": 1.3,
    "woodblock": 1.5,
    "tom": 1.7,
}

# カウベルとハットはソフトではなくハードクリップで歪ませる。
COWBELL_DRIVE = 5.0
COWBELL_CLIP = 0.55

HAT_DRIVE = 4.5
HAT_CLIP = 0.5

# キックを凶悪にするためのコンプ設定。
# アタックを速く・レシオを深くして頭を潰し、メイクアップで胴体を持ち上げる。
KICK_COMP = {
    "threshold_db": -22.0,
    "ratio": 8.0,
    "attack_ms": 1.0,
    "release_ms": 55.0,
    "makeup_db": 7.0,
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
