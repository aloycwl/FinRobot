"""
MT5 Remote Execution Agent
Run this on WINDOWS machine with MT5 installed.
Linux daemon will send trade commands over HTTP to this agent.
"""
from __future__ import annotations

import json
import argparse
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from dataclasses import dataclass

import MetaTrader5 as mt5


@dataclass
class MT5Credentials:
    login: int
    password: str
    server: str


def connect(credentials: MT5Credentials):
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    if not mt5.login(credentials.login, password=credentials.password, server=credentials.server):
        code = mt5.last_error()
        mt5.shutdown()
        raise RuntimeError(f"MT5 login failed: {code}")
    return mt5


def place_market_order(mt5_instance, symbol: str, side: str, lot: float, deviation: int = 20):
    tick = mt5_instance.symbol_info_tick(symbol)
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
    
    result = mt5_instance.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(f"Order failed: {result}")
    
    return {
        "success": True,
        "ticket": result.order,
        "price": result.price,
        "volume": result.volume,
        "comment": result.comment,
        "retcode": result.retcode
    }


class MT5RequestHandler(BaseHTTPRequestHandler):
    credentials = None
    
    def _send_response(self, status_code, data):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            request = json.loads(post_data)
            
            if request.get("action") == "place_order":
                mt5_instance = connect(self.credentials)
                result = place_market_order(
                    mt5_instance,
                    request["symbol"],
                    request["side"],
                    request["lot"],
                    request.get("deviation", 20)
                )
                mt5.shutdown()
                self._send_response(200, result)
                
        except Exception as e:
            self._send_response(400, {"success": False, "error": str(e)})


def main():
    parser = argparse.ArgumentParser(description="MT5 Remote Execution Agent")
    parser.add_argument("--login", required=True, type=int, help="MT5 account login number")
    parser.add_argument("--password", required=True, help="MT5 account password")
    parser.add_argument("--server", required=True, help="MT5 server name")
    parser.add_argument("--port", type=int, default=8642, help="HTTP listen port")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP listen address")
    
    args = parser.parse_args()
    
    MT5RequestHandler.credentials = MT5Credentials(
        login=args.login,
        password=args.password,
        server=args.server
    )
    
    server = HTTPServer((args.host, args.port), MT5RequestHandler)
    print(f"✅ MT5 Remote Agent running on http://{args.host}:{args.port}")
    print("   Keep this window open on your Windows machine")
    print("   Linux daemon will send orders to this endpoint automatically")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down agent")
        server.shutdown()


if __name__ == "__main__":
    main()
