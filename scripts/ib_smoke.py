"""IB smoke test — proves a real Interactive Brokers paper connection end to end.

Run it against a running IB Gateway / TWS logged into a *paper* account:

    PYTHONPATH=src python scripts/ib_smoke.py
    PYTHONPATH=src python scripts/ib_smoke.py --symbol MSFT --no-order

What it does:
  1. connects to IB Gateway (port 4002) / TWS (port 7497) via ib_insync;
  2. requests historical daily bars for a symbol (falls back to delayed data,
     which is free on a paper account);
  3. subscribes to a streaming quote and prints a few ticks;
  4. (optional) places a small MARKET order on the paper account and logs its
     status, then cancels it if it has not filled;
  5. disconnects cleanly.

Configuration is read from the same .env as the platform (see app.config):
  IB_HOST, IB_PORT, IB_CLIENT_ID, IB_ACCOUNT.

SAFETY: order placement only ever runs against a paper account. The script
refuses to place an order unless IB_ACCOUNT looks like a paper id (starts with
"DU") — pass --account-ok to override if your paper id differs.
"""
from __future__ import annotations

import argparse
import asyncio

from app.config import get_settings


async def run(symbol: str, qty: int, place_order: bool, account_ok: bool) -> int:
    # ib_insync is imported lazily so the rest of the repo runs without it installed.
    from ib_insync import IB, MarketOrder, Stock, util

    s = get_settings()
    ib = IB()

    print(f"→ connecting to IB at {s.ib_host}:{s.ib_port} (clientId={s.ib_client_id}) …")
    await ib.connectAsync(s.ib_host, s.ib_port, clientId=s.ib_client_id)
    print(f"✓ connected · server version {ib.client.serverVersion()} · "
          f"accounts={ib.managedAccounts()}")

    # Delayed data is free on paper; switch to it so the script works without a
    # real-time market-data subscription. (1 = live, 3 = delayed.)
    ib.reqMarketDataType(3)

    contract = Stock(symbol, "SMART", "USD")
    await ib.qualifyContractsAsync(contract)

    # --- 1. historical bars -------------------------------------------------
    bars = await ib.reqHistoricalDataAsync(
        contract,
        endDateTime="",
        durationStr="10 D",
        barSizeSetting="1 day",
        whatToShow="TRADES",
        useRTH=True,
    )
    print(f"\n✓ historical: {len(bars)} daily bars for {symbol}")
    for b in bars[-3:]:
        print(f"    {b.date}  O={b.open}  H={b.high}  L={b.low}  C={b.close}  V={b.volume}")

    # --- 2. streaming quote -------------------------------------------------
    print(f"\n→ subscribing to streaming quote for {symbol} …")
    ticker = ib.reqMktData(contract, "", False, False)
    for i in range(5):
        await asyncio.sleep(1)
        print(f"    tick {i + 1}: last={ticker.last}  bid={ticker.bid}  "
              f"ask={ticker.ask}  close={ticker.close}")
    ib.cancelMktData(contract)

    # --- 3. paper order (optional) -----------------------------------------
    if place_order:
        acct = s.ib_account
        if not account_ok and not acct.upper().startswith("DU"):
            print(f"\n⚠ skipping order: IB_ACCOUNT={acct!r} does not look like a paper "
                  f"account (expected 'DU…'). Re-run with --account-ok to force.")
        else:
            print(f"\n→ placing paper MARKET BUY {qty} {symbol} …")
            trade = ib.placeOrder(contract, MarketOrder("BUY", qty))
            for _ in range(10):
                await asyncio.sleep(1)
                print(f"    status: {trade.orderStatus.status}  "
                      f"filled={trade.orderStatus.filled}  "
                      f"avgFill={trade.orderStatus.avgFillPrice}")
                if trade.isDone():
                    break
            if not trade.isDone():
                print("    not filled — cancelling.")
                ib.cancelOrder(trade.order)
                await asyncio.sleep(1)
            print(f"✓ final order status: {trade.orderStatus.status}")
    else:
        print("\n(order placement skipped: --no-order)")

    ib.disconnect()
    print("\n✓ disconnected cleanly.")
    util.sleep(0.2)  # let the event loop flush the disconnect
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="IB paper-account smoke test.")
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--qty", type=int, default=1)
    p.add_argument("--no-order", action="store_true", help="skip placing the paper order")
    p.add_argument("--account-ok", action="store_true",
                   help="allow ordering even if IB_ACCOUNT does not start with 'DU'")
    args = p.parse_args()
    try:
        return asyncio.run(
            run(args.symbol, args.qty, place_order=not args.no_order,
                account_ok=args.account_ok)
        )
    except ModuleNotFoundError:
        print("ib_insync is not installed. Install deps first:\n"
              "    pip install -r requirements.txt")
        return 1
    except Exception as exc:  # noqa: BLE001 — smoke test: surface any failure plainly
        print(f"\n✗ IB smoke test failed: {type(exc).__name__}: {exc}")
        print("  Is IB Gateway/TWS running with the API enabled on the configured port?")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
