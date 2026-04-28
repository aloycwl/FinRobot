# FinRobot

FinRobot is a modular algorithmic trading workspace for crypto/FX research, model experimentation, and optional live execution.

## What this repo now provides

- Clean Python package structure (`finrobot/`) with separate modules for data, indicators, ML, strategy, and execution.
- Numeric command menu for day-to-day operations.
- Integrated market snapshot pipeline:
  - OKX candles
  - CryptoPanic headlines
  - OKX orderbook depth
  - Alternative.me fear & greed
- LSTM/CNN predictive pipelines converted from notebook-style logic into reusable functions.
- Fast non-LLM strategy engine skeleton (EMA crossover + transaction cost aware backtest).
- MetaTrader 5 execution connector with configurable credentials.
- MT5 auto-trading mode with:
  - 1-minute execution cycle
  - 5-minute EMA(5) and EMA(20) trend filter
  - optional capped martingale lot sizing

## Project layout

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

tests/
  test_indicators.py
  test_hft.py

requirements.txt
README.md
```

## Setup

1. Create virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment variables:

```bash
export CP="your_cryptopanic_token"
export NV="your_nvidia_key"
export NVIDIA_MODEL="qwen/qwen3-235b-a22b"

# optional MT5
export MT5_LOGIN="12345678"
export MT5_PASSWORD="your_password"
export MT5_SERVER="Broker-Server"
```

## Run

```bash
python -m finrobot
```

Then choose from menu:

- `6` for one manual MT5 market order
- `7` to start MT5 auto-trading strategy loop

## Strategy logic (menu option 7)

- Trend detection on **5m** candles:
  - Compute EMA(5) and EMA(20)
- Entry decision on each **1m** cycle:
  - If latest 1m close is above both 5m EMAs => `LONG`
  - If latest 1m close is below both 5m EMAs => `SHORT`
  - Otherwise => no trade
- Martingale sizing:
  - Uses base lot, multiplier, and max steps
  - On last closed loss, step increases (capped)
  - On last closed profit, step resets to base lot

## Safety and expectations

- This code is designed for research and iterative improvement.
- No strategy can guarantee fixed returns (e.g. 5%/hour) in live markets.
- Martingale increases risk sharply; always use a cap (`max_steps`) and small base lot.
- Always start with backtesting + paper/demo trading before any real capital.
- Add robust risk controls (max drawdown stop, position caps, circuit-breakers) before production use.

## Iteration loop

Use the workflow below for continuous improvement:

1. Backtest strategy
2. Inspect metrics and failure modes
3. Adjust signal + risk parameters
4. Re-test and compare
5. Only then consider live deployment
