import yfinance as yf
import pandas as pd

def pullYF(op) -> str:
    pd.set_option('display.max_rows', None)

    df = yf.download(op, interval="1m", period="1d")#[['Close']] 
    df.index = pd.to_datetime(df.index)
    l2 = df[df.index > (df.index[-1] - pd.Timedelta(hours=2))]
    l2.index = l2.index.strftime('%y-%m-%d %H:%M')
    return(l2)