"""
Moonshot Daemon - 24/7 Automated Trading Main Loop
Runs continuously, checks for opportunities every 60 seconds
Integrates real-time WebSocket prices with strategy engine and paper trading
"""

import sys
import time
import json
import logging
import signal
import threading
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from moonshot.daemon.hyperliquid_ws_client import (
    HyperliquidWebSocketClient, PriceUpdate, TradeData
)
from moonshot.daemon.state_manager import StateManager, PositionState, TradeRecord
from moonshot.strategies.strategies import (
    AggressiveADXScalper, AggressiveCryptoScalper,
    BreakoutHunter, MeanReversionBandit,
    SmartMoneyConcepts, FibonacciRetracement,
    VWAPStrategy, MACDStrategy,
    TradingSignal, SignalType, TechnicalIndicators
)
from moonshot.strategies.executor import (
    HyperliquidPaperTrading, OrderSide, OrderType
)
import pandas as pd
import numpy as np

log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "daemon.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class QuickMomentum:
    """Fast momentum strategy that generates signals from EMA crosses"""

    def __init__(self, ema_fast: int = 8, ema_slow: int = 21, rsi_period: int = 14,
                 rsi_ob: float = 65, rsi_os: float = 35, max_leverage: float = 20.0):
        self.name = "Quick_Momentum"
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.rsi_ob = rsi_ob
        self.rsi_os = rsi_os
        self.max_leverage = max_leverage
        self.indicators = TechnicalIndicators()
        self.coins_traded = set()
        self.last_signal_time = {}

    def generate_signal(self, symbol: str, ohlcv: pd.DataFrame,
                        current_price: float, account_balance: float) -> Optional[TradingSignal]:
        import time as _time
        now = _time.time()
        coin = symbol.replace("-PERP", "")
        if coin in self.last_signal_time and now - self.last_signal_time[coin] < 15:
            return None

        min_len = max(self.ema_slow, self.rsi_period) + 3
        if len(ohlcv) < min_len:
            return None

        closes = ohlcv['close']
        volumes = ohlcv.get('volume', pd.Series([1] * len(ohlcv)))

        ema_f = self.indicators.ema(closes, self.ema_fast)
        ema_s = self.indicators.ema(closes, self.ema_slow)
        rsi = self.indicators.rsi(closes, self.rsi_period)

        fast_val = ema_f.iloc[-1]
        slow_val = ema_s.iloc[-1]
        prev_fast = ema_f.iloc[-2] if len(ema_f) > 1 else fast_val
        prev_slow = ema_s.iloc[-2] if len(ema_s) > 1 else slow_val
        cur_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50

        bullish_cross = prev_fast <= prev_slow and fast_val > slow_val
        bearish_cross = prev_fast >= prev_slow and fast_val < slow_val

        price_chg = (closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2] if len(closes) >= 2 else 0

        signal = None
        if bullish_cross and cur_rsi < self.rsi_ob:
            confidence = 0.55 + min(0.25, abs(price_chg) * 10)
            if cur_rsi < 45:
                confidence += 0.1
            sl = current_price * 0.997
            tp = current_price * 1.006
            size = (account_balance * 0.15) / current_price
            signal = TradingSignal(
                symbol=symbol, signal_type=SignalType.BUY,
                confidence=min(0.9, confidence), suggested_leverage=20.0,
                suggested_size=size, entry_price=current_price,
                stop_loss=sl, take_profit=tp,
                rationale=f"Mom LONG: EMA{self.ema_fast}/{self.ema_slow} cross, RSI={cur_rsi:.0f}"
            )
            self.last_signal_time[coin] = now

        elif bearish_cross and cur_rsi > self.rsi_os:
            confidence = 0.55 + min(0.25, abs(price_chg) * 10)
            if cur_rsi > 55:
                confidence += 0.1
            sl = current_price * 1.003
            tp = current_price * 0.994
            size = (account_balance * 0.15) / current_price
            signal = TradingSignal(
                symbol=symbol, signal_type=SignalType.SELL,
                confidence=min(0.9, confidence), suggested_leverage=20.0,
                suggested_size=size, entry_price=current_price,
                stop_loss=sl, take_profit=tp,
                rationale=f"Mom SHORT: EMA{self.ema_fast}/{self.ema_slow} cross, RSI={cur_rsi:.0f}"
            )
            self.last_signal_time[coin] = now

        return signal


