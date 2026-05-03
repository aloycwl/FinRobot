# Multi-Strategy Portfolio Trading System - Master Plan

**Created**: 2026-05-03  
**Status**: Planning Phase - Awaiting Implementation Decisions  
**Objective**: Create a comprehensive multi-strategy ensemble trading system that combines Grid, Martingale, HFT, and additional strategies into a unified portfolio with dynamic capital allocation.

---

## 🎯 Executive Summary

### Problem with Current Approach
- Individual strategies optimized in isolation
- No diversification benefits
- Winner-take-all selection ignores strategy combinations
- Risk concentrated in single strategy

### Solution: Multi-Strategy Ensemble
- Run all strategies simultaneously with different capital allocations
- Dynamic rebalancing based on performance and correlation
- Portfolio-level risk management
- Smoother equity curves through diversification

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│            Portfolio Risk Manager                       │
│         (Capital allocation & correlation)             │
└──────────────────┬──────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┬──────────────┬──────────────┐
    │              │              │              │              │
    ▼              ▼              ▼              ▼              ▼
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Grid   │  │Martingale│  │   HFT    │  │  Trend   │  │  Mean    │
│Strategy │  │Strategy  │  │Strategy  │  │Strategy  │  │Reversion │
└────┬────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │            │             │             │             │
     └────────────┴─────────────┴─────────────┴─────────────┘
                   │
                   ▼
          ┌─────────────────┐
          │  Combined P&L   │
          │   & Equity      │
          └─────────────────┘
