#!/bin/bash
# Log rotation script for FinRobot
# Keeps only the last 1000 lines of trading_daemon.log

LOG_FILE="/home/openclaw/FinRobot/trading_daemon.log"
MAX_LINES=1000

if [ -f "$LOG_FILE" ]; then
    # Count current lines
    LINE_COUNT=$(wc -l < "$LOG_FILE")
    
    if [ "$LINE_COUNT" -gt "$MAX_LINES" ]; then
        # Keep only last MAX_LINES
        tail -n "$MAX_LINES" "$LOG_FILE" > "${LOG_FILE}.tmp"
        mv "${LOG_FILE}.tmp" "$LOG_FILE"
        echo "[$(date)] Rotated log: kept last ${MAX_LINES} lines (removed $((LINE_COUNT - MAX_LINES)) old lines)"
    fi
fi

# Also rotate other large log files if they exist
for LOG in "/home/openclaw/FinRobot/feedback_iterations.log" "/home/openclaw/FinRobot/backtest_logs/backtest_engine.log"; do
    if [ -f "$LOG" ]; then
        SIZE=$(stat -c%s "$LOG" 2>/dev/null || stat -f%z "$LOG" 2>/dev/null)
        # If > 100MB, archive and restart
        if [ "$SIZE" -gt 104857600 ]; then
            ARCHIVE="${LOG}.$(date +%Y%m%d_%H%M%S).gz"
            gzip -c "$LOG" > "$ARCHIVE"
            > "$LOG"  # Clear the log
            echo "[$(date)] Archived $LOG to $ARCHIVE ($(numfmt --to=iec $SIZE))"
        fi
    fi
done