class RsiDivergence:
    """RSI overbought/oversold mean reversion with trend filter"""

    def __init__(self, rsi_period: int = 14, rsi_ob: float = 78, rsi_os: float = 22,
                 max_leverage: float = 20.0):
        self.name = "RSI_Reversion"
        self.rsi_period = rsi_period
        self.rsi_ob = rsi_ob
        self.rsi_os = rsi_os
        self.max_leverage = max_leverage
        self.indicators = TechnicalIndicators()
        self.last_signal_time = {}

    def generate_signal(self, symbol: str, ohlcv: pd.DataFrame,
                        current_price: float, account_balance: float) -> Optional[TradingSignal]:
        import time as _time
        now = _time.time()
        coin = symbol.replace("-PERP", "")
        if coin in self.last_signal_time and now - self.last_signal_time[coin] < 15:
            return None

        if len(ohlcv) < max(self.rsi_period + 3, 50):
            return None

        closes = ohlcv['close']
        rsi = self.indicators.rsi(closes, self.rsi_period)
        cur_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        prev_rsi = rsi.iloc[-2] if len(rsi) > 1 and not pd.isna(rsi.iloc[-2]) else 50

        ema20 = closes.rolling(20).mean().iloc[-1] if len(closes) >= 20 else current_price
        ema50 = closes.rolling(50).mean().iloc[-1] if len(closes) >= 50 else current_price
        uptrend = current_price > ema20 and ema20 > ema50
        downtrend = current_price < ema20 and ema20 < ema50

        signal = None
        if cur_rsi < self.rsi_os and prev_rsi < self.rsi_os:
            confidence = 0.6 + (self.rsi_os - cur_rsi) / 100
            if uptrend:
                confidence += 0.1
            sl = current_price * 0.997
            tp = current_price * 1.006
            size = (account_balance * 0.12) / current_price
            signal = TradingSignal(
                symbol=symbol, signal_type=SignalType.BUY,
                confidence=min(0.9, confidence), suggested_leverage=self.max_leverage,
                suggested_size=size, entry_price=current_price,
                stop_loss=sl, take_profit=tp,
                rationale=f"RSI LONG: RSI={cur_rsi:.0f} oversold bounce (trend={'UP' if uptrend else 'flat'})"
            )
            self.last_signal_time[coin] = now

        elif cur_rsi > self.rsi_ob and prev_rsi > self.rsi_ob:
            if uptrend:
                return None
            confidence = 0.6 + (cur_rsi - self.rsi_ob) / 100
            if downtrend:
                confidence += 0.1
            sl = current_price * 1.003
            tp = current_price * 0.994
            size = (account_balance * 0.12) / current_price
            signal = TradingSignal(
                symbol=symbol, signal_type=SignalType.SELL,
                confidence=min(0.9, confidence), suggested_leverage=self.max_leverage,
                suggested_size=size, entry_price=current_price,
                stop_loss=sl, take_profit=tp,
                rationale=f"RSI SHORT: RSI={cur_rsi:.0f} overbought reversal (trend={'DOWN' if downtrend else 'flat'})"
            )
            self.last_signal_time[coin] = now

        return signal


class MicroTrend:
    """Micro trend follower - trades on momentum with trend confirmation"""

    def __init__(self, lookback: int = 10, momentum_threshold: float = 0.002,
                 max_leverage: float = 20.0):
        self.name = "Micro_Trend"
        self.lookback = lookback
        self.momentum_threshold = momentum_threshold
        self.max_leverage = max_leverage
        self.last_signal_time = {}

    def generate_signal(self, symbol: str, ohlcv: pd.DataFrame,
                        current_price: float, account_balance: float) -> Optional[TradingSignal]:
        import time as _time
        now = _time.time()
        coin = symbol.replace("-PERP", "")
        if coin in self.last_signal_time and now - self.last_signal_time[coin] < 15:
            return None

        if len(ohlcv) < self.lookback + 2:
            return None

        closes = ohlcv['close']

        recent = closes.iloc[-self.lookback:]
        momentum = (recent.iloc[-1] - recent.iloc[0]) / recent.iloc[0]

        short_mom = (closes.iloc[-1] - closes.iloc[-3]) / closes.iloc[-3] if len(closes) >= 3 else 0

        ema20 = closes.rolling(20).mean().iloc[-1] if len(closes) >= 20 else current_price
        trending_up = current_price > ema20
        trending_down = current_price < ema20

        signal = None

        if momentum > self.momentum_threshold and short_mom > 0 and trending_up:
            confidence = 0.55 + min(0.3, abs(momentum) * 20)
            sl = current_price * 0.997
            tp = current_price * 1.006
            size = (account_balance * 0.10) / current_price
            signal = TradingSignal(
                symbol=symbol, signal_type=SignalType.BUY,
                confidence=min(0.85, confidence), suggested_leverage=self.max_leverage,
                suggested_size=size, entry_price=current_price,
                stop_loss=sl, take_profit=tp,
                rationale=f"uTrend LONG: mom={momentum*100:.2f}%, short={short_mom*100:.2f}%"
            )
            self.last_signal_time[coin] = now

        elif momentum < -self.momentum_threshold and short_mom < 0 and trending_down:
            confidence = 0.55 + min(0.3, abs(momentum) * 20)
            sl = current_price * 1.003
            tp = current_price * 0.994
            size = (account_balance * 0.10) / current_price
            signal = TradingSignal(
                symbol=symbol, signal_type=SignalType.SELL,
                confidence=min(0.85, confidence), suggested_leverage=self.max_leverage,
                suggested_size=size, entry_price=current_price,
                stop_loss=sl, take_profit=tp,
                rationale=f"uTrend SHORT: mom={momentum*100:.2f}%, short={short_mom*100:.2f}%"
            )
            self.last_signal_time[coin] = now

        return signal


