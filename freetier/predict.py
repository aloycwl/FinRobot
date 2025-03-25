from cryptopanic import news as ne
from datasource import timeseries as ts
from models import models as mo

co = f"""Analyze the following market price and news to predict the trend and price for the next 5-10 minutes:

{ts()}

{ne()}"""

print(mo(co, [{"role":"system","content":"you are a top financial trader"},{"role":"user","content":co}]))