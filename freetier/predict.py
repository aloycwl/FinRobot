from dsCryptopanic import ne
from datasource import ts
from models import md

md("you are an expert financial analyst",

f"""Analyze the following market price and news to predict the trend and price for the next 30 minutes:

**Time Series**
{ts()}

**Latest News**
{ne()}""")


# print(ts())