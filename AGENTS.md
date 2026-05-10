# FinRobot - Agent Documentation

## Project Overview

**FinRobot** is a self-improving autonomous algorithmic trading system with a closed feedback loop using Opencode. It trades XAUUSD (Gold) and Crypto (BTC, ETH, SOL) using multiple strategies with automatic optimization.

## Project Structure

```
FinRobot/
├── moonshot/                    # Moonshot Crypto Trading System (Daemon 2 - PRIMARY)
│   ├── daemon/                  # 24/7 trading daemon core
│   │   ├── main.py              # Main loop, strategy orchestration, WebSocket
│   │   ├── hyperliquid_ws_client.py  # Real-time price feed from Hyperliquid
│   │   ├── state_manager.py     # Position tracking, trade history, persistence
│   │   └── self_improvement.py  # Strategy performance tracking, optimization, opencode feedback, strategy lab
│   ├── strategies/              # Trading strategies & execution
│   │   ├── strategies.py        # Signal generators (10 strategies - see below)
│   │   └── executor.py          # Paper trading engine
│   ├── trader.py                # Legacy trader (run_moonshot.py demo mode)
│   └── monitor.py               # Live monitoring dashboard
├── finrobot/                    # FinRobot Core Package (Daemon 1 - XAUUSD)
│   ├── strategies/              # XAUUSD strategies (grid, martingale, hft, etc.)
│   ├── execution/               # MT5/cTrader execution adapters
│   ├── optimization/            # Feedback loop, genetic optimizer, opencode integration
│   └── utils/                   # Config, data sources, indicators, logging
├── scripts/                     # All management scripts
│   ├── run_daemon.py            # Moonshot daemon launcher (systemd entry point)
│   ├── moonshot_health_check.py # Watchdog: monitors & restarts daemon
│   ├── run_moonshot.py          # Demo mode launcher
│   ├── daemon_service.py        # XAUUSD daemon (Daemon 1)
│   ├── start_daemon.sh          # XAUUSD daemon startup script
│   └── ...                      # Backtest, health, test scripts
├── logs/                        # ALL log files
│   └── daemon.log               # Main trading log (tail -f this)
├── state/                       # ALL runtime state
│   ├── moonshot/                # Moonshot state (positions, trades, performance)
│   └── daemon1/                 # XAUUSD daemon state
├── data/                        # Market data (CSV, cache)
├── backups/                     # Strategy backups
├── docs/                        # Documentation
└── tests/                       # Test suite
```

## Core Architecture - Moonshot Daemon (Daemon 2)

### How It Works
1. **WebSocket Connection**: Connects to Hyperliquid API for real-time BTC/ETH/SOL prices
2. **Candle Building**: Constructs 60-second OHLCV candles from live tick data
3. **Signal Generation**: 10 strategies evaluate every 60 seconds (best signal per coin selected):
   - **QuickMomentum**: EMA 8/21 crosses with RSI filter
   - **RsiDivergence**: RSI overbought/oversold mean reversion
   - **MicroTrend**: Momentum-based trend following
   - **SmartMoneyConcepts**: Order blocks, fair value gaps, institutional flow
   - **FibonacciRetracement**: Key Fib levels (0.382, 0.5, 0.618, 0.786) as S/R
   - **MACDStrategy**: MACD divergence & crossover with RSI/EMA confirmation
   - **VWAPStrategy**: VWAP as dynamic S/R with deviation bands
   - **AggressiveCryptoScalper**: EMA + volume scalping
   - **MeanReversionBandit**: Bollinger Band + RSI reversal
   - **AggressiveADXScalper**: ADX trend strength + EMA direction
4. **Multi-Signal Execution**: Opens up to `max_open_positions - current_positions` trades per iteration (1 per coin)
5. **Position Management**: SL (0.5%), TP (1%), trailing stop (0.4%), stale timeout (10min), max duration (30min)
6. **Self-Improvement**: Tracks per-strategy performance, adjusts parameters every hour
7. **Strategy Lab**: Auto-disables persistently losing strategies (WR<30%, avg_pnl<-0.3%), re-enables after 2hr cooldown
8. **Opencode Feedback**: Actually invokes opencode via subprocess when return < -1% or WR < 50% or DD > 3%

