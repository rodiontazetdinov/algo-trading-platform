"""Simulated execution — fills market orders immediately at last price.

Used for `mock` and `paper` (local simulation) trading modes.
"""
from __future__ import annotations

from app.core.types import Order, OrderStatus
from app.execution.base import ExecutionGateway


class PaperExecutionGateway(ExecutionGateway):
    def __init__(self, slippage_bps: float = 1.0) -> None:
        self._slippage = slippage_bps / 10_000

    async def connect(self) -> None:  # nothing to connect
        return None

    async def disconnect(self) -> None:
        return None

    async def submit(self, order: Order, last_price: float) -> Order:
        fill_price = last_price * (1 + self._slippage)
        order.broker_order_id = f"paper-{id(order)}"
        order.filled_quantity = order.quantity
        order.avg_fill_price = round(fill_price, 4)
        order.status = OrderStatus.FILLED
        return order
