"""Event-driven backtester. Replays bars through a strategy + the same OMS/risk path."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.core.types import Bar, Order, OrderType, Side
from app.oms.manager import OMS
from app.risk.manager import RiskManager
from app.signals.base import Strategy


@dataclass
class BacktestResult:
    trades: int = 0
    rejected: int = 0
    realized_pnl: float = 0.0
    equity_curve: list[float] = field(default_factory=list)
    final_positions: dict[str, int] = field(default_factory=dict)
    sharpe: float = 0.0
    max_drawdown: float = 0.0

    @property
    def win_rate(self) -> float:
        return 0.0  # placeholder; per-trade PnL attribution lives in the full version


def _sharpe(equity: list[float]) -> float:
    """Annualised Sharpe of the equity curve's per-bar returns (assumes daily bars)."""
    if len(equity) < 2:
        return 0.0
    rets = [b - a for a, b in zip(equity, equity[1:])]
    n = len(rets)
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / n
    std = math.sqrt(var)
    if std == 0:
        return 0.0
    return (mean / std) * math.sqrt(252)


def _max_drawdown(equity: list[float]) -> float:
    """Largest peak-to-trough drop on the equity curve, in absolute terms."""
    peak = equity[0] if equity else 0.0
    mdd = 0.0
    for v in equity:
        peak = max(peak, v)
        mdd = max(mdd, peak - v)
    return mdd


class Backtester:
    def __init__(self, strategy: Strategy, risk: RiskManager, qty: int = 100) -> None:
        self.strategy = strategy
        self.risk = risk
        self.oms = OMS()
        self.qty = qty

    def run(self, bars: list[Bar]) -> BacktestResult:
        res = BacktestResult()
        window: list[Bar] = []
        cash = 0.0
        for bar in bars:
            window.append(bar)
            signal = self.strategy.on_bars(window)
            if signal is not None:
                order = Order(
                    symbol=signal.symbol,
                    side=signal.side,
                    quantity=self.qty,
                    order_type=OrderType.MARKET,
                )
                pos = self.oms.get_position(order.symbol)
                decision = self.risk.check(order, bar.close, pos)
                if decision.approved:
                    self.oms.register(order)
                    self.oms.on_fill(order, order.quantity, bar.close)
                    cash += (-1 if signal.side is Side.BUY else 1) * order.quantity * bar.close
                    res.trades += 1
                else:
                    res.rejected += 1
            # mark-to-market equity
            equity = cash + sum(
                p.quantity * bar.close for p in self.oms.positions.values()
            )
            res.equity_curve.append(equity)

        res.realized_pnl = res.equity_curve[-1] if res.equity_curve else 0.0
        res.final_positions = {s: p.quantity for s, p in self.oms.positions.items()}
        res.sharpe = _sharpe(res.equity_curve)
        res.max_drawdown = _max_drawdown(res.equity_curve)
        return res
