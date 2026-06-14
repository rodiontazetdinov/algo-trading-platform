"""Fetch real daily OHLCV history and cache it as CSV under data/.

    PYTHONPATH=src python scripts/fetch_data.py

Used to seed the demo backtest with real market data (no API key needed).
Data source: Yahoo Finance chart endpoint. Re-run to refresh.
"""
from __future__ import annotations

import csv
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SYMBOLS = ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "SPY"]
RANGE = "2y"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def fetch(symbol: str) -> list[list]:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        f"?range={RANGE}&interval=1d"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    result = payload["chart"]["result"][0]
    ts = result["timestamp"]
    q = result["indicators"]["quote"][0]
    rows = []
    for i, t in enumerate(ts):
        o, h, low, c, v = q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i]
        if None in (o, h, low, c):
            continue
        date = datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")
        rows.append([date, round(o, 4), round(h, 4), round(low, 4), round(c, 4), int(v or 0)])
    return rows


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    for symbol in SYMBOLS:
        rows = fetch(symbol)
        out = DATA_DIR / f"{symbol}.csv"
        with out.open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
            w.writerows(rows)
        print(f"{symbol}: {len(rows)} bars -> {out}")


if __name__ == "__main__":
    main()
