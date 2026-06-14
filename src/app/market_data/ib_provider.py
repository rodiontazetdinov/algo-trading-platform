"""Interactive Brokers market-data provider (IB Gateway / TWS via ib_insync).

Kept import-light so the rest of the platform runs without a live IB connection.
Connect against a paper account (IB Gateway port 4002 / TWS port 7497) to use it.
"""
from __future__ import annotations

from collections.abc import AsyncIterator, Iterable

from app.config import Settings
from app.core.logging import get_logger
from app.core.types import Bar
from app.market_data.base import MarketDataProvider

log = get_logger("market_data.ib")


class IBMarketDataProvider(MarketDataProvider):
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._ib = None  # ib_insync.IB instance, created on connect()

    async def connect(self) -> None:
        from ib_insync import IB  # imported lazily

        self._ib = IB()
        await self._ib.connectAsync(
            self._s.ib_host, self._s.ib_port, clientId=self._s.ib_client_id
        )
        log.info("ib_connected", host=self._s.ib_host, port=self._s.ib_port)

    async def disconnect(self) -> None:
        if self._ib is not None:
            self._ib.disconnect()

    @staticmethod
    def _contract(symbol: str):
        from ib_insync import Stock

        return Stock(symbol, "SMART", "USD")

    async def historical_bars(
        self, symbol: str, lookback: int, bar_size: str = "1 day"
    ) -> list[Bar]:
        assert self._ib is not None, "call connect() first"
        raw = await self._ib.reqHistoricalDataAsync(
            self._contract(symbol),
            endDateTime="",
            durationStr=f"{lookback} D",
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=True,
        )
        return [
            Bar(symbol, b.date, b.open, b.high, b.low, b.close, float(b.volume))
            for b in raw
        ]

    async def stream_bars(self, symbols: Iterable[str]) -> AsyncIterator[Bar]:
        assert self._ib is not None, "call connect() first"
        for symbol in symbols:
            self._ib.reqMktData(self._contract(symbol))
        async for tickers in self._ib.pendingTickersEvent:
            for t in tickers:
                if t.last is not None:
                    yield Bar(
                        t.contract.symbol, t.time, t.last, t.last, t.last, t.last,
                        float(t.lastSize or 0),
                    )
