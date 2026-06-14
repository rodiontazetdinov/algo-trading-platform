import pytest
from app.market_data.csv_provider import (
    CsvMarketDataProvider,
    available_symbols,
    has_symbol,
)


def test_available_symbols_includes_seeded_tickers():
    syms = available_symbols()
    assert "AAPL" in syms and "SPY" in syms


def test_has_symbol_case_insensitive():
    assert has_symbol("aapl")
    assert not has_symbol("NOSUCH")


@pytest.mark.asyncio
async def test_historical_bars_returns_recent_real_bars():
    p = CsvMarketDataProvider()
    await p.connect()
    bars = await p.historical_bars("AAPL", 100)
    assert len(bars) == 100
    assert all(b.close > 0 for b in bars)
    assert bars[0].timestamp <= bars[-1].timestamp  # chronological
