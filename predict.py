from dsAlternative import se
from dsCryptopanic import ne
from dsTimeSeries import ts
from marketdepth import ma
from models import md
import config as cf

cm = "You are a master FX strategist and market analyst with deep knowledge of global macroeconomics, technical analysis, and risk management"
co = f"""Analyze the following OHLC market price data, 
formulate RSI, EMA, MACD, Bollinger Bands, Stochastic, ATR, Parabolic, Harmonics, Fibonacci, Gann,
and another other indicators that could be useful for prediction.
Together with the following news, market depth and market sentiment to give me real-time trading plan for the next 3 hours:

*Time Series*\n{ts()}

*Latest News*\n{ne()}

*Market Depth*\n{ma()}

*Market Sentiment*\n{se()}"""

print(co)

cf.ml = 'nvidia'
cf.mo = 'qwen/qwen3-235b-a22b'
print(md(cm, co))
