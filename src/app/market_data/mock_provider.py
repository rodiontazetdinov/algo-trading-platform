"""Deterministic synthetic market data — used for tests, demos and backtests."""
from __future__ import annotations

import asyncio
import math
import random
from collections.abc import AsyncIterator, Iterable
from datetime import datetime, timedelta, timezone

from app.core.types import Bar
from app.market_data.base import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    def __init__(self, seed: int = 42, start_price: float = 100.0) -> None:
        self._seed = seed
        self._start_price = start_price
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    def _series(self, symbol: str, n: int) -> list[Bar]:
        rng = random.Random(f"{self._seed}-{symbol}")
        price = self._start_price
        bars: list[Bar] = []
        t0 = datetime.now(timezone.utc) - timedelta(days=n)
        for i in range(n):
            drift = math.sin(i / 12) * 0.5
            price = max(1.0, price + drift + rng.uniform(-1.5, 1.5))
            o = price
            c = max(1.0, price + rng.uniform(-1.0, 1.0))
            h = max(o, c) + rng.uniform(0, 1.0)
            low = min(o, c) - rng.uniform(0, 1.0)
            bars.append(
                Bar(symbol, t0 + timedelta(days=i), o, h, low, c, rng.uniform(1e5, 1e6))
            )
        return bars

    async def historical_bars(
        self, symbol: str, lookback: int, bar_size: str = "1 day"
    ) -> list[Bar]:
        return self._series(symbol, lookback)

    async def stream_bars(self, symbols: Iterable[str]) -> AsyncIterator[Bar]:
        symbols = list(symbols)
        caches = {s: self._series(s, 1)[-1].close for s in symbols}
        rng = random.Random(self._seed)
        while self._connected:
            for s in symbols:
                px = max(1.0, caches[s] + rng.uniform(-1.0, 1.0))
                caches[s] = px
                yield Bar(s, datetime.now(timezone.utc), px, px, px, px, rng.uniform(1e4, 1e5))
            await asyncio.sleep(1.0)
