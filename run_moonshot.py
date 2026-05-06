#!/usr/bin/env python3
"""
🚀 HYPERLIQUID MOONSHOT ENGINE - MAIN LAUNCHER

Run this script to start the aggressive crypto trading system.

Usage:
    python run_moonshot.py [mode]

Modes:
    demo      - Run a quick 5-minute demo (default)
    live      - Start the full trading engine
    backtest  - Run backtest on historical data
    status    - Check current system status

Examples:
    python run_moonshot.py demo
    python run_moonshot.py live
    python run_moonshot.py --duration 60  # Run for 60 minutes
"""

import sys
import time
import argparse
import logging
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('hyperliquid_moonshot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print the startup banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     🚀 HYPERLIQUID MOONSHOT ENGINE 🚀                          ║
    ║                                                               ║
    ║     💰 Growing 100 USDT → 1000+ USDT by ANY MEANS              ║
    ║     ⚡ AGGRESSIVE CRYPTO SCALPING SYSTEM                        ║
    ║     🔥 YOLO MODE ACTIVATED                                     ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def run_demo(duration_minutes: float = 5.0):
    """
    Run a quick demo of the Moonshot Engine
    
    Args:
        duration_minutes: How long to run the demo
    """
    print_banner()
    
    logger.info("🎮 Starting DEMO mode")
    logger.info(f"⏱️  Duration: {duration_minutes} minutes")
    logger.info("-" * 70)
    
    try:
        from hyperliquid_trader import HyperliquidMoonshotTrader
        
        # Create trader
        trader = HyperliquidMoonshotTrader(
            initial_balance=100.0,
            symbols=["BTC-PERP", "ETH-PERP", "SOL-PERP"],
            max_open_positions=3,
            check_interval=3.0
        )
        
        # Start trading
        trader.start()
        
        # Let it run
        logger.info(f"\n⏳ Running for {duration_minutes} minutes...")
        logger.info("Press Ctrl+C to stop early\n")
        
        try:
            time.sleep(duration_minutes * 60)
        except KeyboardInterrupt:
            logger.info("\n⛔ Interrupted by user")
        
        # Stop
        trader.stop()
        
        # Final stats
        final_stats = trader.engine.get_stats_summary()
        
        print("\n" + "=" * 70)
        print("🎯 DEMO COMPLETE - FINAL RESULTS")
        print("=" * 70)
        print(f"💰 Starting Balance: 100.00 USDT")
        print(f"💰 Final Balance: {final_stats['balance']:.2f} USDT")
        print(f"📈 Total Return: {final_stats['total_return_pct']:+.1f}%")
        print(f"🔄 Total Trades: {final_stats['total_trades']}")
        print(f"🏆 Win Rate: {final_stats['win_rate']:.1f}%")
        print(f"📉 Max Drawdown: {final_stats['max_drawdown_pct']:.1f}%")
        print("=" * 70)
        
        if final_stats['balance'] > 100:
            profit = final_stats['balance'] - 100
            print(f"🎉 PROFIT: +{profit:.2f} USDT (+{profit:.1f}%)")
        else:
            loss = 100 - final_stats['balance']
            print(f"⚠️  LOSS: -{loss:.2f} USDT (-{loss:.1f}%)")
        
        print("=" * 70)
        
    except Exception as e:
        logger.error(f"Error in demo: {e}")
        import traceback
        traceback.print_exc()


def run_live():
    """Run the live trading engine"""
    print_banner()
    
    logger.info("🔴 Starting LIVE trading mode")
    logger.info("⚠️  This will trade with REAL or PAPER account")
    logger.info("-" * 70)
    
    # TODO: Implement live trading mode
    logger.info("Live mode not yet implemented. Use demo mode for now.")


def run_backtest():
    """Run backtest on historical data"""
    print_banner()
    
    logger.info("📊 Starting BACKTEST mode")
    logger.info("Testing strategies on historical data")
    logger.info("-" * 70)
    
    # TODO: Implement backtest mode
    logger.info("Backtest mode not yet implemented.")


def show_status():
    """Show current system status"""
    print_banner()
    
    logger.info("📈 System Status")
    logger.info("-" * 70)
    
    # Check for state files
    import os
    state_files = [
        "hyperliquid_state.json",
        "hyperliquid_moonshot.log"
    ]
    
    for filename in state_files:
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            logger.info(f"✅ {filename}: {size:,} bytes")
        else:
            logger.info(f"❌ {filename}: Not found")
    
    logger.info("-" * 70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Hyperliquid Moonshot Engine - Aggressive Crypto Trading',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_moonshot.py demo              # Run 5-minute demo
  python run_moonshot.py demo --duration 10  # Run 10-minute demo
  python run_moonshot.py status              # Check system status
        """
    )
    
    parser.add_argument(
        'mode',
        nargs='?',
        default='demo',
        choices=['demo', 'live', 'backtest', 'status'],
        help='Operating mode (default: demo)'
    )
    
    parser.add_argument(
        '--duration',
        type=float,
        default=5.0,
        help='Demo duration in minutes (default: 5.0)'
    )
    
    parser.add_argument(
        '--balance',
        type=float,
        default=100.0,
        help='Initial balance in USDT (default: 100.0)'
    )
    
    args = parser.parse_args()
    
    # Route to appropriate function
    if args.mode == 'demo':
        run_demo(duration_minutes=args.duration)
    elif args.mode == 'live':
        run_live()
    elif args.mode == 'backtest':
        run_backtest()
    elif args.mode == 'status':
        show_status()


if __name__ == "__main__":
    main()