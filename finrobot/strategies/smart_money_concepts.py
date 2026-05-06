"""
Smart Money Concepts (SMC) Module
Detects Order Blocks, Fair Value Gaps (FVG), Liquidity Sweeps, and Breaker Blocks
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class OrderBlock:
    """Represents a Bullish or Bearish Order Block"""
    type: str  # 'bullish' or 'bearish'
    index: int
    open_time: pd.Timestamp
    high: float
    low: float
    open: float
    close: float
    volume: float
    strength: float  # 0-1 score based on volume and price action


@dataclass
class FairValueGap:
    """Represents a Fair Value Gap (Imbalance)"""
    type: str  # 'bullish' or 'bearish'
    index: int
    open_time: pd.Timestamp
    top: float
    bottom: float
    size: float
    filled: bool = False


@dataclass
class LiquiditySweep:
    """Represents a Liquidity Sweep (Stop Hunt)"""
    type: str  # 'bullish' or 'bearish'
    index: int
    open_time: pd.Timestamp
    level: float
    swept_high: float
    swept_low: float
    strength: float


class SmartMoneyConcepts:
    """
    Detects Smart Money Concepts from price action
    """
    
    def __init__(self, 
                 ob_lookback: int = 5,
                 fvg_min_size: float = 0.001,
                 sweep_lookback: int = 10):
        self.ob_lookback = ob_lookback
        self.fvg_min_size = fvg_min_size  # Minimum FVG size as percentage
        self.sweep_lookback = sweep_lookback
        
    def detect_order_blocks(self, df: pd.DataFrame) -> List[OrderBlock]:
        """
        Detect Bullish and Bearish Order Blocks
        
        Bullish OB: Bearish candle before strong bullish move
        Bearish OB: Bullish candle before strong bearish move
        """
        order_blocks = []
        
        for i in range(self.ob_lookback, len(df) - 1):
            # Get current and previous candles
            prev = df.iloc[i-1]
            curr = df.iloc[i]
            next_c = df.iloc[i+1]
            
            # Check for Bullish Order Block
            # Pattern: Bearish candle followed by strong bullish move
            if prev['close'] < prev['open']:  # Bearish previous
                move_size = (next_c['close'] - curr['close']) / curr['close']
                if move_size > 0.005:  # 0.5% move
                    strength = self._calculate_ob_strength(prev, curr, next_c, df.iloc[i-2] if i > 1 else None)
                    order_blocks.append(OrderBlock(
                        type='bullish',
                        index=i-1,
                        open_time=prev.name if isinstance(prev.name, pd.Timestamp) else df.index[i-1],
                        high=prev['high'],
                        low=prev['low'],
                        open=prev['open'],
                        close=prev['close'],
                        volume=prev['volume'],
                        strength=strength
                    ))
            
            # Check for Bearish Order Block
            # Pattern: Bullish candle followed by strong bearish move
            if prev['close'] > prev['open']:  # Bullish previous
                move_size = (curr['close'] - next_c['close']) / curr['close']
                if move_size > 0.005:  # 0.5% move
                    strength = self._calculate_ob_strength(prev, curr, next_c, df.iloc[i-2] if i > 1 else None)
                    order_blocks.append(OrderBlock(
                        type='bearish',
                        index=i-1,
                        open_time=prev.name if isinstance(prev.name, pd.Timestamp) else df.index[i-1],
                        high=prev['high'],
                        low=prev['low'],
                        open=prev['open'],
                        close=prev['close'],
                        volume=prev['volume'],
                        strength=strength
                    ))
        
        # Sort by strength and keep only the strongest
        order_blocks.sort(key=lambda x: x.strength, reverse=True)
        return order_blocks[:20]  # Keep top 20 strongest
    
    def _calculate_ob_strength(self, prev, curr, next_c, prev2=None) -> float:
        """Calculate the strength of an order block"""
        strength = 0.5  # Base strength
        
        # Volume factor
        if prev2 is not None:
            vol_ratio = prev['volume'] / (prev2['volume'] + 1e-10)
            strength += min(0.2, vol_ratio * 0.1)
        
        # Price action factor
        body_size = abs(prev['close'] - prev['open']) / (prev['high'] - prev['low'] + 1e-10)
        strength += body_size * 0.15
        
        # Momentum factor
        move_size = abs(next_c['close'] - curr['close']) / curr['close']
        strength += min(0.2, move_size * 10)
        
        return min(1.0, strength)
    
    def detect_fair_value_gaps(self, df: pd.DataFrame) -> List[FairValueGap]:
        """
        Detect Fair Value Gaps (FVGs) / Imbalances
        
        Bullish FVG: Current low > previous high (gap up)
        Bearish FVG: Current high < previous low (gap down)
        """
        fvgs = []
        
        for i in range(2, len(df)):
            prev = df.iloc[i-2]
            curr = df.iloc[i]
            
            # Bullish FVG
            gap_size = curr['low'] - prev['high']
            if gap_size > 0:
                size_pct = gap_size / prev['close']
                if size_pct >= self.fvg_min_size:
                    fvgs.append(FairValueGap(
                        type='bullish',
                        index=i,
                        open_time=df.index[i],
                        top=curr['low'],
                        bottom=prev['high'],
                        size=gap_size
                    ))
            
            # Bearish FVG
            gap_size = prev['low'] - curr['high']
            if gap_size > 0:
                size_pct = gap_size / prev['close']
                if size_pct >= self.fvg_min_size:
                    fvgs.append(FairValueGap(
                        type='bearish',
                        index=i,
                        open_time=df.index[i],
                        top=prev['low'],
                        bottom=curr['high'],
                        size=gap_size
                    ))
        
        return fvgs
    
    def detect_liquidity_sweeps(self, df: pd.DataFrame, 
                                lookback: int = 10) -> List[LiquiditySweep]:
        """
        Detect Liquidity Sweeps (Stop Hunts)
        
        Bullish Sweep: Price takes out recent lows, then reverses up
        Bearish Sweep: Price takes out recent highs, then reverses down
        """
        sweeps = []
        
        for i in range(lookback, len(df) - 1):
            window = df.iloc[i-lookback:i]
            curr = df.iloc[i]
            next_c = df.iloc[i+1]
            
            recent_high = window['high'].max()
            recent_low = window['low'].min()
            
            # Bullish Liquidity Sweep
            # Price takes out recent low, then reverses up strongly
            if curr['low'] < recent_low and next_c['close'] > curr['close']:
                reversal_strength = (next_c['close'] - curr['low']) / (curr['high'] - curr['low'] + 1e-10)
                if reversal_strength > 0.6:  # Strong reversal
                    strength = self._calculate_sweep_strength(curr, next_c, window)
                    sweeps.append(LiquiditySweep(
                        type='bullish',
                        index=i,
                        open_time=df.index[i],
                        level=recent_low,
                        swept_high=curr['high'],
                        swept_low=curr['low'],
                        strength=strength
                    ))
            
            # Bearish Liquidity Sweep
            # Price takes out recent high, then reverses down strongly
            if curr['high'] > recent_high and next_c['close'] < curr['close']:
                reversal_strength = (curr['high'] - next_c['close']) / (curr['high'] - curr['low'] + 1e-10)
                if reversal_strength > 0.6:  # Strong reversal
                    strength = self._calculate_sweep_strength(curr, next_c, window)
                    sweeps.append(LiquiditySweep(
                        type='bearish',
                        index=i,
                        open_time=df.index[i],
                        level=recent_high,
                        swept_high=curr['high'],
                        swept_low=curr['low'],
                        strength=strength
                    ))
        
        return sweeps
    
    def _calculate_sweep_strength(self, curr, next_c, window) -> float:
        """Calculate the strength of a liquidity sweep"""
        strength = 0.5
        
        # Volume spike
        avg_volume = window['volume'].mean()
        if curr['volume'] > avg_volume * 1.5:
            strength += 0.15
        
        # Reversal strength
        if next_c['close'] > curr['open']:
            reversal = (next_c['close'] - curr['low']) / (curr['high'] - curr['low'] + 1e-10)
        else:
            reversal = (curr['high'] - next_c['close']) / (curr['high'] - curr['low'] + 1e-10)
        strength += reversal * 0.2
        
        return min(1.0, strength)
    
    def get_trading_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on SMC concepts
        Returns DataFrame with signal columns
        """
        signals = pd.DataFrame(index=df.index)
        signals['signal'] = 0  # 0 = none, 1 = buy, -1 = sell
        signals['confidence'] = 0.0
        signals['setup_type'] = ''
        
        # Detect all SMC components
        obs = self.detect_order_blocks(df)
        fvgs = self.detect_fair_value_gaps(df)
        sweeps = self.detect_liquidity_sweeps(df)
        
        # Mark order block signals
        for ob in obs:
            idx = df.index[ob.index]
            if ob.type == 'bullish' and ob.strength > 0.7:
                signals.loc[idx, 'signal'] = 1
                signals.loc[idx, 'confidence'] = ob.strength
                signals.loc[idx, 'setup_type'] = 'OB_Bullish'
            elif ob.type == 'bearish' and ob.strength > 0.7:
                signals.loc[idx, 'signal'] = -1
                signals.loc[idx, 'confidence'] = ob.strength
                signals.loc[idx, 'setup_type'] = 'OB_Bearish'
        
        # Mark liquidity sweep signals (high confidence)
        for sweep in sweeps:
            if sweep.strength > 0.75:
                idx = df.index[sweep.index]
                signals.loc[idx, 'signal'] = 1 if sweep.type == 'bullish' else -1
                signals.loc[idx, 'confidence'] = sweep.strength
                signals.loc[idx, 'setup_type'] = f'Sweep_{sweep.type}'
        
        return signals
