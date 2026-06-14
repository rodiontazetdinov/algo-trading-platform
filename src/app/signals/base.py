"""Strategy interface — turns a window of bars into an optional signal."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.types import Bar, Signal


class Strategy(ABC):
    name: str = "base"

    @abstractmethod
    def on_bars(self, bars: list[Bar]) -> Signal | None:
        """Return a Signal or None given the most recent bars (oldest first)."""
