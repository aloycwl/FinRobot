import config as cf


def ts() -> str:

  try:
    if 1 <= int(cf.op) <= 3:
      from dsAlphaVantage import pullAV as s
  except:
    pass

  if cf.op == "1":
    return s(f'FX_DAILY&from_symbol={cf.p1}&to_symbol={cf.p2}')

  elif cf.op == "2":
    return s(f'DIGITAL_CURRENCY_DAILY&symbol={cf.p1}&market={cf.p2}')

  elif cf.op == "3":
    return s(f'TIME_SERIES_DAILY&symbol={cf.p1}')

  elif cf.op == "B":
    from dsOKX import pullOkx as s
    return s()
  else:
    from dsYfinance import pullYF as s
    return s(cf.op)
