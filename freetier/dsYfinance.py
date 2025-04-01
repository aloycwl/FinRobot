import yfinance as yf
import pandas as pd

def pullYF(op) -> str:
    pd.set_option('display.max_rows', None)

    df = yf.download(op, interval="5m")#[['Close']] 
    df.index = pd.to_datetime(df.index)
    l2 = df[df.index > (df.index[-1] - pd.Timedelta(hours=12))]
    l2.index = l2.index.strftime('%y-%m-%d %H:%M')
    return(l2)


# print(pullYF('BTC-USD'))