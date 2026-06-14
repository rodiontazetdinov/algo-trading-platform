"""Abstract market-data provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterable

from app.core.types import Bar


class MarketDataProvider(ABC):
    """All providers (IB, mock, replay) implement this contract."""

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def historical_bars(
        self, symbol: str, lookback: int, bar_size: str = "1 day"
    ) -> list[Bar]:
        """Return the most recent `lookback` bars for `symbol`."""

    @abstractmethod
    def stream_bars(self, symbols: Iterable[str]) -> AsyncIterator[Bar]:
        """Yield live bars as they arrive."""
