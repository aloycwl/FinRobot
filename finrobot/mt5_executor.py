from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MT5Credentials:
    login: int
    password: str
    server: str


def connect(credentials: MT5Credentials):
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    if not mt5.login(credentials.login, password=credentials.password, server=credentials.server):
        code = mt5.last_error()
        mt5.shutdown()
        raise RuntimeError(f"MT5 login failed: {code}")
    return mt5


def place_market_order(mt5, symbol: str, side: str, lot: float, deviation: int = 20):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"Symbol unavailable: {symbol}")
    order_type = mt5.ORDER_TYPE_BUY if side.lower() == "buy" else mt5.ORDER_TYPE_SELL
    price = tick.ask if side.lower() == "buy" else tick.bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "deviation": deviation,
        "magic": 20260428,
        "comment": "finrobot-auto",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(f"Order failed: {result}")
    return result


def shutdown(mt5):
    mt5.shutdown()
