#!/usr/bin/env python3
"""
PLTR Stock Chart with Candlesticks and Moving Averages
Plots candlestick chart with 5-day, 20-day, and 60-day simple moving averages
"""

import yfinance as yf
import mplfinance as mpf
import pandas as pd
from datetime import datetime, timedelta

def fetch_stock_data(ticker='PLTR', period='6mo'):
    """
    Fetch stock data for the given ticker

    Args:
        ticker: Stock ticker symbol (default: PLTR)
        period: Time period to fetch (default: 6mo for 6 months)

    Returns:
        DataFrame with stock data
    """
    print(f"Fetching {ticker} stock data...")
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    return df

def calculate_moving_averages(df):
    """
    Calculate simple moving averages

    Args:
        df: DataFrame with stock data

    Returns:
        DataFrame with added MA columns
    """
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_60'] = df['Close'].rolling(window=60).mean()
    return df

def plot_stock_chart(df, ticker='PLTR'):
    """
    Plot candlestick chart with moving averages

    Args:
        df: DataFrame with stock data and moving averages
        ticker: Stock ticker symbol for title
    """
    # Define moving average plots
    apds = [
        mpf.make_addplot(df['SMA_5'], color='blue', width=1.5, label='5-day SMA'),
        mpf.make_addplot(df['SMA_20'], color='orange', width=1.5, label='20-day SMA'),
        mpf.make_addplot(df['SMA_60'], color='red', width=1.5, label='60-day SMA'),
    ]

    # Create the plot
    mpf.plot(
        df,
        type='candle',
        style='charles',
        title=f'{ticker} Stock Price with Moving Averages',
        ylabel='Price ($)',
        volume=True,
        addplot=apds,
        figsize=(14, 8),
        panel_ratios=(3, 1),
        warn_too_much_data=len(df) + 1
    )

def main():
    """Main function to create the stock chart"""
    # Fetch data
    df = fetch_stock_data('PLTR', period='6mo')

    # Calculate moving averages
    df = calculate_moving_averages(df)

    # Print some statistics
    print(f"\nData range: {df.index[0].date()} to {df.index[-1].date()}")
    print(f"Total trading days: {len(df)}")
    print(f"\nLatest prices:")
    print(f"  Close: ${df['Close'].iloc[-1]:.2f}")
    print(f"  5-day SMA: ${df['SMA_5'].iloc[-1]:.2f}")
    print(f"  20-day SMA: ${df['SMA_20'].iloc[-1]:.2f}")
    print(f"  60-day SMA: ${df['SMA_60'].iloc[-1]:.2f}")

    # Plot the chart
    print("\nGenerating chart...")
    plot_stock_chart(df, 'PLTR')
    print("Chart displayed successfully!")

if __name__ == '__main__':
    main()
