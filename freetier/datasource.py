import pandas as pd
import sys as sy

def ts() -> str:
  op = sy.argv[3]

  try: 
    if 1 <= int(op) <= 3:
      from dsAlphaVantage import pullAV as pa
  except:
    pass

  if op == "1":
    return pa(f'FX_DAILY&from_symbol={sy.argv[4]}&to_symbol={sy.argv[5]}')

  elif op == "2":
    return pa(f'DIGITAL_CURRENCY_DAILY&symbol={sy.argv[4]}&market={sy.argv[5]}')

  elif op == "3":
    return pa(f'TIME_SERIES_DAILY&symbol={sy.argv[4]}')

  else:
    from dsYfinance import pullYF as py
    return py(op)


# print(ts())