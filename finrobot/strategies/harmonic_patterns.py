"""
Harmonic Pattern Detection Module
Detects classic harmonic patterns: Gartley, Bat, Butterfly, Crab, Shark, Cypher
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class HarmonicPattern(Enum):
    GARTLEY = "gartley"
    BAT = "bat"
    BUTTERFLY = "butterfly"
    CRAB = "crab"
    SHARK = "shark"
    CYPHER = "cypher"


@dataclass
class HarmonicSignal:
    """Represents a detected harmonic pattern"""
    pattern: HarmonicPattern
    type: str  # 'bullish' or 'bearish'
    start_idx: int
    x_point: Tuple[int, float]  # (index, price)
    a_point: Tuple[int, float]
    b_point: Tuple[int, float]
    c_point: Tuple[int, float]
    d_point: Tuple[int, float]
    completion_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    confidence: float
    fib_ratios: Dict[str, float]


class HarmonicPatternDetector:
    """
    Detects harmonic patterns in price data
    
    Pattern Fibonacci ratios:
    - Gartley: XA=1, AB=0.618, BC=0.382-0.886, CD=1.27-1.618, XD=0.786
    - Bat: XA=1, AB=0.382-0.5, BC=0.382-0.886, CD=1.618-2.618, XD=0.886
    - Butterfly: XA=1, AB=0.786, BC=0.382-0.886, CD=1.618-2.24, XD=1.27
    - Crab: XA=1, AB=0.382-0.618, BC=0.382-0.886, CD=2.24-3.618, XD=1.618
    - Shark: XA=1, AB=1.13-1.618, BC=1.618-2.24, CD=0.886-1.13, XD=0.886-1.13
    - Cypher: XA=1, AB=0.382-0.618, BC=1.13-1.414, CD=1.27-2.0, XD=0.786
    """
    
    def __init__(self, tolerance: float = 0.05):
        self.tolerance = tolerance  # Tolerance for Fib ratio matching
        
        # Define pattern specifications
        self.pattern_specs = {
            HarmonicPattern.GARTLEY: {
                'AB': (0.618 - tolerance, 0.618 + tolerance),
                'BC': (0.382 - tolerance, 0.886 + tolerance),
                'CD': (1.27 - tolerance, 1.618 + tolerance),
                'XD': (0.786 - tolerance, 0.786 + tolerance),
            },
            HarmonicPattern.BAT: {
                'AB': (0.382 - tolerance, 0.5 + tolerance),
                'BC': (0.382 - tolerance, 0.886 + tolerance),
                'CD': (1.618 - tolerance, 2.618 + tolerance),
                'XD': (0.886 - tolerance, 0.886 + tolerance),
            },
            HarmonicPattern.BUTTERFLY: {
                'AB': (0.786 - tolerance, 0.786 + tolerance),
                'BC': (0.382 - tolerance, 0.886 + tolerance),
                'CD': (1.618 - tolerance, 2.24 + tolerance),
                'XD': (1.27 - tolerance, 1.27 + tolerance),
            },
            HarmonicPattern.CRAB: {
                'AB': (0.382 - tolerance, 0.618 + tolerance),
                'BC': (0.382 - tolerance, 0.886 + tolerance),
                'CD': (2.24 - tolerance, 3.618 + tolerance),
                'XD': (1.618 - tolerance, 1.618 + tolerance),
            },
            HarmonicPattern.SHARK: {
                'AB': (1.13 - tolerance, 1.618 + tolerance),
                'BC': (1.618 - tolerance, 2.24 + tolerance),
                'CD': (0.886 - tolerance, 1.13 + tolerance),
                'XD': (0.886 - tolerance, 1.13 + tolerance),
            },
            HarmonicPattern.CYPHER: {
                'AB': (0.382 - tolerance, 0.618 + tolerance),
                'BC': (1.13 - tolerance, 1.414 + tolerance),
                'CD': (1.27 - tolerance, 2.0 + tolerance),
                'XD': (0.786 - tolerance, 0.786 + tolerance),
            },
        }
    
    def detect_patterns(self, df: pd.DataFrame) -> List[HarmonicSignal]:
        """
        Detect all harmonic patterns in the price data
        """
        signals = []
        
        # Find significant swing points
        swing_points = self._find_swing_points(df)
        
        if len(swing_points) < 5:
            logger.warning("Not enough swing points to detect patterns")
            return signals
        
        # Try to match patterns using 5 consecutive swing points (X, A, B, C, D)
        for i in range(len(swing_points) - 4):
            x_idx, x_price = swing_points[i]
            a_idx, a_price = swing_points[i+1]
            b_idx, b_price = swing_points[i+2]
            c_idx, c_price = swing_points[i+3]
            d_idx, d_price = swing_points[i+4]
            
            # Calculate Fibonacci ratios
            xa = abs(a_price - x_price)
            ab = abs(b_price - a_price)
            bc = abs(c_price - b_price)
            cd = abs(d_price - c_price)
            xd = abs(d_price - x_price)
            
            if xa == 0:
                continue
                
            ab_xa = ab / xa
            bc_ab = bc / ab if ab > 0 else 0
            cd_bc = cd / bc if bc > 0 else 0
            xd_xa = xd / xa
            
            fib_ratios = {
                'AB/XA': ab_xa,
                'BC/AB': bc_ab,
                'CD/BC': cd_bc,
                'XD/XA': xd_xa
            }
            
            # Check each pattern
            for pattern_type, specs in self.pattern_specs.items():
                if self._check_pattern_match(fib_ratios, specs):
                    # Determine if bullish or bearish
                    is_bullish = a_price > x_price
                    
                    # Calculate targets and stop loss
                    if is_bullish:
                        completion_price = d_price
                        stop_loss = d_price - (xa * 0.382)
                        take_profit_1 = d_price + (xa * 0.618)
                        take_profit_2 = d_price + xa
                    else:
                        completion_price = d_price
                        stop_loss = d_price + (xa * 0.382)
                        take_profit_1 = d_price - (xa * 0.618)
                        take_profit_2 = d_price - xa
                    
                    # Calculate confidence based on how well ratios match
                    confidence = self._calculate_confidence(fib_ratios, specs)
                    
                    signal = HarmonicSignal(
                        pattern=pattern_type,
                        type='bullish' if is_bullish else 'bearish',
                        start_idx=x_idx,
                        x_point=(x_idx, x_price),
                        a_point=(a_idx, a_price),
                        b_point=(b_idx, b_price),
                        c_point=(c_idx, c_price),
                        d_point=(d_idx, d_price),
                        completion_price=completion_price,
                        stop_loss=stop_loss,
                        take_profit_1=take_profit_1,
                        take_profit_2=take_profit_2,
                        confidence=confidence,
                        fib_ratios=fib_ratios
                    )
                    
                    signals.append(signal)
        
        # Sort by confidence
        signals.sort(key=lambda x: x.confidence, reverse=True)
        return signals
    
    def _find_swing_points(self, df: pd.DataFrame, 
                           window: int = 5,
                           min_swing_pct: float = 0.001) -> List[Tuple[int, float]]:
        """
        Find significant swing highs and lows
        Returns list of (index, price) tuples
        """
        swings = []
        
        for i in range(window, len(df) - window):
            current = df.iloc[i]
            
            # Check for swing high
            is_swing_high = True
            for j in range(1, window + 1):
                if df.iloc[i-j]['high'] >= current['high'] or df.iloc[i+j]['high'] >= current['high']:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swing_size = current['high'] - df.iloc[i-window:i]['low'].min()
                if swing_size / current['close'] >= min_swing_pct:
                    swings.append((i, current['high']))
                    continue
            
            # Check for swing low
            is_swing_low = True
            for j in range(1, window + 1):
                if df.iloc[i-j]['low'] <= current['low'] or df.iloc[i+j]['low'] <= current['low']:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing_size = df.iloc[i-window:i]['high'].max() - current['low']
                if swing_size / current['close'] >= min_swing_pct:
                    swings.append((i, current['low']))
        
        # Sort by index
        swings.sort(key=lambda x: x[0])
        return swings
    
    def _check_pattern_match(self, fib_ratios: Dict[str, float], 
                             specs: Dict[str, Tuple[float, float]]) -> bool:
        """
        Check if Fibonacci ratios match the pattern specifications
        """
        for ratio_name, (min_val, max_val) in specs.items():
            if ratio_name not in fib_ratios:
                return False
            if not (min_val <= fib_ratios[ratio_name] <= max_val):
                return False
        return True
    
    def _calculate_confidence(self, fib_ratios: Dict[str, float],
                             specs: Dict[str, Tuple[float, float]]) -> float:
        """
        Calculate how well the ratios match the ideal pattern
        """
        confidences = []
        
        for ratio_name, (min_val, max_val) in specs.items():
            if ratio_name in fib_ratios:
                ideal = (min_val + max_val) / 2
                actual = fib_ratios[ratio_name]
                deviation = abs(actual - ideal) / (max_val - min_val + 1e-10)
                confidence = max(0, 1 - deviation)
                confidences.append(confidence)
        
        return np.mean(confidences) if confidences else 0.0
