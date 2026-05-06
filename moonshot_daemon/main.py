"""
Moonshot Daemon - 24/7 Automated Trading Main Loop
Runs continuously, checks for opportunities every 60 seconds
"""

import sys
import time
import json
import logging
import signal
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from moonshot_daemon.hyperliquid_ws_client import (
    HyperliquidWebSocketClient, PriceUpdate, TradeData
)
from moonshot_daemon.state_manager import StateManager, PositionState, TradeRecord

# Setup logging
log_dir = Path("moonshot_logs")
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "moonshot_daemon.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MoonshotDaemon:
    """
    24/7 Automated trading daemon
    - Maintains WebSocket connection to Hyperliquid
    - Checks for trading opportunities every 60 seconds
    - Manages positions and state
    - Logs all activity
    """
    
    def __init__(
        self,
        initial_balance: float = 100.0,
        symbols: List[str] = None,
        check_interval: float = 60.0,  # Check every 60 seconds
        paper_trading: bool = True
    ):
        self.initial_balance = initial_balance
        self.symbols = symbols or ["BTC-PERP", "ETH-PERP", "SOL-PERP"]
        self.check_interval = check_interval
        self.paper_trading = paper_trading
        
        # Components
        self.ws_client: Optional[HyperliquidWebSocketClient] = None
        self.state_manager: Optional[StateManager] = None
        
        # State
        self.running = False
        self.last_check_time = 0
        self.iteration_count = 0
        
        # Threads
        self.main_thread: Optional[threading.Thread] = None
        
        # Price cache
        self.current_prices: Dict[str, float] = {}
        self.price_history: Dict[str, List[Dict]] = {s: [] for s in self.symbols}
        
        logger.info("=" * 70)
        logger.info("🚀 MOONSHOT DAEMON INITIALIZED")
        logger.info("=" * 70)
        logger.info(f"💰 Initial Balance: {initial_balance} USDT")
        logger.info(f"📊 Symbols: {', '.join(self.symbols)}")
        logger.info(f"⏱️  Check Interval: {check_interval}s")
        logger.info(f"🧪 Paper Trading: {paper_trading}")
        logger.info("=" * 70)
    
    def initialize(self):
        """Initialize all components"""
        logger.info("Initializing components...")
        
        # Initialize state manager
        self.state_manager = StateManager(
            data_dir="moonshot_data",
            save_interval=30.0
        )
        self.state_manager.start_auto_save()
        
        # Initialize WebSocket client
        self.ws_client = HyperliquidWebSocketClient()
        
        # Set up callbacks
        self.ws_client.on_price_update = self._on_price_update
        self.ws_client.on_trade = self._on_trade
        self.ws_client.on_connect = self._on_ws_connect
        self.ws_client.on_disconnect = self._on_ws_disconnect
        
        # Subscribe to data
        self.ws_client.subscribe_all_mids()
        for symbol in self.symbols:
            coin = symbol.replace("-PERP", "")
            self.ws_client.subscribe_trades(coin)
        
        logger.info("✅ All components initialized")
    
    def _on_price_update(self, update: PriceUpdate):
        """Handle price update from WebSocket"""
        self.current_prices[update.coin] = update.mid
        
        # Store in history
        if update.coin not in self.price_history:
            self.price_history[update.coin] = []
        
        self.price_history[update.coin].append({
            'timestamp': time.time(),
            'price': update.mid,
            'bid': update.bid,
            'ask': update.ask
        })
        
        # Keep last 1000 prices
        if len(self.price_history[update.coin]) > 1000:
            self.price_history[update.coin] = self.price_history[update.coin][-1000:]
        
        logger.debug(f"Price update: {update.coin} = ${update.mid:,.2f}")
    
    def _on_trade(self, trade: TradeData):
        """Handle trade from WebSocket"""
        logger.debug(f"Trade: {trade.side} {trade.sz} {trade.coin} @ ${trade.px:,.2f}")
    
    def _on_ws_connect(self):
        """Handle WebSocket connection"""
        logger.info("✅ WebSocket connected to Hyperliquid")
    
    def _on_ws_disconnect(self):
        """Handle WebSocket disconnection"""
        logger.warning("⚠️ WebSocket disconnected from Hyperliquid")
    
    def check_opportunities(self):
        """
        Main trading logic - check for opportunities
        This is called every check_interval seconds
        """
        logger.info(f"🔍 Checking for trading opportunities (iteration {self.iteration_count})")
        
        # Check if we have price data
        if not self.current_prices:
            logger.warning("No price data available yet, skipping check")
            return
        
        # Log current prices
        price_str = ", ".join([f"{k}=${v:,.2f}" for k, v in list(self.current_prices.items())[:3]])
        logger.info(f"Current prices: {price_str}")
        
        # TODO: Implement your trading strategies here
        # This is where you would:
        # 1. Calculate technical indicators
        # 2. Check for entry/exit signals
        # 3. Execute trades
        
        # For now, just log that we're monitoring
        logger.info("✅ Opportunity check complete - monitoring continues")
    
    def run(self):
        """Main daemon loop"""
        logger.info("🚀 Starting Moonshot Daemon main loop")
        
        self.running = True
        self.iteration_count = 0
        
        # Start WebSocket client
        if self.ws_client:
            self.ws_client.start()
            
            # Wait for initial connection
            logger.info("⏳ Waiting for WebSocket connection...")
            timeout = 10
            start = time.time()
            while not self.ws_client.connected and time.time() - start < timeout:
                time.sleep(0.1)
            
            if not self.ws_client.connected:
                logger.error("❌ Failed to connect to Hyperliquid within timeout")
                self.running = False
                return
            
            logger.info("✅ WebSocket connected, starting main loop")
        
        # Main loop
        try:
            while self.running:
                self.iteration_count += 1
                loop_start = time.time()
                
                # Check for opportunities
                try:
                    self.check_opportunities()
                except Exception as e:
                    logger.error(f"Error in opportunity check: {e}")
                
                # Calculate sleep time
                elapsed = time.time() - loop_start
                sleep_time = max(0, self.check_interval - elapsed)
                
                if sleep_time > 0:
                    logger.debug(f"Sleeping for {sleep_time:.1f}s")
                    
                    # Sleep in small increments to allow quick shutdown
                    slept = 0
                    while slept < sleep_time and self.running:
                        time.sleep(min(1, sleep_time - slept))
                        slept += 1
                
        except KeyboardInterrupt:
            logger.info("⛔ Interrupted by user")
        except Exception as e:
            logger.error(f"❌ Fatal error in main loop: {e}")
        finally:
            self.running = False
            logger.info("🏁 Moonshot Daemon main loop stopped")
    
    def stop(self):
        """Stop the daemon"""
        logger.info("⛔ Stopping Moonshot Daemon...")
        self.running = False
        
        # Stop WebSocket client
        if self.ws_client:
            self.ws_client.stop()
        
        # Stop state manager
        if self.state_manager:
            self.state_manager.stop_auto_save()
        
        logger.info("✅ Moonshot Daemon stopped")
    
    def get_status(self) -> Dict:
        """Get current daemon status"""
        return {
            'running': self.running,
            'iteration_count': self.iteration_count,
            'websocket_connected': self.ws_client.connected if self.ws_client else False,
            'prices_available': len(self.current_prices),
            'current_prices': self.current_prices,
            'last_check': self.last_check_time,
            'timestamp': time.time()
        }


# Entry point
def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Moonshot 24/7 Trading Daemon')
    parser.add_argument('--balance', type=float, default=100.0, help='Initial balance')
    parser.add_argument('--interval', type=float, default=60.0, help='Check interval in seconds')
    parser.add_argument('--symbols', nargs='+', default=['BTC-PERP', 'ETH-PERP', 'SOL-PERP'])
    args = parser.parse_args()
    
    # Create and run daemon
    daemon = MoonshotDaemon(
        initial_balance=args.balance,
        symbols=args.symbols,
        check_interval=args.interval
    )
    
    # Set up signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        daemon.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        daemon.initialize()
        daemon.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        daemon.stop()
        raise


if __name__ == "__main__":
    main()