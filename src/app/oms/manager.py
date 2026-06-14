"""Order Management System — tracks orders and positions, the single source of truth."""
from __future__ import annotations

from app.core.logging import get_logger
from app.core.types import Order, OrderStatus, Position, Side

log = get_logger("oms")


class OMS:
    def __init__(self) -> None:
        self._orders: dict[int, Order] = {}
        self._positions: dict[str, Position] = {}
        self._seq = 0

    def register(self, order: Order) -> int:
        self._seq += 1
        self._orders[self._seq] = order
        log.info("order_registered", id=self._seq, symbol=order.symbol, side=order.side)
        return self._seq

    def get_position(self, symbol: str) -> Position:
        return self._positions.setdefault(symbol, Position(symbol))

    def on_fill(self, order: Order, fill_qty: int, fill_price: float) -> None:
        order.filled_quantity += fill_qty
        order.avg_fill_price = fill_price
        order.status = (
            OrderStatus.FILLED
            if order.filled_quantity >= order.quantity
            else OrderStatus.PARTIALLY_FILLED
        )
        pos = self.get_position(order.symbol)
        signed = fill_qty if order.side is Side.BUY else -fill_qty
        new_qty = pos.quantity + signed
        if pos.quantity == 0 or (pos.quantity > 0) == (signed > 0):
            # opening or adding to a position -> blend average price
            total_cost = pos.avg_price * abs(pos.quantity) + fill_price * abs(signed)
            pos.avg_price = total_cost / abs(new_qty) if new_qty != 0 else 0.0
        pos.quantity = new_qty
        log.info("fill", symbol=order.symbol, qty=fill_qty, price=fill_price, pos=pos.quantity)

    @property
    def orders(self) -> dict[int, Order]:
        return self._orders

    @property
    def positions(self) -> dict[str, Position]:
        return self._positions
