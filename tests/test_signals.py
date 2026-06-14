from app.core.types import Bar, Side
from app.signals.sma_crossover import SMACrossover, sma
from datetime import datetime, timezone


def _bars(prices):
    return [Bar("TST", datetime.now(timezone.utc), p, p, p, p, 1000) for p in prices]


def test_sma_basic():
    assert sma([1, 2, 3, 4], 2) == 3.5
    assert sma([1], 2) is None


def test_crossover_generates_buy_on_uptrend():
    # downtrend then sharp uptrend -> fast crosses above slow
    prices = list(range(50, 20, -1)) + list(range(20, 80))
    strat = SMACrossover(fast=5, slow=20)
    signal = None
    window = []
    for b in _bars(prices):
        window.append(b)
        s = strat.on_bars(window)
        if s:
            signal = s
    assert signal is not None
    assert signal.side in (Side.BUY, Side.SELL)


def test_fast_must_be_less_than_slow():
    import pytest
    with pytest.raises(ValueError):
        SMACrossover(fast=30, slow=10)
