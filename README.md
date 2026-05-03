# FinRobot - Multi-Strategy Algorithmic Trading System

**Status**: Active Development  
**Last Updated**: 2026-05-03  
**Version**: 2.0 - Multi-Strategy Engine

---

## Overview

FinRobot is a self-improving autonomous algorithmic trading system with a closed feedback loop. It combines multiple trading strategies including Grid Trading, Smart Money Concepts (SMC), Harmonic Patterns, and portfolio-level risk management with continuous genetic optimization.

### Key Features

- **Multi-Strategy Ensemble**: Combines Grid, SMC, Harmonic strategies
- **Smart Money Concepts**: Order Blocks, Fair Value Gaps, Liquidity Sweeps
- **Harmonic Patterns**: Gartley, Bat, Butterfly, Crab, Shark, Cypher patterns
- **Genetic Optimization**: Continuous parameter optimization using genetic algorithms
- **Portfolio Management**: Dynamic capital allocation with risk management
- **Continuous Learning**: Self-improving through iterative backtesting

---

## Project Structure

```
FinRobot/
├── finrobot/
│   ├── smart_money_concepts.py    # SMC module (Order Blocks, FVG, Sweeps)
│   ├── harmonic_patterns.py       # Harmonic pattern detection
│   ├── genetic_optimizer.py       # Genetic algorithm optimizer
│   ├── portfolio_manager.py       # Portfolio allocation & risk management
│   └── multi_strategy_engine.py   # Main engine combining all strategies
├── multi_strategy_runner.py       # CLI runner for continuous optimization
├── MULTI_STRATEGY_PORTFOLIO_PLAN.md  # Master plan document
├── AGENTS.md                      # Agent documentation
└── README.md                      # This file
```

---

## Architecture

### Core Components

#### 1. Smart Money Concepts (`smart_money_concepts.py`)
- **Order Blocks**: Bullish/Bearish OB detection with strength scoring
- **Fair Value Gaps**: Imbalance detection between price levels
- **Liquidity Sweeps**: Stop hunt detection and reversal signals
- **Signal Generation**: Combined setup detection for high-probability trades

#### 2. Harmonic Patterns (`harmonic_patterns.py`)
- **Pattern Detection**: 6 classic harmonic patterns
  - Gartley (0.618, 1.27, 0.786 ratios)
  - Bat (0.382-0.5, 1.618-2.618, 0.886)
  - Butterfly (0.786, 1.618-2.24, 1.27)
  - Crab (0.382-0.618, 2.24-3.618, 1.618)
  - Shark (1.13-1.618, 1.618-2.24, 0.886-1.13)
  - Cypher (0.382-0.618, 1.13-1.414, 0.786)
- **Swing Point Detection**: Automatic significant high/low identification
- **Fibonacci Validation**: Ratio matching with tolerance
- **Signal Generation**: Entry, SL, TP levels with confidence scoring

#### 3. Genetic Optimizer (`genetic_optimizer.py`)
- **Population Management**: 50 individuals per generation (configurable)
- **Selection**: Tournament selection (size 3)
- **Crossover**: Single-point crossover (rate 0.8)
- **Mutation**: Adaptive mutation (rate 0.15)
- **Elitism**: Top 5 individuals preserved
- **Fitness Function**: Multi-objective (win rate, return, drawdown)
- **Parameter Types**: Supports float, int, and choice parameters

#### 4. Portfolio Manager (`portfolio_manager.py`)
- **Performance Tracking**: Per-strategy metrics (Sharpe, drawdown, win rate)
- **Allocation Methods**:
  - Equal weight
  - Inverse volatility (risk parity)
  - Sharpe-weighted
  - Momentum-based
- **Rebalancing**: Time-based (hourly, daily, weekly) or drift-based (>5%)
- **Risk Management**:
  - Max drawdown limits
  - Daily/weekly loss limits
  - Correlation monitoring
- **Circuit Breakers**: Auto-stop on excessive drawdown

#### 5. Multi-Strategy Engine (`multi_strategy_engine.py`)
- **Strategy Implementations**:
  - **GridStrategy**: Grid trading with trend filter
  - **SMCStrategy**: Smart Money Concepts with OB + Sweep setups
  - **HarmonicStrategy**: Harmonic pattern trading
- **Signal Structure**: Unified format across all strategies
- **Backtest Engine**: Event-driven simulation
- **Optimization Loop**: Periodic genetic algorithm runs
- **State Management**: Save/load full system state

---

## Usage

### Starting the Optimizer

```bash
# Start fresh optimization
python multi_strategy_runner.py --iterations 10000 --capital 10000

# Resume from saved state
python multi_strategy_runner.py --resume

# Check current status
python multi_strategy_runner.py --status
```

### Monitoring Progress

```bash
# Watch logs in real-time
tail -f multi_strategy.log

# Check status anytime
python multi_strategy_runner.py --status
```

### Python API

