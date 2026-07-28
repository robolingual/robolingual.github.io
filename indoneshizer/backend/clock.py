"""BPMベースの拍子グリッド(16分刻み)を管理する。"""


class ClockGrid:
    def __init__(self, bpm: float, sr: int):
        self.bpm = bpm
        self.sr = sr
        self.beat_sec = 60.0 / bpm
        self.step_sec = self.beat_sec / 4.0  # 16分音符
        self.bar_sec = self.beat_sec * 4.0

    def step_time(self, bar: int, step: int) -> float:
        return bar * self.bar_sec + step * self.step_sec

    def step_to_sample(self, bar: int, step: int) -> int:
        return int(self.step_time(bar, step) * self.sr)

    def bar_samples(self) -> int:
        return int(self.bar_sec * self.sr)

    def bars_for_duration(self, duration_sec: float) -> int:
        return max(1, int(duration_sec / self.bar_sec) + 1)
