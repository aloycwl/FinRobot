from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CTraderCredentials:
    client_id: str
    client_secret: str
    access_token: str
    account_id: int
    host: str = "api.ctrader.com"


def connect(credentials: CTraderCredentials):
    import ctrader_open_api
    from ctrader_open_api import Client, Protobuf, TcpProtocol, Auth, EndPoints

    client = Client(endPoint=EndPoints.PROTOBUF_ENDPOINT_HOST, protocol=TcpProtocol)

    # Authenticate with cTrader Open API
    auth_response = client.send(Auth.OAuth2LoginRequest(
        clientId=credentials.client_id,
        clientSecret=credentials.client_secret,
        accessToken=credentials.access_token
    ))

    if not auth_response.success:
        raise RuntimeError(f"cTrader authentication failed: {auth_response.error}")

    # Select trading account
    account_response = client.send(Auth.TraderAccountRequest(
        accountId=credentials.account_id
    ))

    if not account_response.success:
        client.close()
        raise RuntimeError(f"cTrader account selection failed: {account_response.error}")

    return client


def place_market_order(ctrader_client, symbol: str, side: str, lot: float, deviation: int = 20):
    from ctrader_open_api import Messages

    # Get symbol info first
    symbol_info = ctrader_client.send(Messages.SymbolByNameRequest(name=symbol))

    if not symbol_info.success:
        raise RuntimeError(f"Symbol unavailable: {symbol}")

    symbol_id = symbol_info.payload.symbol.id
    digits = symbol_info.payload.symbol.digits

    # Get latest tick price
    tick = ctrader_client.send(Messages.TickRequest(symbolId=symbol_id))

    if not tick.success:
        raise RuntimeError(f"Could not retrieve price for {symbol}")

    if side.lower() == "buy":
        order_side = Messages.OrderSide.BUY
        price = tick.payload.ask
    else:
        order_side = Messages.OrderSide.SELL
        price = tick.payload.bid

    # Calculate volume (cTrader uses units not lots: 1 lot = 100000 units)
    volume = int(lot * 100000)

    # Send market order
    order_request = Messages.NewOrderRequest(
        symbolId=symbol_id,
        orderSide=order_side,
        orderType=Messages.OrderType.MARKET,
        volume=volume,
        price=price,
        slippageInPips=deviation,
        comment="finrobot-auto",
        magicNumber=20260428,
        timeInForce=Messages.TimeInForce.GOOD_TILL_CANCEL
    )

    result = ctrader_client.send(order_request)

    if not result.success:
        raise RuntimeError(f"Order failed: {result.error}")

    return result.payload


def shutdown(ctrader_client):
    ctrader_client.close()