```python
from multi_strategy_runner import ContinuousOptimizer

# Create optimizer
optimizer = ContinuousOptimizer(
    initial_capital=10000.0,
    iterations=10000
)

# Start optimization
optimizer.start()

# Or run single iteration
optimizer.run_single_iteration()

# Get current status
summary = optimizer.get_summary()
print(f"Win Rate: {summary['best_win_rate']:.2%}")
```

---

## Configuration

### Strategy Parameters

Each strategy has configurable parameters optimized by genetic algorithm:

**Grid Strategy**:
- `grid_step_pips`: Distance between grid levels (0.5 - 5.0)
- `take_profit_pips`: TP distance (1.0 - 10.0)
- `max_grid_levels`: Max open positions (2 - 10)
- `trend_ema_fast/slow`: Trend filter periods
- `volatility_filter`: ATR-based volatility threshold

**SMC Strategy**:
- `ob_lookback`: Periods for OB detection (3 - 10)
- `fvg_min_size`: Minimum FVG size (0.0005 - 0.005)
- `min_ob_strength`: Minimum OB confidence (0.5 - 0.9)
- `min_sweep_strength`: Minimum sweep confidence (0.6 - 0.9)
- `risk_reward_min`: Minimum R:R ratio (1.0 - 3.0)

**Harmonic Strategy**:
- `tolerance`: Fibonacci ratio tolerance (0.02 - 0.1)
- `min_confidence`: Minimum pattern confidence (0.5 - 0.95)
- `swing_window`: Swing point detection window (3 - 10)
- `risk_reward_min`: Minimum R:R ratio (1.0 - 3.0)

### Genetic Algorithm Settings

```python
GeneticOptimizer(
    population_size=50,      # Individuals per generation
    elite_size=5,            # Top individuals to preserve
    mutation_rate=0.15,      # Mutation probability
    crossover_rate=0.8,      # Crossover probability
    tournament_size=3        # Tournament selection size
)
```

### Optimization Targets

- **Win Rate**: Target > 65%
- **Return**: Target > 5% per session
- **Max Drawdown**: Limit < 3%
- **Sharpe Ratio**: Target > 2.0

---

## Performance Metrics

The system tracks:

- **Win Rate**: Percentage of winning trades
- **Total Return**: Cumulative percentage return
- **Sharpe Ratio**: Risk-adjusted return metric
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Profit Factor**: Gross profit / gross loss
- **Volatility**: Standard deviation of returns
- **Expectancy**: Average R per trade

---

## Development Roadmap

### Completed (v2.0)
- ✅ Multi-strategy ensemble architecture
- ✅ Smart Money Concepts implementation
- ✅ Harmonic pattern detection
- ✅ Genetic optimization engine
- ✅ Portfolio management system
- ✅ Continuous optimization loop
- ✅ State persistence (save/load)

### In Progress
- 🔄 Live data integration (MT5 API)
- 🔄 Real-time execution engine
- 🔄 Advanced risk management (Kelly criterion)
- 🔄 Machine learning integration

### Planned (v3.0)
- 📋 Deep learning price prediction
- 📋 Sentiment analysis integration
- 📋 Options/Futures strategies
- 📋 Multi-asset correlation trading
- 📋 Real-time portfolio optimization
- 📋 Web dashboard for monitoring

---

## Troubleshooting

### Common Issues

**1. Import Errors**
```python
# Ensure finrobot is in Python path
import sys
sys.path.insert(0, '/home/openclaw/FinRobot')
```

**2. Memory Issues**
- Reduce `population_size` in GeneticOptimizer
- Decrease `iterations` in runner
- Clear data cache periodically

**3. Slow Optimization**
- Reduce generation count per optimization
- Decrease population size
- Use parallel processing (add `multiprocessing`)

**4. No Signals Generated**
- Check data quality and format
- Verify parameter ranges are appropriate
- Increase lookback periods for indicators
- Check minimum confidence thresholds

### Debug Mode

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)

# Run with verbose output
optimizer = ContinuousOptimizer()
optimizer.run_single_iteration()  # Step through one iteration
```

### Getting Help

1. Check logs: `tail -f multi_strategy.log`
2. Check status: `python multi_strategy_runner.py --status`
3. Review state: `cat optimizer_state.json | jq .`

---

## Contributing

When adding new strategies:

1. Create new file in `finrobot/` directory
2. Inherit from `StrategyBase` class
3. Implement `generate_signal()` method
4. Define `get_param_specs()` for optimization
5. Register in `MultiStrategyEngine._initialize_strategies()`
6. Add tests and documentation

### Code Style

- Follow PEP 8
- Type hints for function signatures
- Docstrings for all public methods
- Logging instead of print statements

---

## License

This project is proprietary and confidential.

---

## Contact

For questions or issues:
1. Check this README and AGENTS.md
2. Review logs and state files
3. Consult MULTI_STRATEGY_PORTFOLIO_PLAN.md for architecture details

---

**Last Updated**: 2026-05-03  
**System Version**: 2.0  
**Status**: Production Ready - Continuous Optimization Active
