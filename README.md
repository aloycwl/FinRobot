# FinRobot

FinRobot is a **self-improving autonomous algorithmic trading bot with closed opencode feedback loop. For XAUUSD, FX & Crypto.

## ✅ Implemented Features

- All original core modules: data feeds, indicators, ML models, MT5 execution
- ✅ **Martingale Trend Strategy** (backtested)
- ✅ **High Frequency Grid Strategy** (XAUUSD optimized):
  - 5min chart EMA 5/15 trend direction filter
  - 1min chart execution, 5 pip grid steps
  - 1 pip fixed take profit per position
- ✅ **Autonomous Background Daemon** - runs 24/7 disconnected
- ✅ **CLOSED SELF-IMPROVEMENT LOOP with OPENCODE**
  - Automatically runs continuous backtesting
  - Logs all performance metrics
  - Automatically calls opencode for improvements
  - Opencode modifies strategy code directly
  - Hot reloads changes automatically
  - Rate limited, safety guarded, validates all changes

Full daemon system with hot reload, automatic parameter tuning, and self-optimization.

## Project Layout

```text
finrobot/
  __main__.py
  cli.py
  config.py
  data_sources.py
  indicators.py
  llm.py
  ml.py
  hft.py
  mt5_executor.py
  backtesting.py
  grid.py                  # XAUUSD Grid Trading Strategy
  opencode_integration.py  # Automatic opencode feedback loop
  hot_reload.py            # Runtime strategy reloading

daemon_service.py          # Background daemon controller

# Generated runtime files
daemon.pid
daemon_state.json
trading_daemon.log
feedback_iterations.log
opencode_feedback.log
strategy_backups/
```

## Setup

1. Create virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment variables:
Copy `.env.example` to `.env` and fill credentials:
```
# MetaTrader 5
MT5_LOGIN=52606973
MT5_PASSWORD=ew!6J6gjXOUpd6
MT5_SERVER=ICMarketsSC-Demo
MT5_SYMBOL=XAUUSD
MT5_PIP_VALUE=0.01

# Data providers (optional)
CP=
NV=
```

## Run

### Interactive CLI
```bash
python -m finrobot
```
Select actions by number from the interactive menu (includes grid strategy backtest option 6)

### Autonomous Background Daemon
```bash
# Start daemon (survives terminal disconnect)
python3 daemon_service.py start

# Check status anytime
python3 daemon_service.py status

# Run full parameter sweep
python3 daemon_service.py sweep

# Stop daemon
python3 daemon_service.py stop
```

Daemon runs completely in background. You can safely log out. It will continue trading, backtesting, and calling opencode to automatically improve itself indefinitely.

## Safety and expectations

- This code is designed for research and iterative improvement.
- No strategy can guarantee fixed returns (e.g. 5%/hour) in live markets.
- Always start with backtesting + paper/demo trading before any real capital.
- Add robust risk controls (max drawdown stop, position caps, circuit-breakers) before production use.

## Iteration loop

**✅ Correct required workflow (USE THIS EXACT SEQUENCE):**
```
code > backtest > submit results > improve code > repeat
```

### Current Log Status & Findings (2026-04-28)
⚠️ **BROKEN LOOP DETECTED**:
- ✅ Loop IS running (daemon active, executing iterations)
- ❌ EVERY BACKTEST FAILS WITH CONFIG ERRORS
- ❌ Parameter names mismatched in all 3 strategies
- ❌ 100% failed iterations (100/100 logged entries)
- ❌ Loop is stuck repeating same failures without improvement
- Root causes:
  1. GridConfig: invalid `grid_step` parameter name
  2. HFTConfig: invalid `tick_threshold` parameter name
  3. BacktestConfig: invalid `ema_fast` parameter name
  4. Pandas KeyError: 'time' column missing in dataframe
  5. JSON serialization bug: numpy int64 not serializable
  6. KeyError when applying best parameters (none exist)

### Required Fixes First:
1. Fix the config class parameter names to match what the loop is generating
2. Fix dataframe column name mapping
3. Add numpy type conversion before JSON logging
4. Add proper error handling so loop can actually improve instead of repeating failures
