import pytest
from app.backtest.engine import Backtester, _max_drawdown, _sharpe
from app.market_data.mock_provider import MockMarketDataProvider
from app.risk.manager import RiskManager, RiskLimits
from app.signals.sma_crossover import SMACrossover


@pytest.mark.asyncio
async def test_backtest_runs_and_produces_equity_curve():
    provider = MockMarketDataProvider()
    await provider.connect()
    bars = await provider.historical_bars("AAPL", 250)
    bt = Backtester(SMACrossover(5, 20), RiskManager(RiskLimits(max_position_usd=1e9)))
    res = bt.run(bars)
    assert len(res.equity_curve) == len(bars)
    assert res.trades >= 0
    assert res.max_drawdown >= 0.0
    assert isinstance(res.sharpe, float)


def test_max_drawdown_picks_largest_peak_to_trough():
    assert _max_drawdown([100, 120, 90, 110, 60]) == 60.0  # peak 120 → trough 60
    assert _max_drawdown([10, 20, 30]) == 0.0  # monotonic up


def test_sharpe_is_zero_for_flat_equity():
    assert _sharpe([100, 100, 100]) == 0.0
    assert _sharpe([100]) == 0.0
