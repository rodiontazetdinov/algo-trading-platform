"""Classic SMA crossover strategy (fast crosses slow)."""
from __future__ import annotations

from app.core.types import Bar, Side, Signal
from app.signals.base import Strategy


def sma(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


class SMACrossover(Strategy):
    name = "sma_crossover"

    def __init__(self, fast: int = 10, slow: int = 30) -> None:
        if fast >= slow:
            raise ValueError("fast window must be < slow window")
        self.fast = fast
        self.slow = slow

    def on_bars(self, bars: list[Bar]) -> Signal | None:
        if len(bars) < self.slow + 1:
            return None
        closes = [b.close for b in bars]
        fast_prev, fast_now = sma(closes[:-1], self.fast), sma(closes, self.fast)
        slow_prev, slow_now = sma(closes[:-1], self.slow), sma(closes, self.slow)
        if None in (fast_prev, fast_now, slow_prev, slow_now):
            return None

        crossed_up = fast_prev <= slow_prev and fast_now > slow_now
        crossed_down = fast_prev >= slow_prev and fast_now < slow_now
        if not (crossed_up or crossed_down):
            return None

        side = Side.BUY if crossed_up else Side.SELL
        strength = min(1.0, abs(fast_now - slow_now) / slow_now)
        return Signal(bars[-1].symbol, side, strength, self.name)
