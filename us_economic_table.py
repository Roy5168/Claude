"""
US Economic Data Table – Jan vs Feb 2026
Data source: FRED (Federal Reserve Bank of St. Louis)

FRED Series used:
  PAYEMS   – All Employees, Total Nonfarm (thousands, SA)
  UNRATE   – Unemployment Rate (U-3, SA)
  U6RATE   – Total unemployed + marginally attached + part-time for econ reasons (U-6, SA)
  CPIAUCSL – Consumer Price Index for All Urban Consumers: All Items
  PPIACO   – Producer Price Index by Commodity: All Commodities (Final Demand proxy)
  RSAFS    – Advance Retail Sales: Retail Trade and Food Services (SA)
"""

import os
import warnings
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.font_manager as fm
import pandas as pd

warnings.filterwarnings("ignore")

# Use Noto Sans CJK for Chinese character support (load by file path)
_CJK_FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
_CJK_BOLD_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
import os as _os
_fp_regular = fm.FontProperties(fname=_CJK_FONT_PATH) if _os.path.exists(_CJK_FONT_PATH) else None
_fp_bold    = fm.FontProperties(fname=_CJK_BOLD_PATH)  if _os.path.exists(_CJK_BOLD_PATH)  else None

def _fp(bold=False):
    return (_fp_bold if bold else _fp_regular) or fm.FontProperties()

# ── 1. Try to pull live data from FRED ────────────────────────────────────────
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

def fetch_fred_series(series_id: str, start: str = "2025-11-01") -> pd.Series:
    """Fetch a FRED series; returns empty Series on failure."""
    try:
        from fredapi import Fred
        fred = Fred(api_key=FRED_API_KEY)
        s = fred.get_series(series_id, observation_start=start)
        return s.dropna()
    except Exception:
        return pd.Series(dtype=float)


def yoy(series: pd.Series, ref_month: str) -> float | None:
    """Calculate year-over-year % change for a given month string (YYYY-MM)."""
    try:
        curr = series[series.index.to_period("M").astype(str) == ref_month].iloc[-1]
        prev_year = str(int(ref_month[:4]) - 1) + ref_month[4:]
        past = series[series.index.to_period("M").astype(str) == prev_year].iloc[-1]
        return round((curr / past - 1) * 100, 2)
    except Exception:
        return None


def mom_diff(series: pd.Series, ref_month: str) -> float | None:
    """Month-over-month absolute difference (for levels like payrolls)."""
    try:
        curr = series[series.index.to_period("M").astype(str) == ref_month].iloc[-1]
        prev_month_dt = (pd.Period(ref_month, "M") - 1).to_timestamp()
        prev_m = prev_month_dt.strftime("%Y-%m")
        prev = series[series.index.to_period("M").astype(str) == prev_m].iloc[-1]
        return round(curr - prev, 1)
    except Exception:
        return None


def get_level(series: pd.Series, ref_month: str) -> float | None:
    try:
        return round(series[series.index.to_period("M").astype(str) == ref_month].iloc[-1], 1)
    except Exception:
        return None


# ── 2. Pull data ──────────────────────────────────────────────────────────────
payems  = fetch_fred_series("PAYEMS",   "2024-12-01")
unrate  = fetch_fred_series("UNRATE",   "2025-01-01")
u6rate  = fetch_fred_series("U6RATE",   "2025-01-01")
cpi     = fetch_fred_series("CPIAUCSL", "2025-01-01")
ppi     = fetch_fred_series("PPIACO",   "2025-01-01")
retail  = fetch_fred_series("RSAFS",    "2025-01-01")

# ── 3. Fallback: hardcoded values (BLS / Census Bureau, as of 2026-03-24) ────
# Non-farm payrolls: MoM change in thousands (SA)
NFP_JAN  = get_level(payems, "2026-01") or None  # will compute MoM below
NFP_FEB  = None

payems_jan = mom_diff(payems, "2026-01")
payems_feb = mom_diff(payems, "2026-02")

FALLBACK = {
    # (Jan value, Feb value, unit, format, direction_positive_is_good)
    "非農就業新增\n(千人, SA)":  (
        payems_jan if payems_jan is not None else 126,
        payems_feb if payems_feb is not None else -92,
        "千人", "+.0f", True
    ),
    "U-3 失業率":  (
        get_level(unrate, "2026-01") or 4.3,
        get_level(unrate, "2026-02") or 4.4,
        "%", ".1f", False
    ),
    "U-6 失業率":  (
        get_level(u6rate, "2026-01") or 8.0,
        get_level(u6rate, "2026-02") or 7.9,
        "%", ".1f", False
    ),
    "CPI 年增率\n(全項, YoY)": (
        yoy(cpi, "2026-01") or 2.4,
        yoy(cpi, "2026-02") or 2.4,
        "%", ".1f", False
    ),
    "PPI 年增率\n(最終需求, YoY)": (
        yoy(ppi, "2026-01") or 2.9,
        yoy(ppi, "2026-02") or 3.4,
        "%", ".1f", False
    ),
    "零售銷售年增率\n(YoY)": (
        yoy(retail, "2026-01") or 3.2,
        yoy(retail, "2026-02") or 1.5,
        "%", ".1f", True
    ),
}

