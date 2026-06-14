"""Pre-trade risk checks. Every order passes through here before execution."""
from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.core.types import Order, Position, Side

log = get_logger("risk")


@dataclass
class RiskLimits:
    max_position_usd: float = 10_000
    max_daily_loss_usd: float = 2_000
    max_order_qty: int = 500


@dataclass
class RiskDecision:
    approved: bool
    reason: str = "ok"


class RiskManager:
    def __init__(self, limits: RiskLimits) -> None:
        self.limits = limits
        self._realized_pnl_today: float = 0.0

    def register_pnl(self, pnl: float) -> None:
        self._realized_pnl_today += pnl

    def check(
        self, order: Order, last_price: float, position: Position | None
    ) -> RiskDecision:
        if order.quantity <= 0:
            return RiskDecision(False, "non_positive_qty")

        if order.quantity > self.limits.max_order_qty:
            return RiskDecision(False, "max_order_qty")

        signed = order.quantity if order.side is Side.BUY else -order.quantity
        current_qty = position.quantity if position else 0
        projected_usd = abs(current_qty + signed) * last_price
        if projected_usd > self.limits.max_position_usd:
            return RiskDecision(False, "max_position_usd")

        if self._realized_pnl_today <= -self.limits.max_daily_loss_usd:
            return RiskDecision(False, "daily_loss_limit")

        return RiskDecision(True, "ok")
