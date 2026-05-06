from __future__ import annotations

import sqlite3
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Optional

from .config import settings

logger = logging.getLogger("historical_cache")

DB_PATH = "/home/openclaw/FinRobot/historical_data.db"


class HistoricalCache:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS candles (
            timestamp INTEGER PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            symbol TEXT,
            timeframe TEXT
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_time ON candles(symbol, timestamp)")
        self.conn.commit()

    def get_candles(self, symbol: str, limit: int = 1000) -> Optional[pd.DataFrame]:
        """Get candles from cache"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT timestamp, open, high, low, close, volume FROM candles
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (symbol, limit))
        
        rows = cursor.fetchall()
        if not rows:
            return None
            
        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["date"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        df = df.set_index("date").sort_index()
        
        return df[["open", "high", "low", "close", "volume"]]

    def insert_candles(self, df: pd.DataFrame, symbol: str):
        """Insert candles into cache"""
        cursor = self.conn.cursor()
        
        for date, row in df.iterrows():
            timestamp = int(date.timestamp())
            cursor.execute("""
                INSERT OR IGNORE INTO candles 
                (timestamp, open, high, low, close, volume, symbol, timeframe)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                float(row.open),
                float(row.high),
                float(row.low),
                float(row.close),
                float(row.volume),
                symbol,
                "1m"
            ))
        
        self.conn.commit()
        logger.debug(f"Inserted {len(df)} candles into cache")

    def get_latest_timestamp(self, symbol: str) -> Optional[int]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM candles WHERE symbol = ?", (symbol,))
        result = cursor.fetchone()[0]
        return result if result else None

    def count_candles(self, symbol: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM candles WHERE symbol = ?", (symbol,))
        return cursor.fetchone()[0]


cache = HistoricalCache()
