"""
Hyperliquid WebSocket Client
Real-time data feed from Hyperliquid API
"""

import json
import time
import logging
import threading
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class TradeData:
    """Trade data from Hyperliquid"""
    coin: str
    side: str  # "B" for buy, "A" for sell
    px: float  # price
    sz: float  # size
    time: int  # timestamp
    hash: str


@dataclass
class PriceUpdate:
    """Aggregated price update"""
    coin: str
    bid: float
    ask: float
    mid: float
    last_price: float
    volume_24h: float
    timestamp: float


class HyperliquidWebSocketClient:
    """
    WebSocket client for Hyperliquid API
    Connects to real-time data streams
    """
    
    def __init__(
        self,
        ws_url: str = "wss://api.hyperliquid.xyz/ws",
        ping_interval: float = 20.0,
        reconnect_delay: float = 5.0,
        max_reconnect_attempts: int = 10
    ):
        self.ws_url = ws_url
        self.ping_interval = ping_interval
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        
        # WebSocket connection
        self.ws = None
        self.ws_thread: Optional[threading.Thread] = None
        self.ping_thread: Optional[threading.Thread] = None
        
        # State
        self.running = False
        self.connected = False
        self.reconnect_count = 0
        self.last_pong_time = 0
        
        # Subscriptions
        self.subscriptions: List[Dict] = []
        
        # Data storage
        self.price_data: Dict[str, PriceUpdate] = {}
        self.recent_trades: Dict[str, deque] = {}  # coin -> deque of TradeData
        self.ohlcv_data: Dict[str, Dict[str, deque]] = {}  # coin -> timeframe -> deque
        
        # Callbacks
        self.on_price_update: Optional[Callable[[PriceUpdate], None]] = None
        self.on_trade: Optional[Callable[[TradeData], None]] = None
        self.on_connect: Optional[Callable[[], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None
        
        logger.info(f"HyperliquidWebSocketClient initialized")
        logger.info(f"  WS URL: {ws_url}")
        logger.info(f"  Ping interval: {ping_interval}s")
        logger.info(f"  Max reconnects: {max_reconnect_attempts}")
    
    def subscribe_all_mids(self):
        """Subscribe to all mid prices"""
        sub = {"type": "allMids"}
        self.subscriptions.append(sub)
        if self.connected and self.ws:
            self.ws.send(json.dumps({"method": "subscribe", "subscription": sub}))
        logger.info("Subscribed to allMids")
    
    def subscribe_trades(self, coin: str):
        """Subscribe to trades for a specific coin"""
        sub = {"type": "trades", "coin": coin}
        self.subscriptions.append(sub)
        if self.connected and self.ws:
            self.ws.send(json.dumps({"method": "subscribe", "subscription": sub}))
        logger.info(f"Subscribed to trades for {coin}")
    
    def subscribe_l2_book(self, coin: str):
        """Subscribe to L2 order book for a coin"""
        sub = {"type": "l2Book", "coin": coin}
        self.subscriptions.append(sub)
        if self.connected and self.ws:
            self.ws.send(json.dumps({"method": "subscribe", "subscription": sub}))
        logger.info(f"Subscribed to L2 book for {coin}")
    
    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        logger.info("✅ WebSocket connected to Hyperliquid")
        self.connected = True
        self.reconnect_count = 0
        self.last_pong_time = time.time()
        
        # Resubscribe to all previous subscriptions
        for sub in self.subscriptions:
            ws.send(json.dumps({"method": "subscribe", "subscription": sub}))
        
        if self.on_connect:
            try:
                self.on_connect()
            except Exception as e:
                logger.error(f"Error in on_connect callback: {e}")
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            
            # Handle different message types
            channel = data.get("channel")
            
            if channel == "allMids":
                self._process_all_mids(data.get("data", {}))
            elif channel == "trades":
                self._process_trades(data.get("data", []))
            elif channel == "l2Book":
                self._process_l2_book(data.get("data", {}))
            elif channel == "pong":
                self.last_pong_time = time.time()
            else:
                # Log unknown channels for debugging
                logger.debug(f"Unknown channel: {channel}, data: {data}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}, raw: {message[:200]}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def _process_all_mids(self, data: Dict):
        """Process allMids update"""
        # Handle nested structure: {"mids": {"BTC": 50000, "ETH": 3000}}
        if "mids" in data and isinstance(data["mids"], dict):
            prices = data["mids"]
        else:
            prices = data
            
        for coin, mid_price in prices.items():
            try:
                # Skip if mid_price is not a simple number (could be dict in some formats)
                if isinstance(mid_price, dict):
                    # Try to extract price from common fields
                    if "mid" in mid_price:
                        price = float(mid_price["mid"])
                    elif "price" in mid_price:
                        price = float(mid_price["price"])
                    else:
                        logger.debug(f"Skipping {coin}: unexpected nested structure")
                        continue
                else:
                    price = float(mid_price)
                
                # Create or update price data
                if coin not in self.price_data:
                    self.price_data[coin] = PriceUpdate(
                        coin=coin,
                        bid=price * 0.9995,
                        ask=price * 1.0005,
                        mid=price,
                        last_price=price,
                        volume_24h=0.0,
                        timestamp=time.time()
                    )
                else:
                    update = self.price_data[coin]
                    update.mid = price
                    update.bid = price * 0.9995
                    update.ask = price * 1.0005
                    update.last_price = price
                    update.timestamp = time.time()
                
                # Trigger callback
                if self.on_price_update:
                    try:
                        self.on_price_update(self.price_data[coin])
                    except Exception as e:
                        logger.error(f"Error in price update callback: {e}")
                        
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing mid price for {coin}: {e}")
    
    def _process_trades(self, trades: List[Dict]):
        """Process trades update"""
        for trade_data in trades:
            try:
                trade = TradeData(
                    coin=trade_data.get("coin", "UNKNOWN"),
                    side=trade_data.get("side", "B"),
                    px=float(trade_data.get("px", 0)),
                    sz=float(trade_data.get("sz", 0)),
                    time=int(trade_data.get("time", 0)),
                    hash=trade_data.get("hash", "")
                )
                
                # Store in recent trades
                if trade.coin not in self.recent_trades:
                    self.recent_trades[trade.coin] = deque(maxlen=1000)
                self.recent_trades[trade.coin].append(trade)
                
                # Trigger callback
                if self.on_trade:
                    try:
                        self.on_trade(trade)
                    except Exception as e:
                        logger.error(f"Error in trade callback: {e}")
                        
            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Error parsing trade data: {e}, raw: {trade_data}")
    
    def _process_l2_book(self, data: Dict):
        """Process L2 order book update"""
        # TODO: Implement order book processing if needed
        pass
    
    def _on_error(self, ws, error):
        """Handle WebSocket error"""
        logger.error(f"❌ WebSocket error: {error}")
        self.connected = False
        
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        logger.warning(f"⚠️ WebSocket connection closed: {close_status_code} - {close_msg}")
        self.connected = False
        
        if self.on_disconnect:
            try:
                self.on_disconnect()
            except Exception as e:
                logger.error(f"Error in on_disconnect callback: {e}")
        
        # Attempt reconnection if running
        if self.running and self.reconnect_count < self.max_reconnect_attempts:
            self.reconnect_count += 1
            logger.info(f"🔄 Reconnecting in {self.reconnect_delay}s (attempt {self.reconnect_count}/{self.max_reconnect_attempts})")
            time.sleep(self.reconnect_delay)
            self._connect()
        elif self.reconnect_count >= self.max_reconnect_attempts:
            logger.error(f"❌ Max reconnection attempts ({self.max_reconnect_attempts}) reached. Stopping.")
            self.stop()
    
    def _send_ping(self):
        """Send periodic ping to keep connection alive"""
        while self.running:
            try:
                if self.connected and self.ws:
                    self.ws.send(json.dumps({"method": "ping"}))
                    logger.debug("Ping sent")
                
                # Check for pong timeout
                if self.connected and (time.time() - self.last_pong_time) > (self.ping_interval * 3):
                    logger.warning("⚠️ Pong timeout detected, connection may be stale")
                    # Connection will be closed by WebSocket timeout and trigger reconnect
                    
            except Exception as e:
                logger.error(f"Error in ping thread: {e}")
            
            time.sleep(self.ping_interval)
    
    def _connect(self):
        """Initialize and connect WebSocket"""
        try:
            import websocket
            
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Run in separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            self.ws_thread.start()
            
            logger.info(f"🔗 WebSocket connection initiated to {self.ws_url}")
            
        except ImportError:
            logger.error("❌ websocket-client library not installed. Run: pip install websocket-client")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to connect WebSocket: {e}")
            raise
    
    def start(self):
        """Start the WebSocket client"""
        if self.running:
            logger.warning("WebSocket client is already running")
            return
        
        self.running = True
        self.reconnect_count = 0
        
        # Start ping thread
        self.ping_thread = threading.Thread(target=self._send_ping, daemon=True)
        self.ping_thread.start()
        
        # Connect
        self._connect()
        
        logger.info("✅ Hyperliquid WebSocket client started")
    
    def stop(self):
        """Stop the WebSocket client"""
        if not self.running:
            return
        
        logger.info("⛔ Stopping WebSocket client...")
        self.running = False
        self.connected = False
        
        # Close WebSocket
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        
        # Wait for threads
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5)
        
        if self.ping_thread and self.ping_thread.is_alive():
            self.ping_thread.join(timeout=5)
        
        logger.info("✅ WebSocket client stopped")
    
    def get_current_price(self, coin: str) -> Optional[float]:
        """Get current mid price for a coin"""
        if coin in self.price_data:
            return self.price_data[coin].mid
        return None
    
    def get_all_prices(self) -> Dict[str, float]:
        """Get all current prices"""
        return {coin: data.mid for coin, data in self.price_data.items()}


# Convenience function
def create_websocket_client(
    on_price_update: Optional[Callable[[PriceUpdate], None]] = None,
    on_trade: Optional[Callable[[TradeData], None]] = None
) -> HyperliquidWebSocketClient:
    """
    Create and return a configured WebSocket client
    
    Example:
        client = create_websocket_client()
        client.subscribe_all_mids()
        client.start()
        
        # Get prices
        price = client.get_current_price("ETH")
        
        # Stop
        client.stop()
    """
    client = HyperliquidWebSocketClient()
    
    if on_price_update:
        client.on_price_update = on_price_update
    
    if on_trade:
        client.on_trade = on_trade
    
    return client


if __name__ == "__main__":
    # Test the WebSocket client
    import signal
    
    def signal_handler(sig, frame):
        print("\nStopping...")
        client.stop()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🧪 Testing Hyperliquid WebSocket Client")
    print("=" * 50)
    
    # Create client
    client = create_websocket_client()
    
    # Set up callbacks
    def on_price(update: PriceUpdate):
        print(f"💰 {update.coin}: ${update.mid:,.2f}")
    
    def on_trade(trade: TradeData):
        side = "🟢 BUY" if trade.side == "B" else "🔴 SELL"
        print(f"📊 {side} {trade.sz:.4f} {trade.coin} @ ${trade.px:,.2f}")
    
    client.on_price_update = on_price
    client.on_trade = on_trade
    
    # Subscribe to data
    client.subscribe_all_mids()
    client.subscribe_trades("ETH")
    client.subscribe_trades("BTC")
    
    # Start
    print("🔗 Connecting to Hyperliquid...")
    client.start()
    
    print("✅ Connected! Press Ctrl+C to stop")
    print("=" * 50)
    
    # Keep running
    while client.running:
        time.sleep(1)