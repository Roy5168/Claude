# PLTR Stock Chart with Moving Averages

This Python script plots a candlestick chart for Palantir Technologies (PLTR) stock with 5-day, 20-day, and 60-day simple moving averages.

## Features

- **Candlestick Chart**: Visual representation of PLTR stock price movements
- **Simple Moving Averages (SMA)**:
  - 5-day SMA (blue line)
  - 20-day SMA (orange line)
  - 60-day SMA (red line)
- **Volume Chart**: Trading volume displayed below the main chart
- **Stock Statistics**: Displays latest prices and moving average values

## Installation

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the script:

```bash
python pltr_stock_chart.py
```

The script will:
1. Fetch the last 6 months of PLTR stock data from Yahoo Finance
2. Calculate the moving averages
3. Display statistics in the terminal
4. Show an interactive chart

## Requirements

- Python 3.7+
- yfinance
- mplfinance
- pandas
- matplotlib

## Customization

You can modify the script to:
- Change the time period by editing the `period` parameter in `fetch_stock_data()`
- Add more moving averages by modifying the `calculate_moving_averages()` function
- Adjust chart styling in the `plot_stock_chart()` function
