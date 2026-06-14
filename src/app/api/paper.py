"""Live Paper Trading endpoints — talk to an IB Gateway/TWS paper account.

Every endpoint degrades gracefully: if the Gateway is unreachable it returns
``{"connected": false, ...}`` instead of erroring, so the demo page stays alive
whether or not a Gateway is running.

Wire-up: set IB_HOST / IB_PORT (paper Gateway = 4002) and run a Gateway logged
into a paper account. See docker-compose / README.
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.core.logging import get_logger

router = APIRouter()
log = get_logger("paper")

_ib = None
_lock = asyncio.Lock()
CONNECT_TIMEOUT = 8.0


async def _get_ib():
    """Return a connected ib_insync.IB, (re)connecting if needed. Raises on failure."""
    global _ib
    from ib_insync import IB

    async with _lock:
        if _ib is not None and _ib.isConnected():
            return _ib
        s = get_settings()
        ib = IB()
        await ib.connectAsync(
            s.ib_host, s.ib_port, clientId=s.ib_client_id + 7, timeout=CONNECT_TIMEOUT
        )
        ib.reqMarketDataType(3)  # delayed data is free on paper
        _ib = ib
        log.info("paper_connected", host=s.ib_host, port=s.ib_port)
        return _ib


def _offline(exc: Exception) -> dict:
    s = get_settings()
    return {
        "connected": False,
        "host": s.ib_host,
        "port": s.ib_port,
        "error": f"{type(exc).__name__}: {exc}",
        "hint": "IB Gateway не запущен или API выключен (paper порт 4002).",
    }


class OrderRequest(BaseModel):
    symbol: str = "AAPL"
    side: str = "BUY"   # BUY | SELL
    qty: int = 1


@router.get("/status")
async def status() -> dict:
    s = get_settings()
    try:
        ib = await _get_ib()
        accounts = ib.managedAccounts()
        return {
            "connected": True,
            "host": s.ib_host,
            "port": s.ib_port,
            "accounts": accounts,
            "account": accounts[0] if accounts else None,
            "server_version": ib.client.serverVersion(),
        }
    except Exception as exc:  # noqa: BLE001 — surface offline state, never 500
        return _offline(exc)


@router.get("/account")
async def account() -> dict:
    try:
        ib = await _get_ib()
        rows = await ib.accountSummaryAsync()
        wanted = {"NetLiquidation", "TotalCashValue", "BuyingPower",
                  "AvailableFunds", "UnrealizedPnL", "RealizedPnL"}
        summary = {r.tag: float(r.value) for r in rows if r.tag in wanted}
        return {"connected": True, "currency": "USD", "summary": summary}
    except Exception as exc:  # noqa: BLE001
        return _offline(exc)


@router.get("/positions")
async def positions() -> dict:
    try:
        ib = await _get_ib()
        pos = [
            {
                "symbol": p.contract.symbol,
                "quantity": p.position,
                "avg_cost": round(p.avgCost, 2),
            }
            for p in ib.positions()
        ]
        return {"connected": True, "positions": pos}
    except Exception as exc:  # noqa: BLE001
        return _offline(exc)


@router.get("/quote")
async def quote(symbol: str = "AAPL") -> dict:
    try:
        from ib_insync import Stock

        ib = await _get_ib()
        contract = Stock(symbol.upper(), "SMART", "USD")
        await ib.qualifyContractsAsync(contract)
        ticker = ib.reqMktData(contract, "", False, False)
        for _ in range(6):
            await asyncio.sleep(0.5)
            if ticker.last is not None or ticker.close is not None:
                break
        ib.cancelMktData(contract)

        def num(x):
            return None if x is None or x != x else round(float(x), 2)  # NaN-safe

        return {
            "connected": True,
            "symbol": symbol.upper(),
            "last": num(ticker.last),
            "bid": num(ticker.bid),
            "ask": num(ticker.ask),
            "close": num(ticker.close),
        }
    except Exception as exc:  # noqa: BLE001
        return _offline(exc)


@router.post("/order")
async def order(req: OrderRequest) -> dict:
    try:
        from ib_insync import MarketOrder, Stock

        ib = await _get_ib()
        contract = Stock(req.symbol.upper(), "SMART", "USD")
        await ib.qualifyContractsAsync(contract)
        side = "BUY" if req.side.upper() == "BUY" else "SELL"
        trade = ib.placeOrder(contract, MarketOrder(side, max(1, req.qty)))
        for _ in range(12):
            await asyncio.sleep(0.5)
            if trade.isDone():
                break
        return {
            "connected": True,
            "symbol": req.symbol.upper(),
            "side": side,
            "qty": req.qty,
            "order_id": trade.order.orderId,
            "status": trade.orderStatus.status,
            "filled": trade.orderStatus.filled,
            "avg_fill_price": round(trade.orderStatus.avgFillPrice, 2)
            if trade.orderStatus.avgFillPrice else None,
        }
    except Exception as exc:  # noqa: BLE001
        return _offline(exc)
