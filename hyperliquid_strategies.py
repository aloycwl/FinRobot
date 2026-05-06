"""
Hyperliquid Moonshot Engine - Aggressive Trading Strategies
High-risk, high-reward strategies for rapid account growth
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SignalType(Enum):
    BUY = "buy"
    SELL = "sell"
    NEUTRAL = "neutral"


@dataclass
class TradingSignal:
    symbol: str
    signal_type: SignalType
    confidence: float  # 0.0 to 1.0
    suggested_leverage: float
    suggested_size: float
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    rationale: str = ""
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            import time
            self.timestamp = time.time()


class TechnicalIndicators:
    """Technical indicators for strategy calculations"""
    
    @staticmethod
    def ema(prices: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def sma(prices: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return prices.rolling(window=period).mean()
    
    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average True Range"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=period).mean()
    
    @staticmethod
    def bollinger_bands(prices: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands - returns upper, middle, lower"""
        middle = TechnicalIndicators.sma(prices, period)
        std = prices.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper, middle, lower
    
    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Average Directional Index"""
        # Calculate +DM and -DM
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        plus_dm[plus_dm <= minus_dm] = 0
        minus_dm[minus_dm <= plus_dm] = 0
        
        # Calculate ATR
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        # Calculate +DI and -DI
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        # Calculate DX and ADX
        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    @staticmethod
    def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD - returns macd_line, signal_line, histogram"""
        ema_fast = TechnicalIndicators.ema(prices, fast)
        ema_slow = TechnicalIndicators.ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema(macd_line, signal)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram


