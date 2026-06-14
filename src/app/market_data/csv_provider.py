"""Replay provider over cached real market data (CSV under data/).

Real daily OHLCV pulled by scripts/fetch_data.py. Lets the backtest run on
actual prices (AAPL, MSFT, …) without a live IB connection or API key.
"""
from __future__ import annotations

import csv
from collections.abc import AsyncIterator, Iterable
from datetime import datetime, timezone
from pathlib import Path

from app.core.types import Bar
from app.market_data.base import MarketDataProvider

DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def available_symbols() -> list[str]:
    if not DATA_DIR.exists():
        return []
    return sorted(p.stem for p in DATA_DIR.glob("*.csv"))


def has_symbol(symbol: str) -> bool:
    return (DATA_DIR / f"{symbol.upper()}.csv").exists()


class CsvMarketDataProvider(MarketDataProvider):
    """Reads `data/<SYMBOL>.csv` and replays the most recent `lookback` bars."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self._dir = data_dir or DATA_DIR

    async def connect(self) -> None:  # nothing to open
        return None

    async def disconnect(self) -> None:
        return None

    def _load(self, symbol: str) -> list[Bar]:
        path = self._dir / f"{symbol.upper()}.csv"
        if not path.exists():
            raise FileNotFoundError(f"no cached data for {symbol} ({path})")
        bars: list[Bar] = []
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                ts = datetime.strptime(row["Date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                bars.append(
                    Bar(
                        symbol.upper(),
                        ts,
                        float(row["Open"]),
                        float(row["High"]),
                        float(row["Low"]),
                        float(row["Close"]),
                        float(row["Volume"]),
                    )
                )
        return bars

    async def historical_bars(
        self, symbol: str, lookback: int, bar_size: str = "1 day"
    ) -> list[Bar]:
        bars = self._load(symbol)
        return bars[-lookback:] if lookback > 0 else bars

    async def stream_bars(self, symbols: Iterable[str]) -> AsyncIterator[Bar]:
        raise NotImplementedError("CSV provider is for historical replay only")
