from app.core.types import Order, Side
from app.oms.manager import OMS


def test_fill_updates_position():
    oms = OMS()
    o = Order("AAPL", Side.BUY, 100)
    oms.register(o)
    oms.on_fill(o, 100, 150.0)
    pos = oms.get_position("AAPL")
    assert pos.quantity == 100
    assert pos.avg_price == 150.0


def test_engine_run_once_mock():
    import asyncio
    from app.config import get_settings
    from app.engine import TradingEngine

    async def _run():
        eng = TradingEngine(get_settings())
        await eng.start()
        await eng.process_symbol("AAPL")
        await eng.stop()

    asyncio.run(_run())
