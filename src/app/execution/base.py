"""Execution gateway interface — submits orders to a venue."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.types import Order


class ExecutionGateway(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def submit(self, order: Order, last_price: float) -> Order:
        """Submit order to venue and return it updated with fill info."""
