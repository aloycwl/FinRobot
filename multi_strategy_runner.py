#!/usr/bin/env python3
"""
Main Runner for Multi-Strategy Trading System with Continuous Optimization
This script runs the continuous optimization loop that keeps trying different 
strategies, indicators, and parameters to maximize win rate and returns.
"""

import os
import sys
import time
import json
import logging
import argparse
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import signal
import threading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler('multi_strategy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import our modules
try:
    from finrobot.multi_strategy_engine import MultiStrategyEngine, Signal, Trade
    from finrobot.portfolio_manager import PortfolioManager
    from finrobot.genetic_optimizer import GeneticOptimizer
except ImportError as e:
    logger.error(f"Failed to import modules: {e}")
    sys.exit(1)


class ContinuousOptimizer:
    """
    Main orchestrator that continuously optimizes all strategies
    """
    
    def __init__(self, 
                 initial_capital: float = 10000.0,
                 base_data_path: str = 'data',
                 state_file: str = 'optimizer_state.json',
                 iterations: int = 10000):
        
        self.initial_capital = initial_capital
        self.base_data_path = Path(base_data_path)
        self.state_file = state_file
        self.max_iterations = iterations
        
        # Core components
        self.engine: Optional[MultiStrategyEngine] = None
        self.data_cache: Dict[str, pd.DataFrame] = {}
        
        # State tracking
        self.iteration = 0
        self.start_time = datetime.now()
        self.is_running = False
        self.best_win_rate = 0.0
        self.best_return = 0.0
        
        # Performance history
        self.performance_history: List[Dict] = []
        self.parameter_history: List[Dict] = []
        
        # Statistics
        self.total_backtests = 0
        self.total_optimizations = 0
        self.consecutive_fails = 0
        
        # Initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize the optimizer"""
        logger.info("="*60)
        logger.info("Initializing Continuous Optimizer")
        logger.info("="*60)
        
        # Try to load previous state
        self._load_state()
        
        # Initialize engine if not loaded
        if self.engine is None:
            logger.info("Creating new MultiStrategyEngine")
            self.engine = MultiStrategyEngine(
                initial_capital=self.initial_capital
            )
        
        logger.info(f"Initial capital: ${self.initial_capital:,.2f}")
        logger.info(f"Max iterations: {self.max_iterations:,}")
        logger.info("="*60)
    
    def _load_state(self):
        """Load previous optimizer state"""
        if not os.path.exists(self.state_file):
            return
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            self.iteration = state.get('iteration', 0)
            self.best_win_rate = state.get('best_win_rate', 0.0)
            self.best_return = state.get('best_return', 0.0)
            self.total_backtests = state.get('total_backtests', 0)
            self.total_optimizations = state.get('total_optimizations', 0)
            
            # Load performance history
            self.performance_history = state.get('performance_history', [])
            self.parameter_history = state.get('parameter_history', [])
            
            # Try to load engine state
            engine_state_file = state.get('engine_state_file', 'engine_state.json')
            if os.path.exists(engine_state_file):
                self.engine = MultiStrategyEngine.load_state(engine_state_file)
            
            logger.info(f"Loaded state from {self.state_file}")
            logger.info(f"Resuming from iteration {self.iteration}")
            
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            logger.info("Starting fresh")
    
    def _save_state(self):
        """Save current optimizer state"""
        try:
            # Save engine state separately
            engine_state_file = 'engine_state.json'
            if self.engine:
                self.engine.save_state(engine_state_file)
            
            state = {
                'iteration': self.iteration,
                'best_win_rate': self.best_win_rate,
                'best_return': self.best_return,
                'total_backtests': self.total_backtests,
                'total_optimizations': self.total_optimizations,
                'start_time': self.start_time.isoformat(),
                'last_saved': datetime.now().isoformat(),
                'performance_history': self.performance_history[-100:],  # Keep last 100
                'parameter_history': self.parameter_history[-100:],
                'engine_state_file': engine_state_file
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def fetch_data(self, symbol: str = 'XAUUSD',
                   timeframe: str = '1h',
                   periods: int = 1000) -> pd.DataFrame:
        """Fetch market data with caching"""
        cache_key = f"{symbol}_{timeframe}_{periods}"
        
        if cache_key in self.data_cache:
            return self.data_cache[cache_key]
        
        # Fetch data (replace with actual data source)
        if self.engine and hasattr(self.engine, 'fetch_data'):
            df = self.engine.fetch_data(symbol, timeframe, periods)
        else:
            # Generate sample data
            dates = pd.date_range(end=datetime.now(), periods=periods, freq='H')
            np.random.seed(42)
            trend = np.cumsum(np.random.randn(periods) * 0.1)
            price = 4500 + trend * 5
            
            df = pd.DataFrame({
                'open': price + np.random.randn(periods) * 0.5,
                'high': price + abs(np.random.randn(periods)) * 2,
                'low': price - abs(np.random.randn(periods)) * 2,
                'close': price,
                'volume': np.random.randint(1000, 10000, periods)
            }, index=dates)
        
        self.data_cache[cache_key] = df
        return df
    
    def run_single_iteration(self):
        """Run a single optimization iteration"""
        try:
            logger.debug(f"Running iteration {self.iteration + 1}")
            
            # Fetch fresh data
            df = self.fetch_data(periods=500)
            
            # Run backtest with current parameters
            current_params = {}
            for name, strategy in self.engine.strategies.items():
                current_params[name] = strategy.params
            
            backtest_results = self.engine.run_backtest(current_params, df)
            self.total_backtests += 1
            
            # Track performance
            win_rate = backtest_results.get('win_rate', 0)
            total_return = backtest_results.get('total_return', 0)
            
            # Update best if improved
            if win_rate > self.best_win_rate:
                self.best_win_rate = win_rate
                logger.info(f"New best win rate: {win_rate:.2%}")
            
            if total_return > self.best_return:
                self.best_return = total_return
                logger.info(f"New best return: {total_return:.2%}")
            
            # Record history
            self.performance_history.append({
                'iteration': self.iteration,
                'win_rate': win_rate,
                'total_return': total_return,
                'trades': backtest_results.get('total_trades', 0),
                'timestamp': datetime.now().isoformat()
            })
            
            # Periodic optimization
            if self.total_backtests % 100 == 0:
                logger.info("Running strategy optimization...")
                self.total_optimizations += 1
                
                # Optimize each strategy
                for name in self.engine.strategies.keys():
                    try:
                        result = self.engine.optimize_strategy(
                            name, 
                            generations=10, 
                            df=df
                        )
                        logger.info(f"Optimized {name}: {result.get('best_fitness', 'N/A'):.4f}")
                    except Exception as e:
                        logger.error(f"Error optimizing {name}: {e}")
            
            # Periodic state save
            if self.iteration % 50 == 0:
                self._save_state()
            
            self.iteration += 1
            self.consecutive_fails = 0
            
        except Exception as e:
            logger.error(f"Error in iteration {self.iteration}: {e}")
            traceback.print_exc()
            self.consecutive_fails += 1
            
            if self.consecutive_fails > 10:
                logger.error("Too many consecutive failures, stopping")
                self.stop()
    
    def start(self):
        """Start the continuous optimization loop"""
        logger.info("="*60)
        logger.info("Starting Continuous Optimization Loop")
        logger.info("="*60)
        logger.info(f"Target iterations: {self.max_iterations:,}")
        logger.info(f"Current best win rate: {self.best_win_rate:.2%}")
        logger.info(f"Current best return: {self.best_return:.2%}")
        logger.info("="*60)
        
        self.is_running = True
        self.start_time = datetime.now()
        
        try:
            while self.is_running and self.iteration < self.max_iterations:
                self.run_single_iteration()
                
                # Small delay to prevent CPU overload
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, stopping...")
            self.stop()
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            traceback.print_exc()
            self.stop()
    
    def stop(self):
        """Stop the optimization loop and save state"""
        logger.info("="*60)
        logger.info("Stopping Optimization Loop")
        logger.info("="*60)
        
        self.is_running = False
        
        # Save final state
        self._save_state()
        
        # Print final statistics
        runtime = datetime.now() - self.start_time
        
        logger.info("="*60)
        logger.info("FINAL STATISTICS")
        logger.info("="*60)
        logger.info(f"Runtime: {runtime}")
        logger.info(f"Iterations: {self.iteration:,}")
        logger.info(f"Total Backtests: {self.total_backtests:,}")
        logger.info(f"Total Optimizations: {self.total_optimizations}")
        logger.info(f"Best Win Rate: {self.best_win_rate:.2%}")
        logger.info(f"Best Return: {self.best_return:.2%}")
        logger.info("="*60)
    
    def get_summary(self) -> Dict:
        """Get summary of optimization status"""
        runtime = datetime.now() - self.start_time if hasattr(self, 'start_time') else timedelta(0)
        
        return {
            'is_running': self.is_running,
            'iteration': self.iteration,
            'max_iterations': self.max_iterations,
            'progress_pct': (self.iteration / self.max_iterations * 100) if self.max_iterations > 0 else 0,
            'runtime_seconds': runtime.total_seconds(),
            'total_backtests': self.total_backtests,
            'total_optimizations': self.total_optimizations,
            'best_win_rate': self.best_win_rate,
            'best_return': self.best_return,
            'strategies': list(self.strategies.keys()) if self.engine else [],
            'consecutive_fails': self.consecutive_fails
        }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Multi-Strategy Trading Optimizer')
    parser.add_argument('--iterations', type=int, default=10000,
                       help='Number of optimization iterations')
    parser.add_argument('--capital', type=float, default=10000.0,
                       help='Initial capital')
    parser.add_argument('--state-file', type=str, default='optimizer_state.json',
                       help='State file path')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from saved state')
    parser.add_argument('--status', action='store_true',
                       help='Show current status and exit')
    
    args = parser.parse_args()
    
    if args.status:
        # Show status
        if os.path.exists(args.state_file):
            with open(args.state_file, 'r') as f:
                state = json.load(f)
            print("="*60)
            print("OPTIMIZER STATUS")
            print("="*60)
            print(f"Iteration: {state.get('iteration', 0):,}")
            print(f"Total Backtests: {state.get('total_backtests', 0):,}")
            print(f"Total Optimizations: {state.get('total_optimizations', 0)}")
            print(f"Best Win Rate: {state.get('best_win_rate', 0):.2%}")
            print(f"Best Return: {state.get('best_return', 0):.2%}")
            print(f"Last Saved: {state.get('last_saved', 'N/A')}")
            print("="*60)
        else:
            print(f"No state file found at {args.state_file}")
        return
    
    # Create and run optimizer
    optimizer = ContinuousOptimizer(
        initial_capital=args.capital,
        state_file=args.state_file,
        iterations=args.iterations
    )
    
    logger.info("="*60)
    logger.info("Multi-Strategy Continuous Optimizer")
    logger.info("="*60)
    logger.info(f"Configuration:")
    logger.info(f"  Initial Capital: ${args.capital:,.2f}")
    logger.info(f"  Max Iterations: {args.iterations:,}")
    logger.info(f"  State File: {args.state_file}")
    logger.info(f"  Resume: {args.resume}")
    logger.info("="*60)
    
    # Start optimization
    try:
        optimizer.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
    finally:
        optimizer.stop()
    
    logger.info("="*60)
    logger.info("OPTIMIZATION COMPLETE")
    logger.info("="*60)


if __name__ == "__main__":
    main()
