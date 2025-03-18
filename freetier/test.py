import datetime
import json
import os
import pandas
import re
import requests
import yfinance as yf

pandas.set_option('display.max_rows', None)

 
dateE = datetime.datetime.now()
dateS = dateE - datetime.timedelta(days=1)
data = yf.download(['BTC-USD'], start=dateS, end=dateE, interval='5m')
print(data)