class CandleBuilder:
    """Builds OHLCV candles from real-time price ticks"""

    def __init__(self, timeframe_seconds: int = 60):
        self.timeframe_seconds = timeframe_seconds
        self.candles: Dict[str, List[Dict]] = {}
        self.current_candle: Dict[str, Dict] = {}
        self.last_tick: Dict[str, float] = {}

    def update(self, coin: str, price: float, volume: float = 0.0):
        now = time.time()
        candle_start = int(now // self.timeframe_seconds) * self.timeframe_seconds

        if coin not in self.candles:
            self.candles[coin] = []

        if coin not in self.current_candle:
            self.current_candle[coin] = self._new_candle(candle_start, price, volume)
        else:
            candle = self.current_candle[coin]
            if candle["open_time"] != candle_start:
                self.candles[coin].append(candle.copy())
                if len(self.candles[coin]) > 1000:
                    self.candles[coin] = self.candles[coin][-1000:]
                self.current_candle[coin] = self._new_candle(candle_start, price, volume)
            else:
                candle["high"] = max(candle["high"], price)
                candle["low"] = min(candle["low"], price)
                candle["close"] = price
                candle["volume"] += volume

        self.last_tick[coin] = now

    def _new_candle(self, open_time: float, price: float, volume: float) -> Dict:
        return {
            "open_time": open_time,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
            "volume": volume,
        }

    def get_ohlcv_df(self, coin: str, min_candles: int = 15):
        import pandas as pd

        all_candles = list(self.candles.get(coin, []))
        if coin in self.current_candle:
            all_candles.append(self.current_candle[coin])

        if len(all_candles) < min_candles:
            return None

        df = pd.DataFrame(all_candles)
        df.rename(columns={"open_time": "time"}, inplace=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        return df


class MoonshotDaemon:

    def __init__(
        self,
        initial_balance: float = 100.0,
        symbols: List[str] = None,
        check_interval: float = 60.0,
        paper_trading: bool = True
    ):
        self.initial_balance = initial_balance
        self.symbols = symbols or ["BTC-PERP", "ETH-PERP", "SOL-PERP"]
        self.coin_map = {s.replace("-PERP", ""): s for s in self.symbols}
        self.check_interval = check_interval
        self.paper_trading = paper_trading

        self.ws_client: Optional[HyperliquidWebSocketClient] = None
        self.state_manager: Optional[StateManager] = None

        self.candle_builder = CandleBuilder(timeframe_seconds=60)

        self.trading_engine = HyperliquidPaperTrading(
            initial_balance=initial_balance,
            symbols=self.symbols,
            default_leverage=20.0,
            max_leverage=50.0,
        )

        self.strategies = [
            QuickMomentum(
                ema_fast=8, ema_slow=21, rsi_period=14,
                rsi_ob=65, rsi_os=35, max_leverage=20.0,
            ),
            RsiDivergence(
                rsi_period=14, rsi_ob=78, rsi_os=22, max_leverage=20.0,
            ),
            SmartMoneyConcepts(
                ob_lookback=20, fvg_min_size_pct=0.002, max_leverage=20.0,
            ),
            FibonacciRetracement(
                swing_lookback=30, confluence_threshold=0.003, max_leverage=20.0,
            ),
            MACDStrategy(
                macd_fast=12, macd_slow=26, macd_signal=9, max_leverage=20.0,
            ),
            VWAPStrategy(
                vwap_std_mult=2.0, reversion_band=1.5, max_leverage=20.0,
            ),
            AggressiveCryptoScalper(
                ema_fast=5, ema_slow=13, rsi_period=14,
                rsi_overbought=75, rsi_oversold=25,
                volume_threshold=0.5, max_leverage=20.0,
            ),
        ]

        self.running = False
        self.iteration_count = 0
        self.total_signals = 0
        self.total_trades = 0

        self._strategy_tracker = None
        self._self_improver = None
        self._last_signal_strategy: Dict[str, str] = {}
        self._last_improvement_time = 0.0
        self._improvement_interval = 3600
        self._last_backtest_time = 0.0
        self._backtest_interval = 1800

        self.max_open_positions = 5
        self.max_risk_per_trade_pct = 0.03
        self.stop_loss_pct = 0.003
        self.take_profit_pct = 0.006
        self.trailing_stop_pct = 0.004
        self.max_drawdown_pct = 0.50
        self.max_position_duration = 900
        self.stale_position_threshold = 600
        self.stale_pnl_threshold = 0.001

        self.current_prices: Dict[str, float] = {}
        self.position_highest: Dict[str, float] = {}
        self.position_entry_time: Dict[str, float] = {}
        self.position_sl: Dict[str, float] = {}
        self.position_tp: Dict[str, float] = {}

        logger.info("=" * 70)
        logger.info("MOONSHOT DAEMON INITIALIZED - TIGHT SCALP MODE (SL 0.3% TP 0.6%)")
        logger.info("=" * 70)
        logger.info(f"  Initial Balance: {initial_balance} USDT")
        logger.info(f"  Symbols: {', '.join(self.symbols)}")
        logger.info(f"  Check Interval: {check_interval}s")
        logger.info(f"  Paper Trading: {paper_trading}")
        logger.info(f"  Max Leverage: 20x | Risk/Trade: {self.max_risk_per_trade_pct*100:.1f}%")
        logger.info(f"  SL: {self.stop_loss_pct*100:.2f}% | TP: {self.take_profit_pct*100:.2f}% | Trail: {self.trailing_stop_pct*100:.2f}% | Candles: 60s")
        logger.info(f"  Stale: {self.stale_position_threshold}s | Timeout: {self.max_position_duration}s | MaxPos: {self.max_open_positions}")
        logger.info(f"  Strategies: {len(self.strategies)}")
        logger.info("=" * 70)

    def initialize(self):
        logger.info("Initializing components...")

        self.state_manager = StateManager(
            data_dir="state/moonshot",
            save_interval=30.0
        )
        self.state_manager.start_auto_save()

        self.ws_client = HyperliquidWebSocketClient()

        self.ws_client.on_price_update = self._on_price_update
        self.ws_client.on_trade = self._on_trade
        self.ws_client.on_connect = self._on_ws_connect
        self.ws_client.on_disconnect = self._on_ws_disconnect

        self.ws_client.subscribe_all_mids()
        for symbol in self.symbols:
            coin = symbol.replace("-PERP", "")
            self.ws_client.subscribe_trades(coin)

        try:
            from moonshot.daemon.self_improvement import StrategyPerformanceTracker, SelfImprover
            self._strategy_tracker = StrategyPerformanceTracker(
                data_dir="state/moonshot"
            )
            self._self_improver = SelfImprover(
                strategy_tracker=self._strategy_tracker,
                strategies=self.strategies,
                data_dir="state/moonshot",
                improvement_interval=self._improvement_interval,
            )
            self._strategy_tracker.load()
            logger.info("Self-improvement system initialized")
        except Exception as e:
            logger.warning(f"Self-improvement system not available: {e}")
            self._strategy_tracker = None
            self._self_improver = None

        logger.info("All components initialized")

    def _on_price_update(self, update: PriceUpdate):
        coin = update.coin
        self.current_prices[coin] = update.mid

        self.candle_builder.update(coin, update.mid)

        self.trading_engine.update_price(
            f"{coin}-PERP" if f"{coin}-PERP" in self.trading_engine.symbols else coin,
            update.mid
        )

        if coin in [s.replace("-PERP", "") for s in self.symbols]:
            self._check_stops_and_profits(coin, update.mid)

    def _on_trade(self, trade: TradeData):
        pass

    def _on_ws_connect(self):
        logger.info("WebSocket connected to Hyperliquid")

    def _on_ws_disconnect(self):
        logger.warning("WebSocket disconnected from Hyperliquid")

    def _check_stops_and_profits(self, coin: str, current_price: float):
        symbol = f"{coin}-PERP"

        if symbol not in self.trading_engine.positions:
            return

        pos = self.trading_engine.positions[symbol]

        if coin not in self.position_highest:
            self.position_highest[coin] = current_price
        if coin not in self.position_entry_time:
            self.position_entry_time[coin] = pos.timestamp

        self.position_highest[coin] = max(
            self.position_highest.get(coin, current_price), current_price
        )
        highest = self.position_highest[coin]
        entry_time = self.position_entry_time.get(coin, pos.timestamp)
        position_age = time.time() - entry_time

        pos_sl = self.position_sl.get(coin, pos.entry_price * (1 - self.stop_loss_pct))
        pos_tp = self.position_tp.get(coin, pos.entry_price * (1 + self.take_profit_pct))

        if pos.side == OrderSide.BUY:
            pnl_pct = (current_price - pos.entry_price) / pos.entry_price
            sl_pct = (pos.entry_price - pos_sl) / pos.entry_price
            tp_pct = (pos_tp - pos.entry_price) / pos.entry_price
            should_close_sl = current_price <= pos_sl
            should_close_tp = current_price >= pos_tp
            trailing_stop = highest * (1 - self.trailing_stop_pct)
            should_close_trail = current_price < trailing_stop and highest > pos.entry_price * 1.005
            should_close_stale = (position_age > self.stale_position_threshold
                                  and abs(pnl_pct) < self.stale_pnl_threshold)
            should_close_timeout = position_age > self.max_position_duration
        else:
            pnl_pct = (pos.entry_price - current_price) / pos.entry_price
            sl_pct = (pos_sl - pos.entry_price) / pos.entry_price
            tp_pct = (pos.entry_price - pos_tp) / pos.entry_price
            should_close_sl = current_price >= pos_sl
            should_close_tp = current_price <= pos_tp
            trailing_stop = highest * (1 + self.trailing_stop_pct)
            should_close_trail = current_price > trailing_stop and highest < pos.entry_price * 0.995
            should_close_stale = (position_age > self.stale_position_threshold
                                  and abs(pnl_pct) < self.stale_pnl_threshold)
            should_close_timeout = position_age > self.max_position_duration

        should_close = (should_close_sl or should_close_tp or should_close_trail
                        or should_close_stale or should_close_timeout)

        if should_close:
            if should_close_sl:
                reason = "SL"
            elif should_close_tp:
                reason = "TP"
            elif should_close_trail:
                reason = "TRAIL"
            elif should_close_timeout:
                reason = "TIMEOUT"
            elif should_close_stale:
                reason = "STALE"
            else:
                reason = "UNKNOWN"

            realized = pos.calculate_unrealized_pnl(current_price)
            self.trading_engine.close_position(symbol)
            self.total_trades += 1

            if coin in self.position_highest:
                del self.position_highest[coin]
            if coin in self.position_entry_time:
                del self.position_entry_time[coin]
            if coin in self.position_sl:
                del self.position_sl[coin]
            if coin in self.position_tp:
                del self.position_tp[coin]

            emoji = "+" if realized > 0 else ""
            logger.info(
                f"  CLOSED {coin} {reason} | PnL: {emoji}{realized:.4f} USDT "
                f"({pnl_pct*100:+.2f}%) | Age: {position_age:.0f}s | Bal: {self.trading_engine.balance:.2f}"
            )

            self._record_trade_to_state(coin, pos, realized, reason)

    def _record_trade_to_state(self, coin: str, pos, realized: float, reason: str):
        try:
            exit_price = self.current_prices.get(coin, pos.entry_price)
            if pos.size > 0 and pos.entry_price > 0:
                pnl_pct_val = (realized / (pos.entry_price * pos.size)) * 100
            else:
                pnl_pct_val = 0.0

            trade = TradeRecord(
                trade_id=f"T{int(time.time()*1000)}",
                symbol=f"{coin}-PERP",
                side="long" if pos.side == OrderSide.BUY else "short",
                entry_time=pos.timestamp,
                exit_time=time.time(),
                entry_price=pos.entry_price,
                exit_price=exit_price,
                size=pos.size,
                leverage=pos.leverage,
                pnl=realized,
                pnl_pct=pnl_pct_val,
                exit_reason=reason,
                strategy=self._last_signal_strategy.get(coin, "unknown"),
            )
            self.state_manager.add_trade(trade)

            if hasattr(self, '_strategy_tracker') and self._strategy_tracker:
                last_strategy = self._last_signal_strategy.get(coin, "unknown")
                self._strategy_tracker.record_trade(
                    strategy_name=last_strategy,
                    coin=coin,
                    side="long" if pos.side == OrderSide.BUY else "short",
                    pnl=realized,
                    pnl_pct=pnl_pct_val,
                    exit_reason=reason,
                    duration=time.time() - pos.timestamp,
                )
        except Exception as e:
            logger.error(f"Error recording trade: {e}")

    def _compute_position_size(self, symbol: str, entry_price: float, stop_price: float) -> float:
        balance = self.trading_engine.get_available_balance()
        risk_amount = balance * self.max_risk_per_trade_pct
        risk_per_unit = abs(entry_price - stop_price)
        if risk_per_unit <= 0:
            return 0.0
        size = risk_amount / risk_per_unit
        max_notional = balance * 0.3
        if size * entry_price > max_notional:
            size = max_notional / entry_price
        return size

    def check_opportunities(self):
        self.iteration_count += 1
        logger.info(f"--- Iteration {self.iteration_count} ---")

        target_coins = [s.replace("-PERP", "") for s in self.symbols]
        available_prices = {c: p for c, p in self.current_prices.items() if c in target_coins}

        if not available_prices:
            logger.info("Waiting for price data...")
            return

        price_str = " | ".join(f"{c}=${p:,.2f}" for c, p in available_prices.items())
        logger.info(f"Prices: {price_str}")

        open_count = len(self.trading_engine.positions)
        logger.info(
            f"Balance: {self.trading_engine.balance:.2f} | "
            f"Equity: {self.trading_engine.get_balance():.2f} | "
            f"Open: {open_count}/{self.max_open_positions} | "
            f"Trades: {self.total_trades} | Signals: {self.total_signals}"
        )

        if open_count >= self.max_open_positions:
            logger.info("Max positions reached, managing existing")
            return

        balance = self.trading_engine.balance
        if balance < 5.0:
            logger.warning("Balance too low for new trades")
            return

        drawdown = 1.0 - (self.trading_engine.get_balance() / self.trading_engine.stats.get('peak_balance', balance))
        if drawdown > self.max_drawdown_pct:
            logger.warning(f"Max drawdown hit ({drawdown*100:.1f}%), pausing new trades")
            return

        available_slots = self.max_open_positions - open_count
        coin_signals: Dict[str, Tuple[TradingSignal, str, float]] = {}

        active_strategies = self.strategies
        if self._self_improver and self._self_improver.strategy_lab:
            active_strategies = self._self_improver.strategy_lab.evaluate_strategies(self.strategies)

        for coin in target_coins:
            if coin not in available_prices:
                continue

            symbol = f"{coin}-PERP"
            if symbol in self.trading_engine.positions:
                continue

            df = self.candle_builder.get_ohlcv_df(coin, min_candles=15)
            if df is None:
                candle_count = len(self.candle_builder.candles.get(coin, []))
                logger.debug(f"  {coin}: only {candle_count} candles, need 15+")
                continue

            current_price = available_prices[coin]

            for strategy in active_strategies:
                try:
                    signal = strategy.generate_signal(
                        symbol=symbol,
                        ohlcv=df,
                        current_price=current_price,
                        account_balance=balance,
                    )
                    if signal:
                        existing_conf = coin_signals.get(coin, (None, "", 0.0))[2]
                        if signal.confidence > existing_conf:
                            coin_signals[coin] = (signal, getattr(strategy, 'name', strategy.__class__.__name__), signal.confidence)
                except Exception as e:
                    logger.debug(f"Strategy {strategy.name} error for {coin}: {e}")

        sorted_signals = sorted(coin_signals.items(), key=lambda x: x[1][2], reverse=True)

        executed = 0
        for coin, (signal, strategy_name, confidence) in sorted_signals:
            if executed >= available_slots:
                break
            if confidence >= 0.40:
                self._execute_signal(signal, strategy_name=strategy_name)
                executed += 1

        remaining_slots = available_slots - executed
        if remaining_slots > 0:
            logger.info(f"  {remaining_slots} empty slots, waiting for strategy signals")

        if executed == 0 and remaining_slots <= 0:
            logger.info("No high-confidence signals found")

    def _auto_enter_positions(self, target_coins: List[str], available_prices: Dict[str, float],
                               balance: float, max_entries: int):
        entered = 0
        for coin in target_coins:
            if entered >= max_entries:
                break
            symbol = f"{coin}-PERP"
            if symbol in self.trading_engine.positions:
                continue
            if coin not in available_prices:
                continue

            current_price = available_prices[coin]

            df = self.candle_builder.get_ohlcv_df(coin, min_candles=5)
            ema20 = current_price
            ema50 = current_price
            if df is not None and len(df) >= 5:
                closes = df['close']
                if len(closes) >= 20:
                    ema20 = closes.rolling(20).mean().iloc[-1]
                if len(closes) >= 50:
                    ema50 = closes.rolling(50).mean().iloc[-1]

            if ema20 > ema50 or (ema20 == ema50 and df is None):
                side = SignalType.BUY
                sl = current_price * 0.997
                tp = current_price * 1.006
                rationale = f"Auto-LONG: EMA20={ema20:.2f} > EMA50={ema50:.2f}"
            elif ema20 < ema50:
                side = SignalType.SELL
                sl = current_price * 1.003
                tp = current_price * 0.994
                rationale = f"Auto-SHORT: EMA20={ema20:.2f} < EMA50={ema50:.2f}"
            else:
                continue

            size = (balance * 0.10) / current_price if balance > 0 else 0
            if size <= 0:
                continue

            logger.info(f"  Auto-entering {side.value} {coin} @ ${current_price:.2f} | EMA20={ema20:.2f} EMA50={ema50:.2f}")

            signal = TradingSignal(
                symbol=symbol, signal_type=side,
                confidence=0.65, suggested_leverage=20.0,
                suggested_size=size, entry_price=current_price,
                stop_loss=sl, take_profit=tp,
                rationale=rationale,
            )
            self._execute_signal(signal, strategy_name="Auto_Trend", skip_trend_filter=True)
            entered += 1

    def _execute_signal(self, signal: TradingSignal, strategy_name: str = "unknown", skip_trend_filter: bool = False):
        self.total_signals += 1
        coin = signal.symbol.replace("-PERP", "")
        current_price = self.current_prices.get(coin, signal.entry_price or 0)

        if current_price <= 0:
            return

        if not skip_trend_filter and not self._check_trend_filter(signal, coin):
            return

        stop_price = signal.stop_loss or (
            current_price * (1 - self.stop_loss_pct) if signal.signal_type == SignalType.BUY
            else current_price * (1 + self.stop_loss_pct)
        )

        take_profit = signal.take_profit or (
            current_price * (1 + self.take_profit_pct) if signal.signal_type == SignalType.BUY
            else current_price * (1 - self.take_profit_pct)
        )

        size = self._compute_position_size(signal.symbol, current_price, stop_price)
        if size <= 0:
            logger.info(f"  Signal for {coin} skipped: size too small")
            return

        leverage = min(signal.suggested_leverage, 20.0)

        side = OrderSide.BUY if signal.signal_type == SignalType.BUY else OrderSide.SELL

        try:
            order = self.trading_engine.place_order(
                symbol=signal.symbol,
                side=side,
                size=size,
                order_type=OrderType.MARKET,
                leverage=leverage,
            )

            self.position_highest[coin] = current_price
            self.position_entry_time[coin] = time.time()
            self.position_sl[coin] = stop_price
            self.position_tp[coin] = take_profit
            self._last_signal_strategy[coin] = strategy_name

            direction = "LONG" if side == OrderSide.BUY else "SHORT"
            sl_pct = abs(stop_price - current_price) / current_price * 100
            tp_pct = abs(take_profit - current_price) / current_price * 100
            logger.info(
                f"  >> OPENED {direction} {coin} | "
                f"Size: {size:.6f} @ ${current_price:,.2f} | "
                f"Lev: {leverage}x | Conf: {signal.confidence:.0%} | "
                f"SL: {sl_pct:.1f}% TP: {tp_pct:.1f}% | "
                f"Strategy: {strategy_name} | "
                f"{signal.rationale}"
            )

            pos = PositionState(
                symbol=signal.symbol,
                side="long" if side == OrderSide.BUY else "short",
                size=size,
                entry_price=current_price,
                current_price=current_price,
                leverage=leverage,
                stop_loss=stop_price,
                take_profit=take_profit,
            )
            self.state_manager.add_position(pos)

        except ValueError as e:
            logger.info(f"  Signal for {coin} rejected: {e}")
        except Exception as e:
            logger.error(f"  Order error for {coin}: {e}")

    def _check_trend_filter(self, signal: TradingSignal, coin: str) -> bool:
        df = self.candle_builder.get_ohlcv_df(coin, min_candles=30)
        if df is None or len(df) < 30:
            return True

        closes = df['close']
        ema50 = closes.rolling(50).mean().iloc[-1] if len(closes) >= 50 else None
        ema20 = closes.rolling(20).mean().iloc[-1] if len(closes) >= 20 else None

        if ema20 is not None and ema50 is not None:
            if signal.signal_type == SignalType.SELL and ema20 > ema50 * 1.001:
                confidence_penalty = 0.15
                signal.confidence = max(0.0, signal.confidence - confidence_penalty)
                if signal.confidence < 0.45:
                    return False
            elif signal.signal_type == SignalType.BUY and ema20 < ema50 * 0.999:
                confidence_penalty = 0.15
                signal.confidence = max(0.0, signal.confidence - confidence_penalty)
                if signal.confidence < 0.45:
                    return False

        return True

    def run(self):
        logger.info("Starting Moonshot Daemon main loop")

        self.running = True
        self.iteration_count = 0

        if self.ws_client:
            self.ws_client.start()

            logger.info("Waiting for WebSocket connection...")
            timeout = 10
            start = time.time()
            while not self.ws_client.connected and time.time() - start < timeout:
                time.sleep(0.1)

            if not self.ws_client.connected:
                logger.error("Failed to connect to Hyperliquid within timeout")
                self.running = False
                return

            logger.info("WebSocket connected, starting main loop")

        warmup_start = time.time()
        logger.info("Warming up price data (120s for 60s candles)...")
        while self.running and time.time() - warmup_start < 120:
            time.sleep(1)
        logger.info(f"Warmup done. Prices: {len(self.current_prices)} coins")

        try:
            while self.running:
                loop_start = time.time()

                try:
                    self.check_opportunities()
                except Exception as e:
                    logger.error(f"Error in opportunity check: {e}", exc_info=True)

                if self.iteration_count % 10 == 0:
                    self._print_summary()

                if self._self_improver and time.time() - self._last_improvement_time > self._improvement_interval:
                    try:
                        self._run_self_improvement()
                        self._last_improvement_time = time.time()
                    except Exception as e:
                        logger.error(f"Error in self-improvement: {e}", exc_info=True)

                if time.time() - self._last_backtest_time > self._backtest_interval:
                    try:
                        self._run_rolling_backtest()
                        self._last_backtest_time = time.time()
                    except Exception as e:
                        logger.error(f"Error in rolling backtest: {e}", exc_info=True)

                elapsed = time.time() - loop_start
                sleep_time = max(0, self.check_interval - elapsed)

                if sleep_time > 0:
                    slept = 0
                    while slept < sleep_time and self.running:
                        time.sleep(min(1, sleep_time - slept))
                        slept += 1

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
        finally:
            self.running = False
            logger.info("Moonshot Daemon main loop stopped")

    def _print_summary(self):
        stats = self.trading_engine.get_stats_summary()
        strategy_summary = ""
        if self._strategy_tracker:
            strategy_summary = self._strategy_tracker.get_summary_str()
        logger.info(
            f"=== SUMMARY | Bal: {stats['balance']:.2f} | "
            f"Return: {stats['total_return_pct']:+.2f}% | "
            f"Trades: {stats['total_trades']} | "
            f"Win: {stats['win_rate']:.0f}% | "
            f"DD: {stats['max_drawdown_pct']:.1f}% | "
            f"Positions: {stats['current_positions']} ==="
        )
        if strategy_summary:
            logger.info(f"  STRATEGIES: {strategy_summary}")

    def _run_self_improvement(self):
        if not self._self_improver:
            return
        logger.info("Running self-improvement cycle...")
        stats = self.trading_engine.get_stats_summary()
        improvement_result = self._self_improver.run_improvement_cycle(
            current_stats=stats,
            trading_engine=self.trading_engine,
        )
        if improvement_result.get("changes_made"):
            for change in improvement_result["changes_made"]:
                logger.info(f"  IMPROVEMENT: {change}")
            self._apply_strategy_updates()
        if improvement_result.get("should_notify_opencode"):
            logger.info("  Triggering Opencode feedback for deeper analysis...")
            self._trigger_opencode_feedback(stats, improvement_result)

    def _run_rolling_backtest(self):
        if not self._strategy_tracker:
            return
        logger.info("Running rolling backtest on accumulated data...")
        results = {}
        for coin in [s.replace("-PERP", "") for s in self.symbols]:
            df = self.candle_builder.get_ohlcv_df(coin, min_candles=30)
            if df is None or len(df) < 30:
                continue
            current_price = self.current_prices.get(coin, 0)
            if current_price <= 0:
                continue
            for strategy in self.strategies:
                try:
                    signal = strategy.generate_signal(
                        symbol=f"{coin}-PERP",
                        ohlcv=df,
                        current_price=current_price,
                        account_balance=self.trading_engine.balance,
                    )
                    results[f"{coin}_{getattr(strategy, 'name', 'unknown')}"] = {
                        "signal": signal.signal_type.value if signal else "neutral",
                        "confidence": signal.confidence if signal else 0,
                    }
                except Exception:
                    pass
        if results:
            logger.info(f"  Rolling backtest: {len(results)} strategy-coin pairs evaluated")

    def _apply_strategy_updates(self):
        if not self._self_improver:
            return
        updates = self._self_improver.get_strategy_updates()
        for strategy_name, new_params in updates.items():
            for strategy in self.strategies:
                sname = getattr(strategy, 'name', strategy.__class__.__name__)
                if sname == strategy_name:
                    for param, value in new_params.items():
                        if hasattr(strategy, param):
                            old_value = getattr(strategy, param)
                            if old_value != value:
                                setattr(strategy, param, value)
                                logger.info(f"  Updated {sname}.{param}: {old_value} -> {value}")

    def _trigger_opencode_feedback(self, stats, improvement_result):
        try:
            from moonshot.daemon.self_improvement import OpencodeFeedback
            feedback = OpencodeFeedback(data_dir="state/moonshot")
            feedback.request_improvement(
                stats=stats,
                improvement_result=improvement_result,
                strategy_performance=self._strategy_tracker.get_all_performance() if self._strategy_tracker else {},
            )
        except Exception as e:
            logger.error(f"Opencode feedback failed: {e}")

    def stop(self):
        logger.info("Stopping Moonshot Daemon...")
        self.running = False

        if self.ws_client:
            self.ws_client.stop()

        self._print_summary()

        if self.state_manager:
            self.state_manager.stop_auto_save()

        logger.info("Moonshot Daemon stopped")

    def get_status(self) -> Dict:
        return {
            'running': self.running,
            'iteration_count': self.iteration_count,
            'websocket_connected': self.ws_client.connected if self.ws_client else False,
            'prices_available': len(self.current_prices),
            'current_prices': self.current_prices,
            'total_signals': self.total_signals,
            'total_trades': self.total_trades,
            'timestamp': time.time()
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Moonshot 24/7 Trading Daemon')
    parser.add_argument('--balance', type=float, default=100.0, help='Initial balance')
    parser.add_argument('--interval', type=float, default=60.0, help='Check interval in seconds')
    parser.add_argument('--symbols', nargs='+', default=['BTC-PERP', 'ETH-PERP', 'SOL-PERP'])
    args = parser.parse_args()

    daemon = MoonshotDaemon(
        initial_balance=args.balance,
        symbols=args.symbols,
        check_interval=args.interval
    )

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