class AggressiveADXScalper:
    """
    Aggressive ADX Momentum Scalping Strategy
    High leverage entries on strong trend confirmations
    """
    
    def __init__(
        self,
        adx_period: int = 14,
        adx_threshold: float = 25.0,
        ema_fast: int = 9,
        ema_slow: int = 21,
        volume_threshold: float = 1.5,
        atr_period: int = 14,
        risk_reward: float = 2.0,
        max_leverage: float = 20.0
    ):
        self.name = "ADX_Momentum_Scalper"
        self.adx_period = adx_period
        self.adx_threshold = adx_threshold
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.volume_threshold = volume_threshold
        self.atr_period = atr_period
        self.risk_reward = risk_reward
        self.max_leverage = max_leverage
        
        # Indicators
        self.indicators = TechnicalIndicators()
    
    def generate_signal(
        self,
        symbol: str,
        ohlcv: pd.DataFrame,
        current_price: float,
        account_balance: float
    ) -> Optional[TradingSignal]:
        """Generate trading signal based on ADX momentum"""
        
        if len(ohlcv) < max(self.adx_period, self.ema_slow) + 10:
            return None
        
        # Calculate indicators
        closes = ohlcv['close']
        highs = ohlcv['high']
        lows = ohlcv['low']
        volumes = ohlcv.get('volume', pd.Series([1] * len(ohlcv)))
        
        # EMAs
        ema_fast = self.indicators.ema(closes, self.ema_fast)
        ema_slow = self.indicators.ema(closes, self.ema_slow)
        
        # ADX
        adx = self.indicators.adx(highs, lows, closes, self.adx_period)
        
        # ATR
        atr = self.indicators.atr(highs, lows, closes, self.atr_period)
        
        # Volume check
        avg_volume = volumes.rolling(window=20).mean().iloc[-1]
        current_volume = volumes.iloc[-1]
        volume_spike = current_volume > (avg_volume * self.volume_threshold)
        
        # Get current values
        current_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 0
        current_atr = atr.iloc[-1] if not pd.isna(atr.iloc[-1]) else current_price * 0.01
        fast_val = ema_fast.iloc[-1]
        slow_val = ema_slow.iloc[-1]
        prev_fast = ema_fast.iloc[-2] if len(ema_fast) > 1 else fast_val
        prev_slow = ema_slow.iloc[-2] if len(ema_slow) > 1 else slow_val
        
        # Check for crossover
        bullish_cross = (prev_fast <= prev_slow) and (fast_val > slow_val)
        bearish_cross = (prev_fast >= prev_slow) and (fast_val < slow_val)
        
        signal = None
        confidence = 0.0
        
        # Bullish signal conditions
        if bullish_cross and current_adx > self.adx_threshold and volume_spike:
            confidence = min(1.0, (current_adx / 50.0) + (0.2 if volume_spike else 0.0))
            
            # Calculate stop loss and take profit
            stop_loss = current_price - (current_atr * 1.5)
            take_profit = current_price + (current_atr * self.risk_reward)
            
            # Calculate position size based on risk
            risk_amount = account_balance * 0.05  # 5% risk per trade
            risk_per_unit = current_price - stop_loss
            position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
            
            # Apply leverage
            max_position_value = account_balance * self.max_leverage
            position_value = position_size * current_price
            
            if position_value > max_position_value:
                position_size = max_position_value / current_price
            
            leverage = min(self.max_leverage, position_value / account_balance)
            
            signal = TradingSignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=confidence,
                suggested_leverage=leverage,
                suggested_size=position_size,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                rationale=f"ADX Momentum Long: ADX={current_adx:.1f}, EMA9/21 cross, volume spike"
            )
        
        # Bearish signal conditions
        elif bearish_cross and current_adx > self.adx_threshold and volume_spike:
            confidence = min(1.0, (current_adx / 50.0) + (0.2 if volume_spike else 0.0))
            
            # Calculate stop loss and take profit
            stop_loss = current_price + (current_atr * 1.5)
            take_profit = current_price - (current_atr * self.risk_reward)
            
            # Calculate position size
            risk_amount = account_balance * 0.05
            risk_per_unit = stop_loss - current_price
            position_size = risk_amount / risk_per_unit if risk_per_unit > 0 else 0
            
            max_position_value = account_balance * self.max_leverage
            position_value = position_size * current_price
            
            if position_value > max_position_value:
                position_size = max_position_value / current_price
            
            leverage = min(self.max_leverage, position_value / account_balance)
            
            signal = TradingSignal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=confidence,
                suggested_leverage=leverage,
                suggested_size=position_size,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                rationale=f"ADX Momentum Short: ADX={current_adx:.1f}, EMA9/21 cross, volume spike"
            )
        
        return signal