```

---

## 📊 Current Strategy Performance (Baseline)

### Martingale Strategy
- **Return**: -0.99%
- **Win Rate**: 19.9%
- **Trades**: 7,629
- **Status**: ⚠️ Losing but active

### Grid Strategy
- **Return**: 0%
- **Win Rate**: 0%
- **Trades**: 0
- **Status**: ❌ Not executing trades (parameters too conservative)

### HFT Strategy
- **Return**: 0%
- **Win Rate**: 0%
- **Trades**: 0
- **Status**: ❌ Not executing trades (tick threshold too high)

---

## 🔧 Implementation Decisions Required

### 1. Capital Allocation Method

**❓ Question**: How should capital be distributed among strategies?

- [ ] **Option A: Equal Weight (25% each)**
  - Simplest approach
  - No optimization required
  - May underperform if one strategy dominates

- [ ] **Option B: Inverse Volatility Weighting**
  - More capital to less volatile strategies
  - Risk-parity approach
  - Smoother portfolio returns

- [ ] **Option C: Momentum-Based Allocation**
  - More capital to recent winners
  - Trend-following at strategy level
  - Risk: Chasing performance

- [ ] **Option D: Kelly Criterion**
  - Mathematically optimal growth
  - Requires accurate edge estimation
  - May recommend high concentration

- [ ] **Option E: Minimum Variance Portfolio**
  - Markowitz optimization
  - Considers correlations
  - Risk: Overfitting to past

---

### 2. Rebalancing Frequency

**❓ Question**: How often should capital be reallocated?

- [ ] **Option A: After Every Trade**
  - Maximum responsiveness
  - High transaction costs
  - May cause overtrading

- [ ] **Option B: Daily**
  - Balanced approach
  - Captures daily performance shifts
  - Moderate rebalancing costs

- [ ] **Option C: Weekly**
  - Less noise
  - Lower transaction costs
  - Slower to adapt to regime changes

- [ ] **Option D: When Allocation Drifts >X%**
  - Threshold-based
  - Only rebalance when necessary
  - Requires setting threshold X

- [ ] **Option E: Performance-Based (when strategy underperforms)**
  - Event-driven
  - Reactive to performance
  - May lag optimal timing

---

### 3. Correlation Handling

**❓ Question**: How should correlations between strategies be managed?

- [ ] **Option A: Ignore Correlations (Naive Diversification)**
  - Simplest approach
  - Assumes independence
  - May concentrate risk unknowingly

- [ ] **Option B: Reduce Allocation When Correlation Spikes**
  - Dynamic risk management
  - Reduces exposure when diversification breaks
  - Requires correlation monitoring

- [ ] **Option C: Only Trade Uncorrelated Strategies Simultaneously**
  - Strict diversification
  - May limit opportunity set
  - Requires correlation threshold

- [ ] **Option D: Hierarchical Risk Parity**
  - Advanced portfolio construction
  - Accounts for correlation structure
  - Computationally intensive

- [ ] **Option E: Regime-Switching Based on Correlation**
  - Adaptive approach
  - Changes allocation based on correlation regime
  - Requires regime detection

---

### 4. Additional Strategies to Add

**❓ Question**: Which new strategies should be added to the ensemble?

- [ ] **Trend Following (Breakout-Based)**
  - Trades breakouts from consolidation
  - Good for trending markets
  - Complements mean reversion

- [ ] **Mean Reversion (RSI/Bollinger Bands)**
  - Trades overbought/oversold conditions
  - Good for ranging markets
  - Natural hedge to trend following

- [ ] **Volatility Expansion**
  - Trades volatility breakouts
  - Captures news events
  - Uncorrelated to directional strategies

- [ ] **Order Block / Smart Money Concepts**
  - Institutional trading levels
  - High probability setups
  - Requires more complex logic

- [ ] **Arbitrage (Statistical)**
  - Mean reversion between correlated assets
  - Market neutral
  - Low returns but consistent

- [ ] **Machine Learning-Based**
  - Pattern recognition
  - Adaptive to market conditions
  - Requires training data

---

### 5. Risk Controls

**❓ Question**: What risk controls should be implemented?

**Portfolio-Level Stop Losses:**
- [ ] **Max Portfolio Drawdown**: ___% (before stopping/sizing down)
- [ ] **Daily Loss Limit**: ___% (stop trading for day)
- [ ] **Weekly Loss Limit**: ___% (stop trading for week)
- [ ] **Correlation Spike Threshold**: Correlation >___ (reduce exposure)

**Strategy-Level Controls:**
- [ ] **Individual Strategy Drawdown Limit**: ___%
- [ ] **Minimum Win Rate**: ___% (disable underperforming strategies)
- [ ] **Maximum Consecutive Losses**: ___ (pause strategy)

**Position Sizing:**
- [ ] **Max Total Exposure**: ___% of capital
- [ ] **Max Single Strategy Exposure**: ___% of capital
- [ ] **Kelly Fraction**: ___% (if using Kelly sizing)

---

## 📋 Implementation Phases

### Phase 1: Multi-Strategy Runner (Week 1)
- [ ] Create unified backtest runner that executes all strategies on same data
- [ ] Track each strategy's performance separately
- [ ] Calculate correlations between strategy returns
- [ ] Generate combined portfolio equity curve

### Phase 2: Portfolio Allocator (Week 2)
- [ ] Implement selected capital allocation method
- [ ] Create rebalancing logic based on selected frequency
- [ ] Add correlation-based weight adjustments
- [ ] Implement strategy rotation based on performance

### Phase 3: Risk Manager (Week 3)
- [ ] Portfolio-level position sizing
- [ ] Maximum drawdown circuit breakers
- [ ] Correlation spike detection
- [ ] Daily/weekly loss limits

### Phase 4: Signal Aggregation (Week 4)
- [ ] Combine strategy signals with confidence weighting
- [ ] Ensemble voting mechanisms
- [ ] Meta-strategy that learns best combinations
- [ ] Machine learning for signal combination

### Phase 5: New Strategies (Week 5-6)
- [ ] Implement selected additional strategies
- [ ] Backtest and optimize new strategies
- [ ] Integrate into ensemble
- [ ] Recalibrate portfolio weights

---

## 📊 Success Metrics

### Target Performance
- **Portfolio Return**: >5% hourly (20% daily)
- **Portfolio Win Rate**: >65%
- **Max Portfolio Drawdown**: <3%
- **Sharpe Ratio**: >2.0
- **Strategy Correlation**: <0.5 (average)

### Monitoring KPIs
- Individual strategy performance vs. portfolio
- Correlation matrix heatmap
- Capital allocation efficiency
- Risk-adjusted returns by strategy
- Rebalancing frequency and costs

---

## ⚠️ Known Issues to Address

### Current Strategy Issues
1. **Grid Strategy**: Not executing trades (parameters too conservative)
2. **HFT Strategy**: Not executing trades (tick threshold too high)
3. **Martingale**: Losing money (19.9% win rate vs 55% target)

### Technical Debt
- Daemon stopped and needs restart
- Only 3.9% through 10,000 iteration target
- Grid and HFT strategies need parameter tuning

---

## 🚀 Next Steps

1. **Review this document** and make decisions on all options
2. **Restart the daemon** with new multi-strategy architecture
3. **Implement Phase 1**: Multi-strategy runner
4. **Tune individual strategies** to ensure all are trading
5. **Build portfolio allocator** (Phase 2)

---

## 📞 Contact & Notes

**Document Owner**: User  
**Last Updated**: 2026-05-03  
**Status**: Awaiting Implementation Decisions  

**Notes**:
- All checkboxes are currently unchecked - awaiting your decisions
- This is a living document - update as implementation progresses
- Keep track of which options were chosen and why

---

**END OF DOCUMENT**
