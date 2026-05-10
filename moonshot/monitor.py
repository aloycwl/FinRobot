"""
Hyperliquid Moonshot Engine - Live Monitor & Dashboard
Real-time performance tracking and trade monitoring
"""

import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import deque
import threading

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    timestamp: float
    symbol: str
    side: str
    entry_price: float
    exit_price: Optional[float]
    size: float
    leverage: float
    pnl: float
    pnl_pct: float
    exit_reason: str  # 'tp', 'sl', 'manual', 'signal'
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat(),
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'size': self.size,
            'leverage': self.leverage,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'exit_reason': self.exit_reason
        }


@dataclass
class PositionSnapshot:
    timestamp: float
    symbol: str
    side: str
    size: float
    entry_price: float
    current_price: float
    leverage: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    liquidation_price: float
    distance_to_liq_pct: float
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat(),
            'symbol': self.symbol,
            'side': self.side,
            'size': self.size,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'leverage': self.leverage,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
            'liquidation_price': self.liquidation_price,
            'distance_to_liq_pct': self.distance_to_liq_pct
        }


@dataclass
class PerformanceMetrics:
    timestamp: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float
    total_pnl: float
    total_pnl_pct: float
    max_drawdown_pct: float
    current_drawdown_pct: float
    sharpe_ratio: float  # Simplified
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat(),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'expectancy': self.expectancy,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': self.total_pnl_pct,
            'max_drawdown_pct': self.max_drawdown_pct,
            'current_drawdown_pct': self.current_drawdown_pct,
            'sharpe_ratio': self.sharpe_ratio
        }


class MoonshotMonitor:
    """
    Real-time monitoring dashboard for Hyperliquid Moonshot
    Tracks trades, positions, and performance metrics
    """
    
    def __init__(
        self,
        trader_engine=None,
        max_trade_history: int = 1000,
        update_interval: float = 5.0,
        save_interval: float = 60.0
    ):
        self.trader_engine = trader_engine
        self.max_trade_history = max_trade_history
        self.update_interval = update_interval
        self.save_interval = save_interval
        
        # Data storage
        self.trade_history: deque = deque(maxlen=max_trade_history)
        self.position_history: List[PositionSnapshot] = []
        self.performance_history: List[PerformanceMetrics] = []
        self.equity_curve: List[Dict] = []
        
        # Current state
        self.current_metrics: Optional[PerformanceMetrics] = None
        self.open_positions: Dict[str, PositionSnapshot] = {}
        
        # File paths
        self.data_dir = "moonshot_data"
        self.trade_log_file = f"{self.data_dir}/trade_history.jsonl"
        self.metrics_file = f"{self.data_dir}/metrics_history.json"
        self.equity_file = f"{self.data_dir}/equity_curve.json"
        
        # Control
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_save_time = 0
        
        # Create data directory
        import os
        os.makedirs(self.data_dir, exist_ok=True)
        
        logger.info(f"📊 Moonshot Monitor initialized")
        logger.info(f"   Data directory: {self.data_dir}")
    
    def _calculate_metrics(self) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics"""
        
        # Get trade data
        closed_trades = [t for t in self.trade_history if t.exit_price is not None]
        
        total_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t.pnl > 0]
        losing_trades = [t for t in closed_trades if t.pnl <= 0]
        
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate averages
        avg_win = sum(t.pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t.pnl for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        # Profit factor
        total_gains = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))
        profit_factor = total_gains / total_losses if total_losses > 0 else float('inf')
        
        # Expectancy
        expectancy = ((win_rate / 100) * avg_win) - (((100 - win_rate) / 100) * abs(avg_loss))
        
        # PnL
        total_pnl = sum(t.pnl for t in closed_trades)
        
        # Get current balance from engine
        if self.trader_engine:
            current_balance = self.trader_engine.engine.get_balance()
            starting_balance = self.trader_engine.initial_balance
            total_pnl_pct = ((current_balance - starting_balance) / starting_balance * 100)
        else:
            total_pnl_pct = 0
        
        # Drawdown calculation from equity curve
        max_drawdown_pct = 0
        current_drawdown_pct = 0
        
        if self.equity_curve:
            peak = self.equity_curve[0]['equity']
            max_dd = 0
            
            for point in self.equity_curve:
                equity = point['equity']
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak
                if dd > max_dd:
                    max_dd = dd
            
            max_drawdown_pct = max_dd * 100
            
            # Current drawdown
            if self.equity_curve:
                current_equity = self.equity_curve[-1]['equity']
                current_dd = (peak - current_equity) / peak if peak > 0 else 0
                current_drawdown_pct = current_dd * 100
        
        # Simplified Sharpe (assuming risk-free rate of 0)
        sharpe_ratio = 0
        if len(self.equity_curve) > 10:
            returns = []
            for i in range(1, len(self.equity_curve)):
                prev = self.equity_curve[i-1]['equity']
                curr = self.equity_curve[i]['equity']
                if prev > 0:
                    returns.append((curr - prev) / prev)
            
            if returns:
                avg_return = sum(returns) / len(returns)
                variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                std_dev = variance ** 0.5
                
                if std_dev > 0:
                    sharpe_ratio = (avg_return / std_dev) * (252 ** 0.5)  # Annualized
        
        return PerformanceMetrics(
            timestamp=time.time(),
            total_trades=total_trades,
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            expectancy=expectancy,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            max_drawdown_pct=max_drawdown_pct,
            current_drawdown_pct=current_drawdown_pct,
            sharpe_ratio=sharpe_ratio
        )


# Helper function to create and run monitor
def create_monitor(trader_engine=None) -> MoonshotMonitor:
    """Create and return a new MoonshotMonitor instance"""
    return MoonshotMonitor(
        trader_engine=trader_engine,
        max_trade_history=1000,
        update_interval=5.0,
        save_interval=60.0
    )


if __name__ == "__main__":
    # Test the monitor
    monitor = create_monitor()
    
    # Add some mock trades
    from hyperliquid_strategies import TradeRecord
    
    trade1 = TradeRecord(
        timestamp=time.time(),
        symbol="BTC-PERP",
        side="BUY",
        entry_price=45000.0,
        exit_price=45500.0,
        size=0.01,
        leverage=10.0,
        pnl=5.0,
        pnl_pct=1.11,
        exit_reason="tp"
    )
    
    monitor.trade_history.append(trade1)
    
    # Calculate metrics
    metrics = monitor._calculate_metrics()
    
    print("\n📊 Test Metrics:")
    print(f"Total Trades: {metrics.total_trades}")
    print(f"Win Rate: {metrics.win_rate:.1f}%")
    print(f"Total PnL: {metrics.total_pnl:.2f} USDT")
    print(f"Profit Factor: {metrics.profit_factor:.2f}")