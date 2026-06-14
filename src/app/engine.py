"""TradingEngine — wires market data -> strategy -> risk -> OMS -> execution.

Factory selects components by TRADING_MODE (mock | paper | live) so the exact
same signal/risk/OMS path is used for backtest, paper and live trading.
"""
from __future__ import annotations

from app.config import Settings
from app.core.logging import get_logger
from app.core.metrics import ORDERS_REJECTED, ORDERS_SUBMITTED, SIGNALS_GENERATED
from app.core.types import Order, OrderType
from app.execution.base import ExecutionGateway
from app.execution.paper_executor import PaperExecutionGateway
from app.market_data.base import MarketDataProvider
from app.market_data.mock_provider import MockMarketDataProvider
from app.oms.manager import OMS
from app.risk.manager import RiskLimits, RiskManager
from app.signals.base import Strategy
from app.signals.sma_crossover import SMACrossover

log = get_logger("engine")


def build_market_data(s: Settings) -> MarketDataProvider:
    if s.trading_mode in ("paper_ib", "live"):
        from app.market_data.ib_provider import IBMarketDataProvider

        return IBMarketDataProvider(s)
    return MockMarketDataProvider()


def build_execution(s: Settings) -> ExecutionGateway:
    if s.trading_mode == "live":
        from app.execution.ib_executor import IBExecutionGateway

        return IBExecutionGateway(s)
    return PaperExecutionGateway()


class TradingEngine:
    def __init__(self, settings: Settings, strategy: Strategy | None = None) -> None:
        self.s = settings
        self.strategy = strategy or SMACrossover()
        self.oms = OMS()
        self.risk = RiskManager(
            RiskLimits(
                settings.risk_max_position_usd,
                settings.risk_max_daily_loss_usd,
                settings.risk_max_order_qty,
            )
        )
        self.market_data = build_market_data(settings)
        self.execution = build_execution(settings)

    async def start(self) -> None:
        await self.market_data.connect()
        await self.execution.connect()
        log.info("engine_started", mode=self.s.trading_mode)

    async def stop(self) -> None:
        await self.market_data.disconnect()
        await self.execution.disconnect()

    async def process_symbol(self, symbol: str, qty: int = 100) -> Order | None:
        """Single pass: pull history -> signal -> risk -> execute. Returns order if any."""
        bars = await self.market_data.historical_bars(symbol, lookback=60)
        signal = self.strategy.on_bars(bars)
        if signal is None:
            return None
        SIGNALS_GENERATED.labels(signal.strategy, signal.side.value).inc()

        last = bars[-1].close
        order = Order(symbol, signal.side, qty, OrderType.MARKET)
        decision = self.risk.check(order, last, self.oms.get_position(symbol))
        if not decision.approved:
            ORDERS_REJECTED.labels(decision.reason).inc()
            log.info("order_rejected", symbol=symbol, reason=decision.reason)
            return None

        self.oms.register(order)
        order = await self.execution.submit(order, last)
        self.oms.on_fill(order, order.filled_quantity, order.avg_fill_price)
        ORDERS_SUBMITTED.labels(symbol, signal.side.value).inc()
        return order