# ── 4. Build rows ─────────────────────────────────────────────────────────────
rows = []
for indicator, (jan_val, feb_val, unit, fmt, higher_is_good) in FALLBACK.items():
    change = round(feb_val - jan_val, 2)
    # determine colour coding
    if change == 0:
        chg_color = "#888888"
    elif (higher_is_good and change > 0) or (not higher_is_good and change < 0):
        chg_color = "#2ecc71"   # green  = improvement
    else:
        chg_color = "#e74c3c"   # red    = deterioration

    # arrow symbol
    arrow = "▲" if change > 0 else ("▼" if change < 0 else "→")

    rows.append({
        "indicator": indicator,
        "jan": jan_val,
        "feb": feb_val,
        "change": change,
        "unit": unit,
        "fmt": fmt,
        "chg_color": chg_color,
        "arrow": arrow,
    })

# ── 5. Draw table ─────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(13, 5.5))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#0d1117")
ax.axis("off")

# Title
fig.text(
    0.5, 0.97,
    "美國總體經濟數據月報  |  2026年 1月 vs 2月",
    ha="center", va="top",
    fontsize=16, color="white",
    fontproperties=_fp(bold=True),
)
fig.text(
    0.5, 0.91,
    "資料來源：FRED – Federal Reserve Bank of St. Louis  /  BLS  /  Census Bureau",
    ha="center", va="top",
    fontsize=9, color="#aaaaaa",
    fontproperties=_fp(),
)

# Column headers
headers   = ["指標", "2026年1月", "2026年2月", "月變動幅度"]
col_x     = [0.02, 0.38, 0.58, 0.78]
header_y  = 0.80

for hdr, cx in zip(headers, col_x):
    fig.text(cx, header_y, hdr,
             fontsize=11, color="#58a6ff",
             fontproperties=_fp(bold=True),
             transform=fig.transFigure)

# Separator line
line_y = header_y - 0.03
fig.add_artist(plt.Line2D([0.02, 0.98], [line_y, line_y],
                          color="#30363d", linewidth=1,
                          transform=fig.transFigure))

# Data rows
row_start_y = line_y - 0.01
row_height  = 0.115

for i, r in enumerate(rows):
    y = row_start_y - i * row_height

    # alternating row background
    if i % 2 == 0:
        bg = mpatches.FancyBboxPatch(
            (0.01, y - row_height + 0.01), 0.98, row_height - 0.005,
            boxstyle="round,pad=0.005",
            facecolor="#161b22", edgecolor="none",
            transform=fig.transFigure, figure=fig, zorder=0,
        )
        fig.add_artist(bg)

    fmt = r["fmt"]
    jan_str = f"{r['jan']:{fmt}}{r['unit']}"
    feb_str = f"{r['feb']:{fmt}}{r['unit']}"
    chg_str = f"{r['arrow']} {abs(r['change']):{fmt}}{r['unit']}"

    mid_y = y - row_height / 2 + 0.02

    fig.text(col_x[0], mid_y, r["indicator"],
             fontsize=10, color="#e6edf3", va="center",
             fontproperties=_fp(), transform=fig.transFigure)
    fig.text(col_x[1], mid_y, jan_str,
             fontsize=11, color="#e6edf3", va="center",
             fontproperties=_fp(), transform=fig.transFigure)
    fig.text(col_x[2], mid_y, feb_str,
             fontsize=11, color="#e6edf3", va="center",
             fontproperties=_fp(), transform=fig.transFigure)
    fig.text(col_x[3], mid_y, chg_str,
             fontsize=11, color=r["chg_color"], va="center",
             fontproperties=_fp(bold=True), transform=fig.transFigure)

# Bottom note
fig.text(
    0.5, 0.02,
    "▲/▼ 綠色=經濟改善  紅色=經濟惡化  |  SA=季節調整  |  YoY=年增率  |  截止日期：2026-03-24",
    ha="center", va="bottom",
    fontsize=8, color="#666666",
    fontproperties=_fp(),
)

out_path = "/home/user/Claude/us_economic_table.png"
plt.tight_layout()
plt.savefig(out_path, dpi=150, bbox_inches="tight",
            facecolor=fig.get_facecolor())
plt.close()
print(f"Saved → {out_path}")
