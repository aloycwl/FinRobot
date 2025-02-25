# filename: plot_apple_stock.py

import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

# Download historical data for Apple Inc.'s stock
data = yf.download('AAPL', start='2023-01-01', end='2023-12-31')

# Calculate daily returns
daily_returns = data['Close'].pct_change()

# Plot the chart
plt.figure(figsize=(10,6))
plt.plot(daily_returns.index, daily_returns.values, label='Daily Return')
plt.title('Apple Inc. Stock Price Change in 2023')
plt.xlabel('Date')
plt.ylabel('Return (%)')
plt.legend()
plt.grid(True)
plt.show()

# Save the plot to a file
plt.savefig('apple_stock_chart.png')

# Print the first 5 rows of the historical data for verification
print(data.head())