from dsCryptopanic import ne
from datasource import ts
from marketdepth import ma
from models import md
from sentiment import se

cm = "You are a master FX strategist and market analyst with deep knowledge of global macroeconomics, technical analysis, and risk management"
co = f"""Analyze the following OHLC market price data, 
formulate RSI, EMA, MACD, Bollinger Bands, Stochastic, ATR, Parabolic, Harmonics, Fibonacci, Gann,
and another other indicators that could be useful for prediction.
With the following news, market depth and market sentiment to predict the trend and price for the next 30 minutes:

**Time Series**
{ts()}

**Latest News**
{ne()}

**Market Depth**
{ma()}

**Market Sentiment**
{se()}"""

print(md(cm, co))