"""HTTP API for control, monitoring and on-demand backtests."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.backtest.engine import Backtester
from app.config import get_settings
from app.engine import TradingEngine
from app.market_data.mock_provider import MockMarketDataProvider
from app.risk.manager import RiskLimits, RiskManager
from app.signals.sma_crossover import SMACrossover

router = APIRouter()


class BacktestRequest(BaseModel):
    symbol: str = "AAPL"
    lookback: int = 250
    fast: int = 10
    slow: int = 30
    qty: int = 100


@router.get("/health")
async def health() -> dict:
    s = get_settings()
    return {"status": "ok", "mode": s.trading_mode}


@router.get("/positions")
async def positions() -> dict:
    # In production this reads from the shared engine/OMS; demo returns empty book.
    return {"positions": {}}


@router.post("/backtest")
async def backtest(req: BacktestRequest) -> dict:
    provider = MockMarketDataProvider()
    await provider.connect()
    bars = await provider.historical_bars(req.symbol, req.lookback)
    strat = SMACrossover(req.fast, req.slow)
    risk = RiskManager(RiskLimits())
    bt = Backtester(strat, risk, qty=req.qty)
    result = bt.run(bars)
    return {
        "symbol": req.symbol,
        "bars": len(bars),
        "trades": result.trades,
        "rejected": result.rejected,
        "pnl": round(result.realized_pnl, 2),
        "sharpe": round(result.sharpe, 2),
        "max_drawdown": round(result.max_drawdown, 2),
        "equity_curve": [round(v, 2) for v in result.equity_curve],
        "final_positions": result.final_positions,
    }


@router.post("/run-once")
async def run_once(symbol: str = "AAPL") -> dict:
    engine = TradingEngine(get_settings())
    await engine.start()
    order = await engine.process_symbol(symbol)
    await engine.stop()
    if order is None:
        return {"symbol": symbol, "action": "no_signal"}
    return {
        "symbol": symbol,
        "side": order.side.value,
        "qty": order.filled_quantity,
        "price": order.avg_fill_price,
        "status": order.status.value,
    }
