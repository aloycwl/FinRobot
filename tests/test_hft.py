import pandas as pd

from finrobot.hft import TrendMartingaleConfig, next_martingale_lot, trend_signal_1m_with_5m_filter


def test_trend_signal_long_and_short():
    m5 = pd.DataFrame({"close": [90 + i for i in range(30)]})

    m1_long = pd.DataFrame({"close": [130, 131, 132]})
    assert trend_signal_1m_with_5m_filter(m1_long, m5) == 1

    m1_short = pd.DataFrame({"close": [80, 79, 78]})
    assert trend_signal_1m_with_5m_filter(m1_short, m5) == -1


def test_next_martingale_lot_caps_at_max_steps():
    cfg = TrendMartingaleConfig(base_lot=0.01, multiplier=2.0, max_steps=3)
    step, lot = next_martingale_lot(10, cfg)
    assert step == 3
    assert lot == 0.08
