"""
Multi-Strategy Portfolio Manager
Manages capital allocation across multiple strategies with dynamic rebalancing
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class StrategyPerformance:
    """Tracks performance metrics for a single strategy"""
    strategy_name: str
    returns: deque = field(default_factory=lambda: deque(maxlen=100))
    trades: int = 0
    wins: int = 0
    losses: int = 0
    current_allocation: float = 0.0
    current_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    volatility: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update(self, new_return: float, is_win: bool = None):
        """Update with new return"""
        self.returns.append(new_return)
        self.current_return = new_return
        self.last_updated = datetime.now()
        
        if is_win is not None:
            self.trades += 1
            if is_win:
                self.wins += 1
            else:
                self.losses += 1
        
        self._calculate_metrics()
    
    def _calculate_metrics(self):
        """Calculate all performance metrics"""
        if len(self.returns) < 2:
            return
        
        returns_array = np.array(self.returns)
        
        # Basic metrics
        self.win_rate = self.wins / self.trades if self.trades > 0 else 0
        self.volatility = np.std(returns_array)
        
        # Sharpe ratio (assuming risk-free rate = 0)
        mean_return = np.mean(returns_array)
        self.sharpe_ratio = mean_return / (self.volatility + 1e-10) * np.sqrt(252)
        
        # Max drawdown
        cumulative = np.cumsum(returns_array)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max
        self.max_drawdown = np.min(drawdown)
        
        # Profit factor
        gains = np.sum(returns_array[returns_array > 0])
        losses = abs(np.sum(returns_array[returns_array < 0]))
        self.profit_factor = gains / (losses + 1e-10)
    
    def to_dict(self) -> Dict:
        return {
            'strategy_name': self.strategy_name,
            'returns': list(self.returns),
            'trades': self.trades,
            'wins': self.wins,
            'losses': self.losses,
            'current_allocation': self.current_allocation,
            'sharpe_ratio': self.sharpe_ratio,
            'max_drawdown': self.max_drawdown,
            'volatility': self.volatility,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'last_updated': self.last_updated.isoformat()
        }


@dataclass
class PortfolioAllocation:
    """Represents capital allocation across strategies"""
    allocations: Dict[str, float] = field(default_factory=dict)  # Strategy -> allocation %
    last_rebalanced: datetime = field(default_factory=datetime.now)
    rebalance_threshold: float = 0.05  # Rebalance if drift exceeds 5%
    
    def normalize(self):
        """Ensure allocations sum to 1.0"""
        total = sum(self.allocations.values())
        if total > 0:
            for key in self.allocations:
                self.allocations[key] /= total
    
    def get_drift(self, target: Dict[str, float]) -> float:
        """Calculate maximum drift from target allocation"""
        all_keys = set(self.allocations.keys()) | set(target.keys())
        max_drift = 0.0
        for key in all_keys:
            current = self.allocations.get(key, 0)
            tgt = target.get(key, 0)
            drift = abs(current - tgt)
            max_drift = max(max_drift, drift)
        return max_drift


class PortfolioManager:
    """
    Manages a portfolio of trading strategies with dynamic capital allocation
    """
    
    def __init__(self,
                 total_capital: float = 10000.0,
                 allocation_method: str = 'inverse_volatility',
                 rebalance_frequency: str = 'daily',
                 risk_free_rate: float = 0.0,
                 max_drawdown_limit: float = 0.05):
        
        self.total_capital = total_capital
        self.allocation_method = allocation_method
        self.rebalance_frequency = rebalance_frequency
        self.risk_free_rate = risk_free_rate
        self.max_drawdown_limit = max_drawdown_limit
        
        self.strategies: Dict[str, StrategyPerformance] = {}
        self.current_allocation = PortfolioAllocation()
        self.target_allocation = PortfolioAllocation()
        
        self.equity_curve: List[float] = [total_capital]
        self.returns_history: deque = deque(maxlen=100)
        self.last_rebalance: Optional[datetime] = None
        
        self.is_running = False
        self.current_drawdown = 0.0
        
    def add_strategy(self, name: str, initial_allocation: float = 0.0):
        """Add a new strategy to the portfolio"""
        if name not in self.strategies:
            self.strategies[name] = StrategyPerformance(
                strategy_name=name,
                current_allocation=initial_allocation
            )
            self.current_allocation.allocations[name] = initial_allocation
            logger.info(f"Added strategy: {name}")
    
    def remove_strategy(self, name: str):
        """Remove a strategy from the portfolio"""
        if name in self.strategies:
            del self.strategies[name]
            if name in self.current_allocation.allocations:
                del self.current_allocation.allocations[name]
            logger.info(f"Removed strategy: {name}")
    
    def update_strategy_performance(self, 
                                   name: str, 
                                   new_return: float,
                                   is_win: Optional[bool] = None):
        """Update performance for a strategy"""
        if name in self.strategies:
            self.strategies[name].update(new_return, is_win)
    
    def calculate_target_allocations(self) -> Dict[str, float]:
        """
        Calculate target allocations based on selected method
        """
        if not self.strategies:
            return {}
        
        if self.allocation_method == 'equal_weight':
            n = len(self.strategies)
            return {name: 1.0/n for name in self.strategies.keys()}
        
        elif self.allocation_method == 'inverse_volatility':
            # Inverse volatility weighting (risk parity)
            inverse_vols = {}
            for name, perf in self.strategies.items():
                vol = perf.volatility if perf.volatility > 0 else 0.01
                inverse_vols[name] = 1.0 / vol
            
            total = sum(inverse_vols.values())
            if total > 0:
                return {name: val/total for name, val in inverse_vols.items()}
            return {name: 1.0/len(self.strategies) for name in self.strategies.keys()}
        
        elif self.allocation_method == 'sharpe_weighted':
            # Sharpe ratio weighted
            sharpe_scores = {}
            for name, perf in self.strategies.items():
                # Use max(0, sharpe) to avoid negative weights
                score = max(0, perf.sharpe_ratio)
                sharpe_scores[name] = score + 0.01  # Add small constant
            
            total = sum(sharpe_scores.values())
            if total > 0:
                return {name: val/total for name, val in sharpe_scores.items()}
            return {name: 1.0/len(self.strategies) for name in self.strategies.keys()}
        
        elif self.allocation_method == 'momentum':
            # Momentum-based (more to recent winners)
            momentum_scores = {}
            for name, perf in self.strategies.items():
                if len(perf.returns) >= 5:
                    recent_return = np.mean(list(perf.returns)[-5:])
                    momentum_scores[name] = max(0, recent_return) + 0.001
                else:
                    momentum_scores[name] = 0.001
            
            total = sum(momentum_scores.values())
            if total > 0:
                return {name: val/total for name, val in momentum_scores.items()}
            return {name: 1.0/len(self.strategies) for name in self.strategies.keys()}
        
        else:
            # Default to equal weight
            n = len(self.strategies)
            return {name: 1.0/n for name in self.strategies.keys()}
    
    def check_rebalance_needed(self) -> bool:
        """Check if rebalancing is needed"""
        if self.last_rebalance is None:
            return True
        
        # Check time-based rebalancing
        now = datetime.now()
        if self.rebalance_frequency == 'hourly':
            if (now - self.last_rebalance).total_seconds() >= 3600:
                return True
        elif self.rebalance_frequency == 'daily':
            if now.date() != self.last_rebalance.date():
                return True
        elif self.rebalance_frequency == 'weekly':
            if (now - self.last_rebalance).days >= 7:
                return True
        
        # Check drift-based rebalancing
        target = self.calculate_target_allocations()
        drift = self.current_allocation.get_drift(target)
        if drift > self.current_allocation.rebalance_threshold:
            return True
        
        return False
    
    def rebalance(self):
        """Execute rebalancing"""
        target = self.calculate_target_allocations()
        
        # Update allocations
        for name, alloc in target.items():
            self.target_allocation.allocations[name] = alloc
            if name in self.strategies:
                self.strategies[name].current_allocation = alloc
        
        self.current_allocation.allocations = target.copy()
        self.current_allocation.last_rebalanced = datetime.now()
        self.last_rebalance = datetime.now()
        
        logger.info(f"Rebalanced portfolio: {target}")
    
    def update_portfolio_value(self, returns: Dict[str, float]):
        """
        Update portfolio value based on strategy returns
        """
        # Calculate weighted return
        portfolio_return = 0.0
        for name, ret in returns.items():
            alloc = self.current_allocation.allocations.get(name, 0)
            portfolio_return += ret * alloc
            
            # Update individual strategy performance
            self.update_strategy_performance(name, ret)
        
        # Update portfolio
        self.returns_history.append(portfolio_return)
        new_value = self.equity_curve[-1] * (1 + portfolio_return)
        self.equity_curve.append(new_value)
        
        # Calculate drawdown
        peak = max(self.equity_curve)
        self.current_drawdown = (new_value - peak) / peak if peak > 0 else 0
        
        # Check for drawdown limit
        if abs(self.current_drawdown) > self.max_drawdown_limit:
            logger.warning(f"Max drawdown limit reached: {self.current_drawdown:.2%}")
            self.is_running = False
        
        # Check if rebalancing needed
        if self.check_rebalance_needed():
            self.rebalance()
    
    def get_portfolio_stats(self) -> Dict:
        """Get portfolio statistics"""
        if len(self.equity_curve) < 2:
            return {}
        
        returns = np.array(self.returns_history) if self.returns_history else np.array([0])
        
        stats = {
            'total_return': (self.equity_curve[-1] - self.equity_curve[0]) / self.equity_curve[0],
            'current_value': self.equity_curve[-1],
            'max_drawdown': self.current_drawdown,
            'volatility': np.std(returns) if len(returns) > 1 else 0,
            'sharpe_ratio': np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252) if len(returns) > 1 else 0,
            'num_strategies': len(self.strategies),
            'allocation': self.current_allocation.allocations.copy(),
            'strategy_performances': {name: perf.to_dict() for name, perf in self.strategies.items()}
        }
        
        return stats
    
    def save_state(self, filepath: str):
        """Save portfolio state"""
        state = {
            'total_capital': self.total_capital,
            'allocation_method': self.allocation_method,
            'rebalance_frequency': self.rebalance_frequency,
            'equity_curve': self.equity_curve,
            'returns_history': list(self.returns_history),
            'current_allocation': self.current_allocation.allocations,
            'strategies': {name: perf.to_dict() for name, perf in self.strategies.items()},
            'is_running': self.is_running,
            'current_drawdown': self.current_drawdown
        }
        import json
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    @classmethod
    def load_state(cls, filepath: str) -> 'PortfolioManager':
        """Load portfolio state"""
        import json
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        pm = cls(
            total_capital=state['total_capital'],
            allocation_method=state['allocation_method'],
            rebalance_frequency=state['rebalance_frequency']
        )
        
        pm.equity_curve = state['equity_curve']
        pm.returns_history = deque(state['returns_history'], maxlen=100)
        pm.current_allocation.allocations = state['current_allocation']
        pm.is_running = state['is_running']
        pm.current_drawdown = state['current_drawdown']
        
        # Restore strategies
        for name, data in state['strategies'].items():
            perf = StrategyPerformance(strategy_name=name)
            perf.returns = deque(data.get('returns', []), maxlen=100)
            perf.trades = data.get('trades', 0)
            perf.wins = data.get('wins', 0)
            perf.losses = data.get('losses', 0)
            perf.current_allocation = data.get('current_allocation', 0)
            pm.strategies[name] = perf
        
        return pm
