from app.core.types import Order, Side, Position
from app.risk.manager import RiskManager, RiskLimits


def test_rejects_oversize_order():
    rm = RiskManager(RiskLimits(max_order_qty=100))
    o = Order("AAPL", Side.BUY, 200)
    assert rm.check(o, 50.0, None).approved is False


def test_rejects_position_limit():
    rm = RiskManager(RiskLimits(max_position_usd=1000))
    o = Order("AAPL", Side.BUY, 100)
    # 100 * 50 = 5000 > 1000
    d = rm.check(o, 50.0, Position("AAPL"))
    assert d.approved is False
    assert d.reason == "max_position_usd"


def test_daily_loss_blocks():
    rm = RiskManager(RiskLimits(max_daily_loss_usd=500))
    rm.register_pnl(-600)
    o = Order("AAPL", Side.BUY, 1)
    assert rm.check(o, 10.0, None).approved is False


def test_approves_valid_order():
    rm = RiskManager(RiskLimits(max_position_usd=100000, max_order_qty=500))
    o = Order("AAPL", Side.BUY, 10)
    assert rm.check(o, 50.0, None).approved is True
