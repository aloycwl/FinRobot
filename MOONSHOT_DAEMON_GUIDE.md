# 🚀 Moonshot Daemon 2 - 24/7 Trading Bot

## Quick Start

### Start the Daemon
```bash
cd /home/openclaw/FinRobot
python3 run_daemon.py --interval 60 --balance 100
```

### Monitor Logs
```bash
# Real-time log viewing
tail -f moonshot_logs/moonshot_daemon.log

# Check latest entries
tail -50 moonshot_logs/moonshot_daemon.log
```

### Check Status
```bash
# View current state
cat moonshot_data/state.json

# View positions
cat moonshot_data/positions.json

# View trade history
cat moonshot_data/trades.jsonl
```

### Stop the Daemon
```bash
# Find PID and kill
ps aux | grep run_daemon
kill -TERM <PID>

# Or if running in foreground, press Ctrl+C
```

---

## Architecture

### Components
1. **WebSocket Client** (`hyperliquid_ws_client.py`)
   - Connects to Hyperliquid WebSocket
   - Receives real-time price data
   - Handles auto-reconnection

2. **State Manager** (`state_manager.py`)
   - Tracks open positions
   - Records trade history
   - Persists state to disk
   - Auto-saves every 30 seconds

3. **Main Daemon** (`main.py`)
   - 24/7 event loop
   - Checks for opportunities every 60s
   - Manages lifecycle

### Data Flow
```
Hyperliquid WS → WebSocket Client → Price Cache → Main Loop
                                              ↓
State Manager ← Trade History ← Opportunity Check
```

---

## File Structure

```
/home/openclaw/FinRobot/
├── run_daemon.py              # Launcher script
├── moonshot_daemon/           # Daemon package
│   ├── __init__.py
│   ├── main.py               # Main daemon loop
│   ├── hyperliquid_ws_client.py  # WebSocket client
│   └── state_manager.py      # State persistence
├── moonshot_data/            # Data storage
│   ├── state.json           # Current state
│   ├── positions.json       # Open positions
│   └── trades.jsonl         # Trade history
└── moonshot_logs/            # Log files
    └── moonshot_daemon.log  # Main log
```

---

## Configuration

Edit `moonshot_daemon/main.py` to customize:

```python
# Trading parameters
INITIAL_BALANCE = 100.0        # Starting USDT
MAX_LEVERAGE = 50.0           # Max leverage
MAX_POSITIONS = 5             # Max open trades
RISK_PER_TRADE = 0.05         # 5% risk per trade

# Symbols to trade
SYMBOLS = ["BTC-PERP", "ETH-PERP", "SOL-PERP"]

# Operational
CHECK_INTERVAL = 60.0         # Check every 60s
SAVE_INTERVAL = 30.0            # Save state every 30s
```

---

## Adding Trading Logic

Implement your strategy in `check_opportunities()` in `main.py`:

```python
def check_opportunities(self):
    """Main trading logic - check for opportunities"""
    
    # 1. Get current prices
    prices = self.ws_client.get_all_prices()
    
    # 2. Calculate indicators
    for symbol in self.symbols:
        coin = symbol.replace("-PERP", "")
        price = prices.get(coin)
        
        if price:
            # Your indicator calculations
            # rsi = calculate_rsi(symbol)
            # ema = calculate_ema(symbol)
            
            # 3. Check for signals
            # if rsi < 30:
            #     self.execute_trade(symbol, 'buy', price)
            pass
    
    logger.info("✅ Opportunity check complete")
```

---

## Troubleshooting

### Daemon won't start
```bash
# Check Python version
python3 --version  # Should be 3.7+

# Check imports
python3 -c "from moonshot_daemon.main import MoonshotDaemon"

# Check for syntax errors
python3 -m py_compile moonshot_daemon/main.py
```

### No price data
```bash
# Check WebSocket connection
tail -f moonshot_logs/moonshot_daemon.log | grep -E "(WebSocket|price|ERROR)"

# Test WebSocket manually
python3 -c "
from moonshot_daemon.hyperliquid_ws_client import HyperliquidWebSocketClient
client = HyperliquidWebSocketClient()
client.subscribe_all_mids()
client.start()
import time; time.sleep(10)
print(client.get_all_prices())
client.stop()
"
```

### State not saving
```bash
# Check permissions
ls -la moonshot_data/

# Check disk space
df -h

# Clear corrupted state
rm moonshot_data/state.json moonshot_data/positions.json
```

---

## Monitoring

### Live Dashboard (Terminal)
```bash
# Watch live prices and stats
watch -n 1 'echo "=== Moonshot Daemon Status ===" && echo "" && echo "Latest Log:" && tail -5 moonshot_logs/moonshot_daemon.log && echo "" && echo "Current State:" && cat moonshot_data/state.json 2>/dev/null | python3 -m json.tool 2>/dev/null | head -20'
```

### Health Check Script
```bash
#!/bin/bash
# health_check.sh

PID=$(pgrep -f "run_daemon.py")
if [ -z "$PID" ]; then
    echo "❌ Daemon is not running"
    exit 1
else
    echo "✅ Daemon is running (PID: $PID)"
fi

# Check last log entry
LAST_LOG=$(tail -1 moonshot_logs/moonshot_daemon.log)
LAST_TIME=$(echo "$LAST_LOG" | grep -oP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
if [ ! -z "$LAST_TIME" ]; then
    LAST_EPOCH=$(date -d "$LAST_TIME" +%s 2>/dev/null || echo "0")
    NOW_EPOCH=$(date +%s)
    DIFF=$((NOW_EPOCH - LAST_EPOCH))
    if [ $DIFF -gt 120 ]; then
        echo "⚠️  Last log entry is ${DIFF}s old"
    else
        echo "✅ Last log entry is ${DIFF}s old"
    fi
fi
```

---

## Next Steps

1. **Implement Trading Logic**: Add your strategies to `check_opportunities()`
2. **Add Risk Management**: Implement position sizing and stop losses
3. **Add Notifications**: Set up alerts for trades and errors
4. **Deploy to VPS**: Run on a server for true 24/7 operation
5. **Monitor Performance**: Track metrics and optimize strategies

---

## Support

- **Logs**: `moonshot_logs/moonshot_daemon.log`
- **State**: `moonshot_data/state.json`
- **Code**: `moonshot_daemon/`
- **README**: This file

