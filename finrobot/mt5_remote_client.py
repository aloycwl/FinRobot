from __future__ import annotations

import json
import requests


class MT5RemoteClient:
    def __init__(self, host: str, port: int = 8642):
        self.endpoint = f"http://{host}:{port}"
    
    def place_order(self, symbol: str, side: str, lot: float, deviation: int = 20):
        payload = {
            "action": "place_order",
            "symbol": symbol,
            "side": side,
            "lot": lot,
            "deviation": deviation
        }
        
        response = requests.post(self.endpoint, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()


def get_remote_client():
    from .config import Config
    return MT5RemoteClient(Config.MT5_REMOTE_HOST, Config.MT5_REMOTE_PORT)
