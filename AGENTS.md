# FinRobot - Agent Documentation

## Project Overview

**FinRobot** is a self-improving autonomous algorithmic trading system with a closed feedback loop using Opencode. It trades XAUUSD (Gold), FX pairs, and Crypto using multiple strategies with automatic optimization.

## Core Architecture

### 1. Background Daemon (`daemon_service.py`)
- **Purpose**: Runs 24/7 without terminal connection
- **PID File**: `daemon.pid` - tracks running instance
- **State File**: `daemon_state.json` - live status
- **Log File**: `trading_daemon.log` - main progress output
- **Interval**: 5-second cycles between backtests

### 2. Continuous Backtest Engine (`continuous_backtest.py`)
- **Purpose**: Tests strategies with random parameter combinations
- **Strategies Tested**:
  - Grid Trading (XAUUSD optimized)
  - Martingale Trend Following
  - High Frequency Trading (HFT)
- **Cycle Interval**: 2 seconds between tests
- **Sweep Interval**: Every 10 cycles, runs full parameter sweep

### 3. Opencode Feedback Loop (`finrobot/opencode_integration.py`)
- **Purpose**: Automatically improves strategy code
- **Rate Limit**: 75 minutes minimum between calls
- **Trigger Conditions**:
  - Win rate below 55%
  - Drawdown exceeds 2%
  - Scheduled optimization every 24 hours
- **Action**: Sends backtest results to Opencode, which modifies code directly

## Key Files & Their Purposes

### State Files (JSON)
| File | Purpose | Update Frequency |
|------|---------|------------------|
| `daemon_state.json` | Live daemon status (running, price, trades) | Every cycle |
| `feedback_loop_state.json` | Best parameters per strategy, iteration count | When new best found |
| `daemon.pid` | Process ID of running daemon | Start/Stop only |

### Log Files
| File | Purpose | Retention |
|------|---------|-----------|
| `trading_daemon.log` | Main progress output - use `tail -f` | Keep last 1000 lines |
| `backtest_logs/backtest_engine.log` | Detailed backtest results | Rotate daily |
| `opencode_feedback.log` | Opencode interaction history | Keep all |
| `feedback_iterations.log` | Every backtest result (JSONL) | Rotate when >100MB |

### Strategy Configuration
| File | Purpose |
|------|---------|
| `finrobot/grid.py` | Grid trading strategy for XAUUSD |
| `finrobot/backtesting.py` | Martingale trend strategy |
| `finrobot/hft.py` | High frequency trading strategy |
| `finrobot/indicators.py` | Technical indicators library |

## How to Monitor Progress

### Quick Status Check
```bash
# View daemon status
python daemon_service.py status

# Watch live progress (recommended)
tail -f trading_daemon.log
```

### Understanding the Log Output
The log shows progress in this format:
```
2026-05-01 13:47:31 | INFO     | Cycle #381 | Price: 4566.70 | [GRID] Return: -0.45% | [MART] Return: -0.99% | [HFT] Return: 0.00%
2026-05-01 13:47:31 | INFO     | Best: Martingale (Return: -0.99%, Win: 19.9%, Iter: 381)
```

Key metrics to watch:
- **Cycle #**: Current iteration count
- **Price**: Current XAUUSD price
- **[GRID]/[MART]/[HFT] Return**: Profit/loss percentage for each strategy
- **Best**: Current best performing strategy with stats

## Critical Lessons Learned

### 1. Data Column Bug (Fixed)
- **Issue**: `fetch_candles()` returned DataFrame with 'date' column as index, but backtesting looked for 'time' column
- **Fix**: Modified `backtesting.py` to handle both index and column naming
- **Date Fixed**: 2026-05-01

### 2. Parameter Name Mismatches (Fixed)
- **Issue**: Config classes used different parameter names than the backtest engine expected
- **Fixed Names**:
  - GridConfig: `grid_step` → `grid_step_pips`
  - HFTConfig: `tick_threshold` → correct
  - BacktestConfig: `ema_fast`/`ema_slow` → correct

### 3. JSON Serialization Error (Fixed)
- **Issue**: numpy int64 types couldn't be serialized to JSON in logs
- **Fix**: Added `NumpyJsonEncoder` class to handle numpy types

### 4. Strategy Performance Insights

#### Martingale Strategy
- **Best Parameters Found**:
  - multiplier: 1.25
  - base_lot: 0.005
  - max_steps: 2
  - ema_fast: 8
  - ema_slow: 34