class AggressiveCryptoScalper:
    """
    Ultra-aggressive scalping strategy for crypto
    Captures small moves with high frequency
    """
    
    def __init__(
        self,
        ema_fast: int = 3,
        ema_slow: int = 8,
        rsi_period: int = 7,
        rsi_overbought: float = 70,
        rsi_oversold: float = 30,
        volume_threshold: float = 1.3,
        min_move_pct: float = 0.001,  # 0.1%
        max_leverage: float = 50.0
    ):
        self.name = "Aggressive_Scalper"
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.volume_threshold = volume_threshold
        self.min_move_pct = min_move_pct
        self.max_leverage = max_leverage
        
        self.indicators = TechnicalIndicators()
        self.last_trade_time = 0
        self.min_trade_interval = 30  # Minimum 30 seconds between trades
    
    def generate_signal(
        self,
        symbol: str,
        ohlcv: pd.DataFrame,
        current_price: float,
        account_balance: float
    ) -> Optional[TradingSignal]:
        """Generate scalping signals"""
        
        import time
        
        # Check minimum trade interval
        if time.time() - self.last_trade_time < self.min_trade_interval:
            return None
        
        if len(ohlcv) < max(self.ema_slow, self.rsi_period) + 5:
            return None
        
        closes = ohlcv['close']
        highs = ohlcv['high']
        lows = ohlcv['low']
        volumes = ohlcv.get('volume', pd.Series([1] * len(ohlcv)))
        
        # Calculate indicators
        ema_fast = self.indicators.ema(closes, self.ema_fast)
        ema_slow = self.indicators.ema(closes, self.ema_slow)
        rsi = self.indicators.rsi(closes, self.rsi_period)
        
        # Volume analysis
        avg_volume = volumes.rolling(window=20).mean().iloc[-1]
        current_volume = volumes.iloc[-1]
        volume_spike = current_volume > (avg_volume * self.volume_threshold)
        
        # Get current values
        fast_val = ema_fast.iloc[-1]
        slow_val = ema_slow.iloc[-1]
        current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        
        prev_fast = ema_fast.iloc[-2] if len(ema_fast) > 1 else fast_val
        prev_slow = ema_slow.iloc[-2] if len(ema_slow) > 1 else slow_val
        
        # Calculate price change
        price_change_pct = abs(closes.iloc[-1] - closes.iloc[-5]) / closes.iloc[-5] if len(closes) >= 5 else 0
        
        signal = None
        
        # Bullish scalping setup
        if (fast_val > slow_val and prev_fast <= prev_slow and  # EMA cross
            current_rsi < self.rsi_overbought and  # Not overbought
            volume_spike and  # Volume confirmation
            price_change_pct >= self.min_move_pct):  # Sufficient movement
            
            confidence = 0.6 + (0.2 if volume_spike else 0) + (0.1 if current_rsi < 50 else 0)
            confidence = min(1.0, confidence)
            
            stop_loss = current_price * 0.995  # 0.5% stop
            take_profit = current_price * 1.01  # 1% target
            
            # Max position with high leverage
            max_position_value = account_balance * self.max_leverage * 0.9  # Use 90% of available
            position_size = max_position_value / current_price
            
            signal = TradingSignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=confidence,
                suggested_leverage=self.max_leverage,
                suggested_size=position_size,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                rationale=f"Scalp Long: EMA{self.ema_fast}/{self.ema_slow} cross, RSI={current_rsi:.1f}, volume spike"
            )
            
            self.last_trade_time = time.time()
        
        # Bearish scalping setup
        elif (fast_val < slow_val and prev_fast >= prev_slow and  # EMA cross
              current_rsi > self.rsi_oversold and  # Not oversold
              volume_spike and
              price_change_pct >= self.min_move_pct):
            
            confidence = 0.6 + (0.2 if volume_spike else 0) + (0.1 if current_rsi > 50 else 0)
            confidence = min(1.0, confidence)
            
            stop_loss = current_price * 1.005  # 0.5% stop
            take_profit = current_price * 0.99  # 1% target
            
            max_position_value = account_balance * self.max_leverage * 0.9
            position_size = max_position_value / current_price
            
            signal = TradingSignal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=confidence,
                suggested_leverage=self.max_leverage,
                suggested_size=position_size,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                rationale=f"Scalp Short: EMA{self.ema_fast}/{self.ema_slow} cross, RSI={current_rsi:.1f}, volume spike"
            )
            
            self.last_trade_time = time.time()
        
        return signal


