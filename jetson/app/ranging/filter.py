from __future__ import annotations

from collections import deque
from statistics import median


class DistanceFilter:
    def __init__(self, window: int = 1, alpha: float = 1.0, outlier_m: float = 15.0):
        self.values: deque[float] = deque(maxlen=window)
        self.alpha, self.outlier_m = alpha, outlier_m
        self.ema: float | None = None

    def update(self, value: float) -> float | None:
        if value <= 0 or value > 500:
            return self.ema
        if self.ema is not None and abs(value - self.ema) > self.outlier_m:
            return self.ema
        self.values.append(value)
        sample = median(self.values)
        self.ema = sample if self.ema is None else self.alpha * sample + (1-self.alpha) * self.ema
        return self.ema
