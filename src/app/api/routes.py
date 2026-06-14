"""HTTP API for control, monitoring and on-demand backtests."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.backtest.engine import Backtester
from app.config import get_settings
from app.engine import TradingEngine
from app.market_data.csv_provider import (
    CsvMarketDataProvider,
    available_symbols,
    has_symbol,
)
from app.market_data.mock_provider import MockMarketDataProvider
from app.risk.manager import RiskLimits, RiskManager
from app.signals.sma_crossover import SMACrossover

router = APIRouter()

# Position limit sized for real share prices ($100–500); cranking qty past it
# triggers the risk manager so rejections are visible in the demo.
DEMO_MAX_POSITION_USD = 50_000


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


@router.get("/symbols")
async def symbols() -> dict:
    """Tickers with cached real market data (for the demo dropdown)."""
    return {"symbols": available_symbols()}


@router.post("/backtest")
async def backtest(req: BacktestRequest) -> dict:
    # Real cached data when available, deterministic mock otherwise.
    if has_symbol(req.symbol):
        provider: MockMarketDataProvider | CsvMarketDataProvider = CsvMarketDataProvider()
        data_source = "real"
    else:
        provider = MockMarketDataProvider()
        data_source = "synthetic"
    await provider.connect()
    bars = await provider.historical_bars(req.symbol, req.lookback)
    strat = SMACrossover(req.fast, req.slow)
    risk = RiskManager(RiskLimits(max_position_usd=DEMO_MAX_POSITION_USD))
    bt = Backtester(strat, risk, qty=req.qty)
    result = bt.run(bars)
    return {
        "symbol": req.symbol.upper(),
        "data_source": data_source,
        "bars": len(bars),
        "from": bars[0].timestamp.date().isoformat() if bars else None,
        "to": bars[-1].timestamp.date().isoformat() if bars else None,
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