- **Performance**: -0.99% return, 19.9% win rate (POOR)
- **Issue**: Win rate far below 55% target

#### Grid Strategy
- **Best Parameters Found**:
  - grid_step_pips: 1.0
  - take_profit_pips: 3.0
  - trend_ema_fast: 21
  - trend_ema_slow: 21
  - max_grid_levels: 2
  - base_lot: 0.02
- **Performance**: 0% return, 0% win rate, 0 trades
- **Issue**: Not executing any trades - likely due to grid spacing too tight

#### HFT Strategy
- **Best Parameters Found**:
  - tick_threshold: 0.08
  - volume_filter: 10
  - latency_ms: 50
  - spread_limit: 0.01
- **Performance**: 0% return, 0% win rate, 0 trades
- **Issue**: Not executing any trades - tick threshold may be too high for XAUUSD volatility

## Recommended Next Steps

1. **Fix Grid Strategy**: Reduce `grid_step_pips` to 0.5-1.0 for XAUUSD volatility
2. **Fix HFT Strategy**: Lower `tick_threshold` to 0.02-0.05 for XAUUSD
3. **Improve Martingale**: Test with faster EMA periods (5/12 instead of 8/34)
4. **Add New Indicators**: Test ADX, Ichimoku, Order Blocks per opencode instructions
5. **Target Metrics**: Aim for 5% hourly return, 85%+ win rate, <1.5% max drawdown

## File Modification Guidelines

When Opencode (or any agent) modifies code:

1. **Backup First**: Always copy original to `strategy_backups/`
2. **Test Immediately**: Run backtest after changes
3. **Log Changes**: Update this AGENTS.md with what was changed and why
4. **Hot Reload**: Changes are automatically picked up by daemon
5. **Validation**: Ensure code runs without errors before considering success

## Emergency Contacts & Resources

- **Opencode CLI**: `/home/openclaw/.npm-global/bin/opencode`
- **Python Environment**: Virtual env in project root
- **Data Source**: Local CSV files in `data/` directory
- **MT5 Connection**: Credentials in `.env` file

## Recent Updates (2026-05-02)

### ✅ Log Optimization Completed
**Problem**: Log files were growing extremely large with verbose output every cycle.

**Solution Implemented**:
1. **Daemon Logging** (`daemon_service.py`):
   - Now outputs **one clean line per cycle** with all key metrics
   - Format: `[ITER: X/10000 X.X%] Price: X | G:ret%|win%|trades M:... H:... | Best:X [E:N]`
   - Progress percentage shown (target: 10,000 iterations)
   - Summary only every 10 cycles

2. **Continuous Backtest** (`continuous_backtest.py`):
   - Reduced verbosity by ~90%
   - Only logs new "best" parameters or errors
   - Summaries every 100 iterations instead of every cycle

3. **Feedback Loop** (`finrobot/feedback_loop.py`):
   - Logging reduced to key events only
   - Baseline tests logged every 100 iterations
   - Best parameter updates logged when found

4. **Log Rotation** (`rotate_logs.sh`):
   - Created automatic log rotation script
   - Keeps only last 1000 lines of `trading_daemon.log`
   - Archives files >100MB with gzip
   - Run manually or add to crontab for automatic rotation

### How to Monitor Progress Now

Simply run:
```bash
tail -f /home/openclaw/FinRobot/trading_daemon.log
```

You'll see one clean line per cycle:
```
[ITER: 382/10000 3.8%] Price: 4566.70 | G:-0.45%|19.9%|5 M:-0.99%|19.9%|7629 H:0.00%|0.0%|0 | Best:M
```

**Fields explained:**
- `ITER: current/max percentage` - Progress tracking
- `Price: XAUUSD price`
- `G: return%|win%|trades` - Grid strategy summary
- `M: return%|win%|trades` - Martingale strategy summary  
- `H: return%|win%|trades` - HFT strategy summary
- `Best: [G/M/H]` - Which strategy is currently best
- `[E: N]` - Number of errors this cycle (only shown if >0)

---

**Last Updated**: 2026-05-02  
**Iteration Count**: 381 → optimizing toward 10,000  
**Daemon Status**: Running  
**Best Strategy**: Martingale (Return: -0.99%, Win Rate: 19.9%)  
**Current Optimization**: Reducing log verbosity, focusing on actionable metrics
