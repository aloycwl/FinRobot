from dsCryptopanic import ne
from datasource import ts
from marketdepth import ma
from models import md

md("you are an expert financial analyst",

f"""Analyze the following OHLC market price data, formulate RSI, EMA, MACD, Bollinger Bands, Stochastic ATR, Parabolic,
and another other indicators that could be useful for prediction.
With the following news and market depth to predict the trend and price for the next 30 minutes:

**Time Series**
{ts()}

**Latest News**
{ne()}

**Market Depth**
{ma()}""")