### Key Parameters
- **Initial Balance**: 100 USDT (paper trading)
- **Max Open Positions**: 5
- **Max Leverage**: 5x
- **Risk Per Trade**: 2% of balance
- **Min Confidence**: 0.45 (45%)
- **SL**: 0.5% | **TP**: 1.0% | **Trail**: 0.4%
- **Stale Timeout**: 600s (10min) | **Max Duration**: 1800s (30min)
- **Signal Cooldown**: 60s per coin per strategy

## How to Monitor

```bash
# Watch live moonshot trading
tail -f logs/daemon.log

# Check daemon status
systemctl --user status moonshot-daemon.service

# Run health check
python3 scripts/moonshot_health_check.py

# Watch daemon 1 (XAUUSD)
tail -f logs/trading_daemon.log
```

### Log Format
```
--- Iteration 5 ---
Prices: BTC=$79,607.50 | ETH=$2,279.95 | SOL=$88.27
Balance: 100.00 | Equity: 100.00 | Open: 0/5 | Trades: 0 | Signals: 0
=== SUMMARY | Bal: 100.00 | Return: +0.00% | Trades: 15 | Win: 67% | DD: 0.0% | Positions: 3 ===
  STRATEGIES: Quick_Mo:3t|67wr|+0.080% | SMC_Orde:2t|50wr|+0.120% | Fib_Retr:1t|100wr|+0.250%
```

## Daemon Management

```bash
# Start moonshot daemon
systemctl --user start moonshot-daemon.service

# Stop
systemctl --user stop moonshot-daemon.service

# Restart
systemctl --user restart moonshot-daemon.service

# Enable on boot
systemctl --user enable moonshot-daemon.service
```

## File Modification Guidelines

When modifying code:
1. **Backup First**: Copy originals to `backups/`
2. **Test Immediately**: Run daemon and check logs
3. **Update AGENTS.md**: Document what changed and why
4. **Hot Reload**: Daemon picks up changes on restart (systemctl --user restart)
5. **Validate**: Check `tail -f logs/daemon.log` for errors

## Critical Lessons Learned

### 1. Warmup Period Required
The daemon needs 120 seconds to build enough candles before trading starts. Don't panic if you see "No high-confidence signals found" in the first few minutes.

### 2. Stale State Causes Crashes
If `state/moonshot/positions.json` has very old positions (>1hr), the daemon may crash on startup. Reset with: `echo '{}' > state/moonshot/positions.json`

### 3. systemd Service Configuration
`StartLimitIntervalSec` must be in `[Unit]` section, not `[Service]`. Wrong placement causes warnings and restart failures.

### 4. Duplicate Logging
Multiple modules configuring `logging.basicConfig()` causes duplicate log lines. The daemon's `main.py` now handles all logging configuration.

### 5. SL/TP Must Match Timeframe
Wide SL/TP (2%/4%) on 60-second candles causes 97% of trades to exit via STALE at random PnL. Tightened to 0.5%/1% for scalping.

### 6. Only One Signal Per Cycle Starves The System
Picking only the best signal across all coins/strategies means 1 trade per minute max. Changed to open 1 signal per coin per cycle, filling all available position slots.

### 7. Opencode Feedback Must Actually Invoke Opencode
The old `OpencodeFeedback` only wrote to a JSONL file. Now it invokes opencode via subprocess with a structured performance report prompt.

---

**Last Updated**: 2026-05-09
**Major Changes**: Tightened SL/TP, added 4 new strategies (SMC, Fibonacci, VWAP, MACD), fixed opencode feedback, added strategy lab, multi-signal execution, max positions 3->5
**Daemon 2 Status**: Running via systemd
**Daemon 1 Status**: Preserved but not actively used (all strategies unprofitable)
