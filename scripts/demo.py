"""Standalone demo: backtest + single mock trade, no infra required.

    PYTHONPATH=src python scripts/demo.py
"""
import asyncio

from app.backtest.engine import Backtester
from app.config import get_settings
from app.engine import TradingEngine
from app.market_data.mock_provider import MockMarketDataProvider
from app.risk.manager import RiskLimits, RiskManager
from app.signals.sma_crossover import SMACrossover


async def main() -> None:
    provider = MockMarketDataProvider()
    await provider.connect()
    bars = await provider.historical_bars("AAPL", 250)

    bt = Backtester(SMACrossover(10, 30), RiskManager(RiskLimits(max_position_usd=1e9)))
    res = bt.run(bars)
    print(f"[backtest] bars={len(bars)} trades={res.trades} "
          f"rejected={res.rejected} pnl={res.realized_pnl:.2f}")

    engine = TradingEngine(get_settings())
    await engine.start()
    order = await engine.process_symbol("AAPL")
    await engine.stop()
    if order:
        print(f"[live-mock] {order.side.value} {order.filled_quantity} AAPL "
              f"@ {order.avg_fill_price} -> {order.status.value}")
    else:
        print("[live-mock] no signal on latest bar")


if __name__ == "__main__":
    asyncio.run(main())
