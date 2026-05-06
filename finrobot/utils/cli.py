from __future__ import annotations

import json

from .config import settings
from .data_sources import fetch_fear_greed, fetch_market_depth, fetch_news, fetch_okx_candles
from .hft import HFTConfig, backtest
from .indicators import enrich_indicators
from .llm import llm_prediction
from .mt5_executor import MT5Credentials, connect as mt5_connect, place_market_order as mt5_place_order, shutdown as mt5_shutdown
from .ctrader_executor import CTraderCredentials, connect as ctrader_connect, place_market_order as ctrader_place_order, shutdown as ctrader_shutdown
from .grid import GridConfig, backtest_xauusd_grid


MENU = {
    "1": "Show latest market snapshot",
    "2": "Run LLM trading plan",
    "3": "Train LSTM and predict 10 steps",
    "4": "Train CNN and predict 10 steps",
    "5": "Backtest fast strategy",
    "6": "Backtest XAUUSD Grid Strategy",
    "7": "Place MT5 live market order",
    "8": "Place cTrader live market order (Linux native)",
    "0": "Exit",
}


def show_menu() -> None:
    print("\n=== FinRobot Menu ===")
    for key, value in MENU.items():
        print(f"{key}. {value}")


def option_snapshot() -> None:
    frame = fetch_okx_candles(limit=120)
    enriched = enrich_indicators(frame)
    print(enriched.tail(5)[["open", "high", "low", "close", "EMA_50", "RSI_14", "MACD"]])
    print("\nLatest news:")
    print(fetch_news()[:1500])
    print("\nMarket depth:")
    print(fetch_market_depth()[:1200])
    print("\nFear & greed:")
    print(fetch_fear_greed())


def option_llm() -> None:
    frame = fetch_okx_candles(limit=120)
    prompt = f"""Analyze this market data and provide only a concise 3-hour trading plan.

Time series:
{frame.tail(100)}

Latest news:
{fetch_news()}

Market depth:
{fetch_market_depth()}

Sentiment:
{fetch_fear_greed()}
"""
    system = (
        "You are a master FX strategist and market analyst. Give concise plan only, no disclaimers."
    )
    print(llm_prediction(prompt, system))


def option_lstm() -> None:
    from .ml import build_sequences, predict_future_steps, train_lstm

    frame = fetch_okx_candles(limit=600)
    x_data, y_data, scaler, features = build_sequences(frame)
    model = train_lstm(x_data, y_data)
    scaled = scaler.transform(features)
    preds = predict_future_steps(model, scaler, scaled, sequence_length=60, steps=10)
    print("LSTM 10-step predictions:", [round(float(v), 2) for v in preds])


def option_cnn() -> None:
    from .ml import build_sequences, predict_future_steps, train_cnn

    frame = fetch_okx_candles(limit=600)
    x_data, y_data, scaler, features = build_sequences(frame)
    model = train_cnn(x_data, y_data)
    scaled = scaler.transform(features)
    preds = predict_future_steps(model, scaler, scaled, sequence_length=60, steps=10)
    print("CNN 10-step predictions:", [round(float(v), 2) for v in preds])


def option_backtest() -> None:
    frame = fetch_okx_candles(limit=1000)
    results = backtest(frame, HFTConfig())
    print("HFT backtest stats:")
    print(json.dumps(results, indent=2))


def option_backtest_grid() -> None:
    frame = fetch_okx_candles(limit=2000)
    results = backtest_xauusd_grid(frame, GridConfig())
    print("\n=== XAUUSD Grid Strategy Backtest Results ===")
    print(json.dumps(results, indent=2))


def option_mt5_order() -> None:
    login = settings.mt5_login or int(input("MT5 login: "))
    password = settings.mt5_password or input("MT5 password: ")
    server = settings.mt5_server or input("MT5 server: ")
    symbol = input("Symbol (e.g., BTCUSD): ").strip()
    side = input("Side (buy/sell): ").strip().lower()
    lot = float(input("Lot size: "))

    mt5 = mt5_connect(MT5Credentials(login=login, password=password, server=server))
    try:
        result = mt5_place_order(mt5, symbol=symbol, side=side, lot=lot)
        print(f"Order sent successfully: {result}")
    finally:
        mt5_shutdown(mt5)


def option_ctrader_order() -> None:
    client_id = settings.ctrader_client_id or input("cTrader Client ID: ")
    client_secret = settings.ctrader_client_secret or input("cTrader Client Secret: ")
    access_token = settings.ctrader_access_token or input("cTrader Access Token: ")
    account_id = settings.ctrader_account_id or int(input("cTrader Account ID: "))
    symbol = input("Symbol (e.g., XAUUSD): ").strip()
    side = input("Side (buy/sell): ").strip().lower()
    lot = float(input("Lot size: "))

    ctrader = ctrader_connect(CTraderCredentials(
        client_id=client_id,
        client_secret=client_secret,
        access_token=access_token,
        account_id=account_id
    ))
    try:
        result = ctrader_place_order(ctrader, symbol=symbol, side=side, lot=lot)
        print(f"Order sent successfully: {result}")
    finally:
        ctrader_shutdown(ctrader)


def main() -> None:
    while True:
        show_menu()
        choice = input("Select action by number: ").strip()
        if choice == "1":
            option_snapshot()
        elif choice == "2":
            option_llm()
        elif choice == "3":
            option_lstm()
        elif choice == "4":
            option_cnn()
        elif choice == "5":
            option_backtest()
        elif choice == "6":
            option_backtest_grid()
        elif choice == "7":
            option_mt5_order()
        elif choice == "8":
            option_ctrader_order()
        elif choice == "0":
            print("Goodbye")
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