class BreakoutHunter:
    """
    High-probability breakout strategy
    Captures explosive moves when price breaks key levels
    """
    
    def __init__(
        self,
        lookback_period: int = 20,
        consolidation_threshold: float = 0.03,  # 3% range
        volume_multiplier: float = 2.0,
        breakout_confirmation: float = 0.005,  # 0.5% beyond level
        ema_filter_period: int = 50,
        max_leverage: float = 30.0
    ):
        self.name = "Breakout_Hunter"
        self.lookback_period = lookback_period
        self.consolidation_threshold = consolidation_threshold
        self.volume_multiplier = volume_multiplier
        self.breakout_confirmation = breakout_confirmation
        self.ema_filter_period = ema_filter_period
        self.max_leverage = max_leverage
        
        self.indicators = TechnicalIndicators()
        self.last_breakout_time = 0
        self.cooldown_period = 300  # 5 minutes between breakouts
    
    def generate_signal(
        self,
        symbol: str,
        ohlcv: pd.DataFrame,
        current_price: float,
        account_balance: float
    ) -> Optional[TradingSignal]:
        """Generate breakout signals"""
        
        import time
        
        # Cooldown check
        if time.time() - self.last_breakout_time < self.cooldown_period:
            return None
        
        if len(ohlcv) < self.lookback_period + self.ema_filter_period:
            return None
        
        highs = ohlcv['high']
        lows = ohlcv['low']
        closes = ohlcv['close']
        volumes = ohlcv.get('volume', pd.Series([1] * len(ohlcv)))
        
        # Find consolidation range
        recent_highs = highs.tail(self.lookback_period)
        recent_lows = lows.tail(self.lookback_period)
        
        resistance = recent_highs.max()
        support = recent_lows.min()
        range_size = (resistance - support) / support
        
        # Check if in consolidation
        in_consolidation = range_size < self.consolidation_threshold
        
        if not in_consolidation:
            return None
        
        # Volume analysis
        avg_volume = volumes.tail(self.lookback_period).mean()
        current_volume = volumes.iloc[-1]
        volume_confirmed = current_volume > (avg_volume * self.volume_multiplier)
        
        # EMA filter
        ema_filter = self.indicators.ema(closes, self.ema_filter_period)
        above_ema = current_price > ema_filter.iloc[-1]
        below_ema = current_price < ema_filter.iloc[-1]
        
        # Breakout detection
        breakout_up = current_price > (resistance * (1 + self.breakout_confirmation))
        breakout_down = current_price < (support * (1 - self.breakout_confirmation))
        
        signal = None
        
        # Bullish breakout
        if breakout_up and volume_confirmed and above_ema:
            self.last_breakout_time = time.time()
            
            confidence = 0.7
            if current_price > ema_filter.iloc[-1] * 1.02:
                confidence += 0.15
            if volume_confirmed:
                confidence += 0.1
            
            stop_loss = support * 0.995  # Just below support
            take_profit = current_price + ((current_price - stop_loss) * 3)  # 3:1 R:R
            
            # Large position with leverage
            max_position_value = account_balance * self.max_leverage * 0.95
            position_size = max_position_value / current_price
            
            signal = TradingSignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=confidence,
                suggested_leverage=self.max_leverage,
                suggested_size=position_size,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                rationale=f"Breakout Long: R/S range {range_size*100:.1f}%, volume {current_volume/avg_volume:.1f}x, EMA50 filter"
            )
        
        # Bearish breakout
        elif breakout_down and volume_confirmed and below_ema:
            self.last_breakout_time = time.time()
            
            confidence = 0.7
            if current_price < ema_filter.iloc[-1] * 0.98:
                confidence += 0.15
            if volume_confirmed:
                confidence += 0.1
            
            stop_loss = resistance * 1.005  # Just above resistance
            take_profit = current_price - ((stop_loss - current_price) * 3)
            
            max_position_value = account_balance * self.max_leverage * 0.95
            position_size = max_position_value / current_price
            
            signal = TradingSignal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=confidence,
                suggested_leverage=self.max_leverage,
                suggested_size=position_size,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                rationale=f"Breakout Short: R/S range {range_size*100:.1f}%, volume {current_volume/avg_volume:.1f}x, EMA50 filter"
            )
        
        return signal


