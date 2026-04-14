"""市場快照：一次抓齊所有持股的技術 + 基本面 + 大盤背景資料。

使用 yfinance 抓取。輸出為可 JSON 序列化的 dict (MarketSnapshot)，確保
同一 portfolio 重跑時位元組完全一致以命中 prompt cache。
"""

from __future__ import annotations

import datetime
import json
import math
from typing import Any

import pandas as pd
import yfinance as yf

from advisor.models import Portfolio

# 美股大盤背景符號
_BENCHMARK_SYMBOLS = ["^GSPC", "^IXIC", "^DJI", "^VIX", "^TNX"]

# 欄位白名單：yfinance Ticker.info 內容很多，只挑基本面最相關的
_INFO_FIELDS = [
    "shortName",
    "longName",
    "sector",
    "industry",
    "currency",
    "marketCap",
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "priceToSalesTrailing12Months",
    "enterpriseValue",
    "enterpriseToEbitda",
    "profitMargins",
    "grossMargins",
    "operatingMargins",
    "returnOnEquity",
    "returnOnAssets",
    "revenueGrowth",
    "earningsGrowth",
    "debtToEquity",
    "currentRatio",
    "quickRatio",
    "freeCashflow",
    "operatingCashflow",
    "totalCash",
    "totalDebt",
    "beta",
    "dividendYield",
    "payoutRatio",
    "fiftyTwoWeekHigh",
    "fiftyTwoWeekLow",
    "fiftyDayAverage",
    "twoHundredDayAverage",
]


def _safe_float(val: Any) -> float | None:
    """將 yfinance 可能傳回的 NaN/None/numpy 數值標準化。"""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return round(f, 6)
    except (TypeError, ValueError):
        return None


def _calculate_sma(close: pd.Series, window: int) -> float | None:
    """計算最近一期 SMA（重用 pltr_stock_chart.py 的概念）。"""
    if len(close) < window:
        return None
    return _safe_float(close.rolling(window=window).mean().iloc[-1])


def _calculate_rsi(close: pd.Series, period: int = 14) -> float | None:
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return _safe_float(rsi.iloc[-1])


def _calculate_macd(close: pd.Series) -> dict[str, float | None]:
    if len(close) < 35:
        return {"macd": None, "signal": None, "histogram": None}
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    return {
        "macd": _safe_float(macd_line.iloc[-1]),
        "signal": _safe_float(signal_line.iloc[-1]),
        "histogram": _safe_float((macd_line - signal_line).iloc[-1]),
    }


def _fetch_price_series(ticker: yf.Ticker) -> dict[str, Any]:
    """抓 1 年日線，計算 SMA/RSI/MACD + 近期高低。"""
    try:
        hist = ticker.history(period="1y", auto_adjust=True)
    except Exception as exc:
        return {"error": f"history_failed: {exc}"}

    if hist is None or hist.empty:
        return {"error": "empty_history"}

    close = hist["Close"].dropna()
    if close.empty:
        return {"error": "empty_close"}

    last_close = _safe_float(close.iloc[-1])
    period_high = _safe_float(close.max())
    period_low = _safe_float(close.min())
    macd = _calculate_macd(close)

    return {
        "last_close": last_close,
        "period_high_52w": period_high,
        "period_low_52w": period_low,
        "sma_5": _calculate_sma(close, 5),
        "sma_20": _calculate_sma(close, 20),
        "sma_60": _calculate_sma(close, 60),
        "sma_200": _calculate_sma(close, 200),
        "rsi_14": _calculate_rsi(close, 14),
        "macd": macd["macd"],
        "macd_signal": macd["signal"],
        "macd_histogram": macd["histogram"],
        "volume_latest": int(hist["Volume"].iloc[-1]) if "Volume" in hist else None,
        "data_points": len(close),
    }


def _extract_fundamentals(info: dict[str, Any]) -> dict[str, Any]:
    """從 yfinance info 字典挑出白名單欄位。"""
    result: dict[str, Any] = {}
    for key in _INFO_FIELDS:
        val = info.get(key)
        if isinstance(val, (int, float)):
            result[key] = _safe_float(val)
        elif isinstance(val, str):
            result[key] = val
        # 略過其他型別
    return result


def _fetch_symbol(symbol: str) -> dict[str, Any]:
    """抓單一 symbol 的價格序列 + 基本面資料。"""
    try:
        ticker = yf.Ticker(symbol)
    except Exception as exc:
        return {"symbol": symbol, "data_unavailable": True, "error": str(exc)}

    price = _fetch_price_series(ticker)
    if "error" in price:
        return {"symbol": symbol, "data_unavailable": True, "error": price["error"]}

    fundamentals: dict[str, Any] = {}
    try:
        info = ticker.info or {}
        fundamentals = _extract_fundamentals(info)
    except Exception as exc:
        fundamentals = {"error": f"info_failed: {exc}"}

    return {
        "symbol": symbol,
        "data_unavailable": False,
        "price": price,
        "fundamentals": fundamentals,
    }


def build_market_snapshot(portfolio: Portfolio) -> dict[str, Any]:
    """一次抓齊所有 holding + 大盤背景資料。

    回傳確定性序列化的 dict：鍵排序、數值 round，以利 prompt cache 命中。
    """
    snapshot: dict[str, Any] = {
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "base_currency": portfolio.base_currency,
        "holdings_data": {},
        "benchmarks": {},
    }

    seen: set[str] = set()
    for holding in portfolio.holdings:
        sym = holding.symbol.upper()
        if sym in seen:
            continue
        seen.add(sym)
        snapshot["holdings_data"][sym] = _fetch_symbol(sym)

    for bench in _BENCHMARK_SYMBOLS:
        snapshot["benchmarks"][bench] = _fetch_symbol(bench)

    return snapshot


def serialize_snapshot(snapshot: dict[str, Any]) -> str:
    """確定性 JSON 序列化：sort_keys=True、固定 indent。"""
    return json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True)
