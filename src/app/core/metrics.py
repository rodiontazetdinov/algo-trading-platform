"""Prometheus metrics exposed by the platform."""
from prometheus_client import Counter, Gauge, Histogram

SIGNALS_GENERATED = Counter(
    "signals_generated_total", "Number of trading signals generated", ["strategy", "side"]
)
ORDERS_SUBMITTED = Counter(
    "orders_submitted_total", "Number of orders submitted", ["symbol", "side"]
)
ORDERS_REJECTED = Counter(
    "orders_rejected_total", "Number of orders rejected by risk", ["reason"]
)
OPEN_POSITIONS = Gauge("open_positions", "Current number of open positions")
MARKET_DATA_LATENCY = Histogram(
    "market_data_latency_seconds", "Latency of market data tick handling"
)