class MeanReversionBandit:
    """
    High-probability mean reversion strategy
    Exploits price extremes with Bollinger Bands and RSI
    """
    
    def __init__(
        self,
        bb_period: int = 20,
        bb_std_dev: float = 2.5,  # Wider bands for crypto
        rsi_period: int = 14,
        rsi_overbought: float = 75,
        rsi_oversold: float = 25,
        volume_threshold: float = 1.2,
        adx_filter_max: float = 20.0,  # Only trade when ADX < 20 (ranging)
        max_leverage: float = 15.0
    ):
        self.name = "Mean_Reversion_Bandit"
        self.bb_period = bb_period
        self.bb_std_dev = bb_std_dev
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.volume_threshold = volume_threshold
        self.adx_filter_max = adx_filter_max
        self.max_leverage = max_leverage
        
        self.indicators = TechnicalIndicators()
        self.last_trade_time = 0
        self.cooldown_period = 180  # 3 minutes
    
    def generate_signal(
        self,
        symbol: str,
        ohlcv: pd.DataFrame,
        current_price: float,
        account_balance: float
    ) -> Optional[TradingSignal]:
        """Generate mean reversion signals"""
        
        import time
        
        # Cooldown
        if time.time() - self.last_trade_time < self.cooldown_period:
            return None
        
        if len(ohlcv) < max(self.bb_period, self.rsi_period) + 10:
            return None
        
        closes = ohlcv['close']
        highs = ohlcv['high']
        lows = ohlcv['low']
        volumes = ohlcv.get('volume', pd.Series([1] * len(ohlcv)))
        
        # Calculate indicators
        upper, middle, lower = self.indicators.bollinger_bands(
            closes, self.bb_period, self.bb_std_dev
        )
        rsi = self.indicators.rsi(closes, self.rsi_period)
        adx = self.indicators.adx(highs, lows, closes, 14)
        
        # Volume check
        avg_volume = volumes.tail(20).mean()
        current_volume = volumes.iloc[-1]
        volume_ok = current_volume > (avg_volume * self.volume_threshold)
        
        # Get current values
        current_upper = upper.iloc[-1]
        current_middle = middle.iloc[-1]
        current_lower = lower.iloc[-1]
        current_rsi = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        current_adx = adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 25
        
        # Check ranging market condition
        is_ranging = current_adx < self.adx_filter_max
        
        signal = None
        
        # Long signal: Price at or below lower band with oversold RSI
        if (current_price <= current_lower * 1.002 and  # Within 0.2% of lower band
            current_rsi < self.rsi_oversold and
            is_ranging and volume_ok):
            
            self.last_trade_time = time.time()
            
            confidence = 0.6 + ((self.rsi_oversold - current_rsi) / 100) * 0.3
            if volume_ok:
                confidence += 0.1
            
            stop_loss = current_lower * 0.995  # Below lower band
            take_profit = current_middle  # Target middle band
            
            position_value = account_balance * self.max_leverage * 0.8
            position_size = position_value / current_price
            
            signal = TradingSignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                confidence=confidence,
                suggested_leverage=self.max_leverage,
                suggested_size=position_size,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                rationale=f"Mean Reversion Long: BB lower touch, RSI={current_rsi:.1f}, ranging market"
            )
        
        # Short signal: Price at or above upper band with overbought RSI
        elif (current_price >= current_upper * 0.998 and  # Within 0.2% of upper band
              current_rsi > self.rsi_overbought and
              is_ranging and volume_ok):
            
            self.last_trade_time = time.time()
            
            confidence = 0.6 + ((current_rsi - self.rsi_overbought) / 100) * 0.3
            if volume_ok:
                confidence += 0.1
            
            stop_loss = current_upper * 1.005  # Above upper band
            take_profit = current_middle  # Target middle band
            
            position_value = account_balance * self.max_leverage * 0.8
            position_size = position_value / current_price
            
            signal = TradingSignal(
                symbol=symbol,
                signal_type=SignalType.SELL,
                confidence=confidence,
                suggested_leverage=self.max_leverage,
                suggested_size=position_size,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                rationale=f"Mean Reversion Short: BB upper touch, RSI={current_rsi:.1f}, ranging market"
            )
        
        return signal


# Export all strategies
__all__ = [
    'AggressiveADXScalper',
    'AggressiveCryptoScalper', 
    'BreakoutHunter',
    'MeanReversionBandit',
    'TradingSignal',
    'SignalType',
    'TechnicalIndicators'
]