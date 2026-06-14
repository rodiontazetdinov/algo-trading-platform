"""Interactive Brokers execution gateway (ib_insync). Used for `live` mode."""
from __future__ import annotations

from app.config import Settings
from app.core.logging import get_logger
from app.core.types import Order, OrderStatus, OrderType
from app.execution.base import ExecutionGateway

log = get_logger("execution.ib")


class IBExecutionGateway(ExecutionGateway):
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._ib = None

    async def connect(self) -> None:
        from ib_insync import IB

        self._ib = IB()
        await self._ib.connectAsync(
            self._s.ib_host, self._s.ib_port, clientId=self._s.ib_client_id + 100
        )
        log.info("ib_exec_connected", port=self._s.ib_port)

    async def disconnect(self) -> None:
        if self._ib is not None:
            self._ib.disconnect()

    async def submit(self, order: Order, last_price: float) -> Order:
        from ib_insync import LimitOrder, MarketOrder, Stock

        assert self._ib is not None, "call connect() first"
        contract = Stock(order.symbol, "SMART", "USD")
        if order.order_type is OrderType.LIMIT and order.limit_price:
            ib_order = LimitOrder(order.side.value, order.quantity, order.limit_price)
        else:
            ib_order = MarketOrder(order.side.value, order.quantity)

        trade = self._ib.placeOrder(contract, ib_order)
        order.broker_order_id = str(trade.order.orderId)
        order.status = OrderStatus.SUBMITTED
        log.info("ib_order_placed", id=order.broker_order_id, symbol=order.symbol)
        return order
