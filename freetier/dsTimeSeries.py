import config as cf

def ts() -> str:

  try: 
    if 1 <= int(cf.op) <= 3:
      from dsAlphaVantage import pullAV as pa
  except:
    pass

  if cf.op == "1":
    return pa(f'FX_DAILY&from_symbol={cf.p1}&to_symbol={cf.p2}')

  elif cf.op == "2":
    return pa(f'DIGITAL_CURRENCY_DAILY&symbol={cf.p1}&market={cf.p2}')

  elif cf.op == "3":
    return pa(f'TIME_SERIES_DAILY&symbol={cf.p1}')

  else:
    from dsYfinance import pullYF as py
    return py(cf.op)