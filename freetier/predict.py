from datasource import prompt as pm
from models import models as mo

co = pm(
  "Analyze the following high-frequency price data (OHLC) and "
  "predict the trend and price for the next 5-10 minutes.\n"
)

print(mo(co, [{"role":"system","content":"you are a top financial trader"},{"role":"user","content":co}]))