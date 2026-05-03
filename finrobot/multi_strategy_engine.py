"""
Multi-Strategy Trading Engine with Continuous Optimization
Combines Grid, Martingale, HFT, Smart Money Concepts, and Harmonic Patterns
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
import logging
import json
import random
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import our modules
try:
    from finrobot.smart_money_concepts import SmartMoneyConcepts, OrderBlock
    from finrobot.harmonic_patterns import HarmonicPatternDetector, HarmonicSignal
    from finrobot.genetic_optimizer import GeneticOptimizer, StrategyGenome, optimize_strategy_parameters
    from finrobot.portfolio_manager import PortfolioManager, StrategyPerformance
except ImportError:
    from smart_money_concepts import SmartMoneyConcepts, OrderBlock
    from harmonic_patterns import HarmonicPatternDetector, HarmonicSignal
    from genetic_optimizer import GeneticOptimizer, StrategyGenome, optimize_strategy_parameters
    from portfolio_manager import PortfolioManager, StrategyPerformance


logger = logging.getLogger(__name__)


@dataclass
class Signal:
    """Unified signal structure for all strategies"""
    strategy: str  # 'grid', 'martingale', 'hft', 'smc', 'harmonic'
    type: str  # 'buy', 'sell', 'hold'
    confidence: float  # 0.0 to 1.0
    entry_price: float
    stop_loss: float
    take_profit: float
    take_profit_2: Optional[float] = None
    timeframe: str = '1h'
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'strategy': self.strategy,
            'type': self.type,
            'confidence': self.confidence,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'take_profit_2': self.take_profit_2,
            'timeframe': self.timeframe,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class Trade:
    """Represents a completed trade"""
    signal: Signal
    exit_price: float
    exit_time: datetime
    pnl: float
    pnl_pct: float
    exit_reason: str  # 'tp1', 'tp2', 'sl', 'trailing', 'time'
    
    def to_dict(self) -> Dict:
        return {
            'signal': self.signal.to_dict(),
            'exit_price': self.exit_price,
            'exit_time': self.exit_time.isoformat(),
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'exit_reason': self.exit_reason
        }


class StrategyBase:
    """Base class for all strategies"""
    
    def __init__(self, name: str, params: Dict = None):
        self.name = name
        self.params = params or {}
        self.is_active = True
        self.performance = StrategyPerformance(strategy_name=name)
        
    def generate_signal(self, df: pd.DataFrame) -> Optional[Signal]:
        """Generate trading signal - to be implemented by subclasses"""
        raise NotImplementedError
    
    def update_params(self, params: Dict):
        """Update strategy parameters"""
        self.params.update(params)
    
    def get_param_specs(self) -> Dict[str, Dict]:
        """Get parameter specifications for optimization"""
        raise NotImplementedError


class GridStrategy(StrategyBase):
    """Grid Trading Strategy"""
    
    def __init__(self, params: Dict = None):
        super().__init__('grid', params)
        self.default_params = {
            'grid_step_pips': 1.0,
            'take_profit_pips': 3.0,
            'max_grid_levels': 5,
            'base_lot': 0.01,
            'trend_ema_fast': 21,
            'trend_ema_slow': 55,
            'volatility_filter': 1.5
        }
        self.params = {**self.default_params, **(params or {})}
        self.grid_levels: List[Dict] = []
        
    def get_param_specs(self) -> Dict[str, Dict]:
        return {
            'grid_step_pips': {'min': 0.5, 'max': 5.0, 'step': 0.1, 'type': 'float'},
            'take_profit_pips': {'min': 1.0, 'max': 10.0, 'step': 0.5, 'type': 'float'},
            'max_grid_levels': {'min': 2, 'max': 10, 'step': 1, 'type': 'int'},
            'base_lot': {'min': 0.001, 'max': 0.1, 'step': 0.001, 'type': 'float'},
            'trend_ema_fast': {'min': 5, 'max': 50, 'step': 1, 'type': 'int'},
            'trend_ema_slow': {'min': 20, 'max': 200, 'step': 5, 'type': 'int'},
            'volatility_filter': {'min': 0.5, 'max': 3.0, 'step': 0.1, 'type': 'float'}
        }
    
    def generate_signal(self, df: pd.DataFrame) -> Optional[Signal]:
        if len(df) < self.params['trend_ema_slow'] + 10:
            return None
        
        # Calculate EMAs
        ema_fast = df['close'].ewm(span=self.params['trend_ema_fast'], adjust=False).mean()
        ema_slow = df['close'].ewm(span=self.params['trend_ema_slow'], adjust=False).mean()
        
        current_price = df['close'].iloc[-1]
        
        # Volatility filter
        atr = self._calculate_atr(df, 14)
        volatility = atr / current_price
        if volatility > self.params['volatility_filter'] / 100:
            return None
        
        # Determine trend
        trend_up = ema_fast.iloc[-1] > ema_slow.iloc[-1]
        trend_down = ema_fast.iloc[-1] < ema_slow.iloc[-1]
        
        # Calculate grid levels
        grid_step = self.params['grid_step_pips'] / 100  # Convert pips
        take_profit = self.params['take_profit_pips'] / 100
        
        # Generate signal if we're near a grid level
        if trend_up:
            # Bullish grid - buy on dips
            entry = current_price - grid_step
            if abs(current_price - entry) < grid_step * 0.3:
                return Signal(
                    strategy='grid',
                    type='buy',
                    confidence=0.6,
                    entry_price=entry,
                    stop_loss=entry - (take_profit * 0.5),
                    take_profit=entry + take_profit,
                    take_profit_2=entry + (take_profit * 1.5),
                    metadata={'trend': 'up', 'grid_step': grid_step}
                )
        
        elif trend_down:
            # Bearish grid - sell on rallies
            entry = current_price + grid_step
            if abs(current_price - entry) < grid_step * 0.3:
                return Signal(
                    strategy='grid',
                    type='sell',
                    confidence=0.6,
                    entry_price=entry,
                    stop_loss=entry + (take_profit * 0.5),
                    take_profit=entry - take_profit,
                    take_profit_2=entry - (take_profit * 1.5),
                    metadata={'trend': 'down', 'grid_step': grid_step}
                )
        
        return None
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        high = df['high'].iloc[-period:]
        low = df['low'].iloc[-period:]
        close = df['close'].shift(1).iloc[-period:]
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        return atr


class SMCStrategy(StrategyBase):
    """Smart Money Concepts Strategy using Order Blocks and Liquidity Sweeps"""
    
    def __init__(self, params: Dict = None):
        super().__init__('smc', params)
        self.default_params = {
            'ob_lookback': 5,
            'fvg_min_size': 0.001,
            'sweep_lookback': 10,
            'min_ob_strength': 0.7,
            'min_sweep_strength': 0.75,
            'risk_reward_min': 1.5,
            'max_trades_per_hour': 3
        }
        self.params = {**self.default_params, **(params or {})}
        self.smc = SmartMoneyConcepts(
            ob_lookback=self.params['ob_lookback'],
            fvg_min_size=self.params['fvg_min_size'],
            sweep_lookback=self.params['sweep_lookback']
        )
        self.recent_trades: deque = deque(maxlen=20)
    
    def get_param_specs(self) -> Dict[str, Dict]:
        return {
            'ob_lookback': {'min': 3, 'max': 10, 'step': 1, 'type': 'int'},
            'fvg_min_size': {'min': 0.0005, 'max': 0.005, 'step': 0.0001, 'type': 'float'},
            'sweep_lookback': {'min': 5, 'max': 20, 'step': 1, 'type': 'int'},
            'min_ob_strength': {'min': 0.5, 'max': 0.9, 'step': 0.05, 'type': 'float'},
            'min_sweep_strength': {'min': 0.6, 'max': 0.9, 'step': 0.05, 'type': 'float'},
            'risk_reward_min': {'min': 1.0, 'max': 3.0, 'step': 0.1, 'type': 'float'},
            'max_trades_per_hour': {'min': 1, 'max': 10, 'step': 1, 'type': 'int'}
        }
    
    def generate_signal(self, df: pd.DataFrame) -> Optional[Signal]:
        if len(df) < 20:
            return None
        
        # Check trade frequency
        now = datetime.now()
        recent_count = sum(1 for t in self.recent_trades 
                          if (now - t).total_seconds() < 3600)
        if recent_count >= self.params['max_trades_per_hour']:
            return None
        
        current_price = df['close'].iloc[-1]
        
        # Detect SMC components
        obs = self.smc.detect_order_blocks(df)
        sweeps = self.smc.detect_liquidity_sweeps(df)
        
        # Look for high-quality setups
        # Setup 1: Bullish OB after bullish sweep
        for sweep in sweeps:
            if (sweep.type == 'bullish' and 
                sweep.strength >= self.params['min_sweep_strength']):
                
                # Look for bullish OB near sweep level
                for ob in obs:
                    if (ob.type == 'bullish' and 
                        ob.strength >= self.params['min_ob_strength']):
                        
                        # Check if OB is near current price
                        if abs(ob.high - current_price) < current_price * 0.001:
                            # Calculate R:R
                            stop_loss = ob.low
                            take_profit = current_price + (current_price - stop_loss) * 2
                            risk = current_price - stop_loss
                            reward = take_profit - current_price
                            
                            if risk > 0 and reward / risk >= self.params['risk_reward_min']:
                                self.recent_trades.append(now)
                                return Signal(
                                    strategy='smc',
                                    type='buy',
                                    confidence=sweep.strength * ob.strength,
                                    entry_price=current_price,
                                    stop_loss=stop_loss,
                                    take_profit=take_profit,
                                    take_profit_2=take_profit + (take_profit - current_price),
                                    metadata={
                                        'setup': 'OB_after_sweep',
                                        'ob_strength': ob.strength,
                                        'sweep_strength': sweep.strength,
                                        'risk_reward': reward / risk
                                    }
                                )
        
        # Setup 2: Bearish OB after bearish sweep
        for sweep in sweeps:
            if (sweep.type == 'bearish' and 
                sweep.strength >= self.params['min_sweep_strength']):
                
                for ob in obs:
                    if (ob.type == 'bearish' and 
                        ob.strength >= self.params['min_ob_strength']):
                        
                        if abs(ob.low - current_price) < current_price * 0.001:
                            stop_loss = ob.high
                            take_profit = current_price - (stop_loss - current_price) * 2
                            risk = stop_loss - current_price
                            reward = current_price - take_profit
                            
                            if risk > 0 and reward / risk >= self.params['risk_reward_min']:
                                self.recent_trades.append(now)
                                return Signal(
                                    strategy='smc',
                                    type='sell',
                                    confidence=sweep.strength * ob.strength,
                                    entry_price=current_price,
                                    stop_loss=stop_loss,
                                    take_profit=take_profit,
                                    take_profit_2=take_profit - (current_price - take_profit),
                                    metadata={
                                        'setup': 'OB_after_sweep',
                                        'ob_strength': ob.strength,
                                        'sweep_strength': sweep.strength,
                                        'risk_reward': reward / risk
                                    }
                                )
        
        return None


class HarmonicStrategy(StrategyBase):
    """Harmonic Pattern Strategy"""
    
    def __init__(self, params: Dict = None):
        super().__init__('harmonic', params)
        self.default_params = {
            'tolerance': 0.05,
            'min_confidence': 0.7,
            'risk_reward_min': 1.5,
            'swing_window': 5,
            'max_patterns_per_day': 5
        }
        self.params = {**self.default_params, **(params or {})}
        self.detector = HarmonicPatternDetector(tolerance=self.params['tolerance'])
        self.detected_patterns: deque = deque(maxlen=50)
        
    def get_param_specs(self) -> Dict[str, Dict]:
        return {
            'tolerance': {'min': 0.02, 'max': 0.1, 'step': 0.01, 'type': 'float'},
            'min_confidence': {'min': 0.5, 'max': 0.95, 'step': 0.05, 'type': 'float'},
            'risk_reward_min': {'min': 1.0, 'max': 3.0, 'step': 0.1, 'type': 'float'},
            'swing_window': {'min': 3, 'max': 10, 'step': 1, 'type': 'int'},
            'max_patterns_per_day': {'min': 1, 'max': 10, 'step': 1, 'type': 'int'}
        }
    
    def generate_signal(self, df: pd.DataFrame) -> Optional[Signal]:
        if len(df) < 20:
            return None
        
        # Detect patterns
        patterns = self.detector.detect_patterns(df)
        
        if not patterns:
            return None
        
        # Get the highest confidence pattern
        best_pattern = patterns[0]
        
        # Check confidence threshold
        if best_pattern.confidence < self.params['min_confidence']:
            return None
        
        # Check if we've seen this pattern recently
        pattern_key = f"{best_pattern.pattern.value}_{best_pattern.d_point[0]}"
        for p in self.detected_patterns:
            if p == pattern_key:
                return None
        
        self.detected_patterns.append(pattern_key)
        
        # Calculate risk:reward
        risk = abs(best_pattern.completion_price - best_pattern.stop_loss)
        reward = abs(best_pattern.take_profit_1 - best_pattern.completion_price)
        
        if risk > 0 and reward / risk < self.params['risk_reward_min']:
            return None
        
        # Create signal
        signal_type = 'buy' if best_pattern.type == 'bullish' else 'sell'
        
        return Signal(
            strategy='harmonic',
            type=signal_type,
            confidence=best_pattern.confidence,
            entry_price=best_pattern.completion_price,
            stop_loss=best_pattern.stop_loss,
            take_profit=best_pattern.take_profit_1,
            take_profit_2=best_pattern.take_profit_2,
            metadata={
                'pattern': best_pattern.pattern.value,
                'fib_ratios': best_pattern.fib_ratios,
                'x_point': best_pattern.x_point,
                'a_point': best_pattern.a_point,
                'b_point': best_pattern.b_point,
                'c_point': best_pattern.c_point,
                'd_point': best_pattern.d_point
            }
        )


class MultiStrategyEngine:
    """
    Main engine that coordinates all strategies with continuous optimization
    """
    
    def __init__(self,
                 initial_capital: float = 10000.0,
                 optimization_interval: int = 100,  # Backtests between optimization
                 data_fetcher: Optional[Callable] = None):
        
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.optimization_interval = optimization_interval
        self.data_fetcher = data_fetcher
        
        # Initialize strategies
        self.strategies: Dict[str, StrategyBase] = {}
        self.optimizers: Dict[str, GeneticOptimizer] = {}
        self.backtest_count = 0
        self.optimization_count = 0
        
        # Performance tracking
        self.trades: List[Trade] = []
        self.signals: deque = deque(maxlen=1000)
        self.equity_curve: List[float] = [initial_capital]
        self.returns_history: deque = deque(maxlen=1000)
        
        # Active positions
        self.active_positions: Dict[str, Signal] = {}
        
        # Best parameters found
        self.best_params_history: List[Dict] = []
        
        # Initialize all strategies
        self._initialize_strategies()
    
    def _initialize_strategies(self):
        """Initialize all trading strategies"""
        # Grid Strategy
        grid = GridStrategy()
        self.strategies['grid'] = grid
        
        # SMC Strategy
        smc = SMCStrategy()
        self.strategies['smc'] = smc
        
        # Harmonic Strategy
        harmonic = HarmonicStrategy()
        self.strategies['harmonic'] = harmonic
        
        # Initialize optimizers for each strategy
        for name, strategy in self.strategies.items():
            self.optimizers[name] = GeneticOptimizer(
                population_size=30,
                elite_size=3,
                mutation_rate=0.15,
                crossover_rate=0.8
            )
            self.optimizers[name].initialize_population(
                name, 
                strategy.get_param_specs()
            )
        
        logger.info(f"Initialized {len(self.strategies)} strategies with optimizers")
    
    def fetch_data(self, symbol: str = 'XAUUSD', 
                   timeframe: str = '1h',
                   periods: int = 1000) -> pd.DataFrame:
        """Fetch market data"""
        if self.data_fetcher:
            return self.data_fetcher(symbol, timeframe, periods)
        
        # Default: create sample data (replace with actual data source)
        logger.warning("No data fetcher provided, using sample data")
        dates = pd.date_range(end=datetime.now(), periods=periods, freq='H')
        np.random.seed(42)
        
        # Generate realistic OHLCV data
        trend = np.cumsum(np.random.randn(periods) * 0.1)
        price = 4500 + trend * 5 + np.random.randn(periods) * 3
        
        df = pd.DataFrame({
            'open': price + np.random.randn(periods) * 0.5,
            'high': price + abs(np.random.randn(periods)) * 2,
            'low': price - abs(np.random.randn(periods)) * 2,
            'close': price,
            'volume': np.random.randint(1000, 10000, periods)
        }, index=dates)
        
        return df
    
    def run_backtest(self, params: Dict[str, Dict], 
                    df: pd.DataFrame = None) -> Dict:
        """
        Run backtest with given parameters for all strategies
        Returns performance metrics
        """
        if df is None:
            df = self.fetch_data()
        
        total_pnl = 0.0
        total_trades = 0
        wins = 0
        losses = 0
        
        # Run each strategy
        for name, strategy in self.strategies.items():
            if name in params:
                strategy.update_params(params[name])
            
            # Simple backtest simulation
            pnl = 0.0
            trades = 0
            
            for i in range(100, len(df), 10):  # Step through data
                window = df.iloc[i-50:i]
                signal = strategy.generate_signal(window)
                
                if signal:
                    # Simulate trade
                    if i + 5 < len(df):
                        future_price = df['close'].iloc[i+5]
                        price_diff = future_price - signal.entry_price
                        
                        if signal.type == 'sell':
                            price_diff = -price_diff
                        
                        pnl += price_diff * 1000  # Simplified P&L
                        trades += 1
                        
                        if price_diff > 0:
                            wins += 1
                        else:
                            losses += 1
            
            total_pnl += pnl
            total_trades += trades
        
        # Calculate metrics
        win_rate = wins / total_trades if total_trades > 0 else 0
        
        results = {
            'total_return': total_pnl / self.initial_capital,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'wins': wins,
            'losses': losses,
            'pnl': total_pnl,
            'sharpe_ratio': 0.0,  # Simplified
            'max_drawdown': 0.0   # Simplified
        }
        
        return results
    
    def optimize_strategy(self, strategy_name: str, 
                         generations: int = 20,
                         df: pd.DataFrame = None) -> Dict:
        """
        Run genetic optimization for a specific strategy
        """
        if df is None:
            df = self.fetch_data()
        
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            logger.error(f"Strategy {strategy_name} not found")
            return {}
        
        optimizer = self.optimizers.get(strategy_name)
        if not optimizer:
            logger.error(f"No optimizer found for {strategy_name}")
            return {}
        
        param_specs = strategy.get_param_specs()
        
        # Define fitness function
        def fitness_func(genome: StrategyGenome) -> float:
            params = {strategy_name: {k: v.value for k, v in genome.parameters.items()}}
            try:
                results = self.run_backtest(params, df)
                # Multi-objective fitness
                fitness = (
                    results.get('win_rate', 0) * 0.3 +
                    min(results.get('total_return', 0), 1.0) * 0.4 +
                    (1 - results.get('max_drawdown', 0)) * 0.3
                )
                return fitness
            except Exception as e:
                logger.error(f"Error in fitness: {e}")
                return -np.inf
        
        # Run optimization
        logger.info(f"Optimizing {strategy_name} for {generations} generations")
        
        for gen in range(generations):
            optimizer.evaluate_fitness(fitness_func)
            
            best = optimizer.best_genome
            if best:
                logger.info(f"Gen {gen}: Best fitness = {best.fitness:.4f}")
            
            if gen < generations - 1:
                optimizer.create_next_generation()
        
        # Get best parameters
        best_params = optimizer.get_best_params()
        
        # Update strategy with best params
        if best_params:
            strategy.update_params(best_params)
            self.best_params_history.append({
                'timestamp': datetime.now().isoformat(),
                'strategy': strategy_name,
                'params': best_params,
                'fitness': optimizer.best_genome.fitness if optimizer.best_genome else None
            })
        
        return {
            'strategy': strategy_name,
            'best_params': best_params,
            'best_fitness': optimizer.best_genome.fitness if optimizer.best_genome else None,
            'generations': generations
        }
    
    def optimize_all_strategies(self, 
                               generations: int = 20,
                               df: pd.DataFrame = None):
        """Optimize all strategies"""
        if df is None:
            df = self.fetch_data()
        
        results = []
        for name in self.strategies.keys():
            try:
                result = self.optimize_strategy(name, generations, df)
                results.append(result)
            except Exception as e:
                logger.error(f"Error optimizing {name}: {e}")
        
        return results
    
    def run_optimization_loop(self, 
                            iterations: int = 1000,
                            optimization_interval: int = 100,
                            data_update_interval: int = 10):
        """
        Main optimization loop that continuously improves strategies
        """
        logger.info(f"Starting optimization loop: {iterations} iterations")
        
        df = self.fetch_data()
        
        for i in range(iterations):
            try:
                # Run backtest with current best params
                current_params = {}
                for name, strategy in self.strategies.items():
                    current_params[name] = strategy.params
                
                results = self.run_backtest(current_params, df)
                
                # Update performance tracking
                self.backtest_count += 1
                
                # Periodic optimization
                if self.backtest_count % optimization_interval == 0:
                    logger.info(f"Running optimization at iteration {i}")
                    self.optimization_count += 1
                    
                    # Optimize each strategy
                    for name in self.strategies.keys():
                        opt_result = self.optimize_strategy(name, generations=10, df=df)
                        logger.info(f"Optimized {name}: {opt_result.get('best_fitness', 'N/A')}")
                
                # Periodic data refresh
                if i % data_update_interval == 0:
                    df = self.fetch_data()
                
                # Log progress
                if i % 10 == 0:
                    logger.info(f"Iteration {i}/{iterations}: "
                              f"Return={results.get('total_return', 0):.2%}, "
                              f"Win Rate={results.get('win_rate', 0):.1%}")
                
            except Exception as e:
                logger.error(f"Error in iteration {i}: {e}")
                traceback.print_exc()
        
        logger.info(f"Optimization loop complete. {self.optimization_count} optimizations performed.")
    
    def save_state(self, filepath: str):
        """Save engine state"""
        state = {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'backtest_count': self.backtest_count,
            'optimization_count': self.optimization_count,
            'strategies': {
                name: {
                    'params': strat.params,
                    'performance': strat.performance.to_dict()
                }
                for name, strat in self.strategies.items()
            },
            'best_params_history': self.best_params_history,
            'equity_curve': self.equity_curve,
            'trades': [t.to_dict() for t in self.trades]
        }
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    @classmethod
    def load_state(cls, filepath: str, data_fetcher: Callable = None) -> 'MultiStrategyEngine':
        """Load engine state"""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        engine = cls(
            initial_capital=state['initial_capital'],
            data_fetcher=data_fetcher
        )
        
        engine.current_capital = state.get('current_capital', engine.initial_capital)
        engine.backtest_count = state.get('backtest_count', 0)
        engine.optimization_count = state.get('optimization_count', 0)
        engine.best_params_history = state.get('best_params_history', [])
        engine.equity_curve = state.get('equity_curve', [engine.initial_capital])
        
        # Restore strategies
        for name, data in state.get('strategies', {}).items():
            if name == 'grid':
                strategy = GridStrategy(data['params'])
            elif name == 'smc':
                strategy = SMCStrategy(data['params'])
            elif name == 'harmonic':
                strategy = HarmonicStrategy(data['params'])
            else:
                continue
            
            engine.strategies[name] = strategy
        
        return engine
