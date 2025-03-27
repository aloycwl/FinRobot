from dsCryptopanic import ne
from datasource import ts
from models import md

md("you are an expert financial analyst",

f"""Analyze the following market price and news to predict the trend and price for the next 5-10 minutes:

**Time Series**
{ts()}

**Latest News**
{ne()}""")