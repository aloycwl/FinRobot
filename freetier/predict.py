from cryptopanic import news as ne
from datasource import timeseries as ts
from models import models as mo

print(mo("you are an expert financial analyst",

f"""Analyze the following market price and news to predict the trend and price for the next 5-10 minutes:

**Time Series**
{ts()}

**Latest News**
{ne()}"""))