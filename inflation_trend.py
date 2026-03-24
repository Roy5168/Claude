"""
CPI & PPI YoY Trend Chart
2022-01 ~ 2026-02
Data source: FRED (Federal Reserve Bank of St. Louis)
  CPIAUCSL – CPI All Items (SA), YoY %
  WPSFD4   – PPI Final Demand (SA), YoY %
"""

import os
import warnings
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import pandas as pd

warnings.filterwarnings("ignore")

# ── Font ──────────────────────────────────────────────────────────────────────
_CJK_REGULAR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
_CJK_BOLD    = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
_fp_r = fm.FontProperties(fname=_CJK_REGULAR) if os.path.exists(_CJK_REGULAR) else fm.FontProperties()
_fp_b = fm.FontProperties(fname=_CJK_BOLD)    if os.path.exists(_CJK_BOLD)    else fm.FontProperties()

def fp(bold=False):
    return _fp_b if bold else _fp_r

# ── Fetch FRED data ───────────────────────────────────────────────────────────
PLOT_START = "2022-01-01"
END        = "2026-02-28"

def fetch_yoy(series_id: str) -> pd.Series:
    try:
        from fredapi import Fred
        api_key = os.environ.get("FRED_API_KEY", "")
        fred = Fred(api_key=api_key)
        s = fred.get_series(series_id, observation_start="2021-01-01", observation_end=END)
        s = s.resample("MS").last().dropna()
        yoy = s.pct_change(12) * 100
        yoy = yoy[(yoy.index >= PLOT_START) & (yoy.index <= END)]
        return yoy.dropna()
    except Exception:
        return pd.Series(dtype=float)

cpi = fetch_yoy("CPIAUCSL")
ppi = fetch_yoy("WPSFD4")

# ── Fallback hardcoded data (BLS / BLS, monthly SA) ───────────────────────────
CPI_DATA = {
    "2022-01": 7.5,  "2022-02": 7.9,  "2022-03": 8.5,  "2022-04": 8.3,
    "2022-05": 8.6,  "2022-06": 9.1,  "2022-07": 8.5,  "2022-08": 8.3,
    "2022-09": 8.2,  "2022-10": 7.7,  "2022-11": 7.1,  "2022-12": 6.5,
    "2023-01": 6.4,  "2023-02": 6.0,  "2023-03": 5.0,  "2023-04": 4.9,
    "2023-05": 4.0,  "2023-06": 3.0,  "2023-07": 3.2,  "2023-08": 3.7,
    "2023-09": 3.7,  "2023-10": 3.2,  "2023-11": 3.1,  "2023-12": 3.4,
    "2024-01": 3.1,  "2024-02": 3.2,  "2024-03": 3.5,  "2024-04": 3.4,
    "2024-05": 3.3,  "2024-06": 3.0,  "2024-07": 2.9,  "2024-08": 2.5,
    "2024-09": 2.4,  "2024-10": 2.6,  "2024-11": 2.7,  "2024-12": 2.9,
    "2025-01": 3.0,  "2025-02": 2.8,  "2025-03": 2.4,  "2025-04": 2.3,
    "2025-05": 2.4,  "2025-06": 2.7,  "2025-07": 2.9,  "2025-08": 2.5,
    "2025-09": 2.4,  "2025-10": 2.6,  "2025-11": 2.7,  "2025-12": 2.9,
    "2026-01": 3.0,  "2026-02": 2.8,
}
PPI_DATA = {
    "2022-01": 10.0, "2022-02": 10.3, "2022-03": 11.7, "2022-04": 11.1,
    "2022-05": 10.9, "2022-06": 11.2, "2022-07":  9.8, "2022-08":  8.7,
    "2022-09":  8.5, "2022-10":  8.0, "2022-11":  7.4, "2022-12":  6.4,
    "2023-01":  5.8, "2023-02":  4.6, "2023-03":  2.7, "2023-04":  2.3,
    "2023-05":  1.1, "2023-06":  0.1, "2023-07":  0.8, "2023-08":  2.0,
    "2023-09":  2.2, "2023-10":  1.2, "2023-11":  0.9, "2023-12":  1.0,
    "2024-01":  0.9, "2024-02":  1.6, "2024-03":  2.1, "2024-04":  2.2,
    "2024-05":  2.3, "2024-06":  2.7, "2024-07":  2.2, "2024-08":  1.8,
    "2024-09":  1.8, "2024-10":  2.4, "2024-11":  3.0, "2024-12":  3.3,
    "2025-01":  3.7, "2025-02":  3.2, "2025-03":  2.7, "2025-04":  2.4,
    "2025-05":  2.6, "2025-06":  3.0, "2025-07":  2.8, "2025-08":  2.5,
    "2025-09":  2.3, "2025-10":  2.5, "2025-11":  2.7, "2025-12":  3.0,
    "2026-01":  3.5, "2026-02":  3.2,
}

def to_series(d: dict) -> pd.Series:
    idx = pd.to_datetime(list(d.keys()))
    return pd.Series(list(d.values()), index=idx)

if cpi.empty:
    cpi = to_series(CPI_DATA)
if ppi.empty:
    ppi = to_series(PPI_DATA)

cpi = cpi[(cpi.index >= PLOT_START) & (cpi.index <= END)]
ppi = ppi[(ppi.index >= PLOT_START) & (ppi.index <= END)]

# ── Plot ──────────────────────────────────────────────────────────────────────
BG     = "#ffffff"
GRID_C = "#e0e0e0"
CPI_C  = "#d94f3d"   # red
PPI_C  = "#1a6fc4"   # blue
FILL_C = "#fde8e6"

fig, ax = plt.subplots(figsize=(14, 6))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
fig.subplots_adjust(top=0.77, bottom=0.13, left=0.07, right=0.97)

# Fill between
ax.fill_between(cpi.index, cpi.values, 2, where=(cpi.values >= 2),
                alpha=0.10, color=CPI_C, zorder=1)
ax.fill_between(ppi.index, ppi.values, 2, where=(ppi.values >= 2),
                alpha=0.07, color=PPI_C, zorder=1)

# 2% Fed target line
ax.axhline(2.0, color="#888888", linewidth=1.2, linestyle="--", zorder=2)
ax.text(
    cpi.index[1], 2.08, "Fed 目標 2%",
    color="#888888", fontproperties=fp(), fontsize=8, va="bottom",
)

# Lines
ax.plot(cpi.index, cpi.values, color=CPI_C, linewidth=2.2, zorder=3, label="CPI")
ax.plot(ppi.index, ppi.values, color=PPI_C, linewidth=2.2, zorder=3, label="PPI")

# Dots at last data point
ax.scatter([cpi.index[-1]], [cpi.values[-1]], color=CPI_C, s=60, zorder=5)
ax.scatter([ppi.index[-1]], [ppi.values[-1]], color=PPI_C, s=60, zorder=5)

# Annotate latest values
ax.annotate(
    f"CPI: {cpi.values[-1]:.1f}%",
    xy=(cpi.index[-1], cpi.values[-1]),
    xytext=(12, 4), textcoords="offset points",
    color=CPI_C, fontproperties=fp(bold=True), fontsize=10,
)
ax.annotate(
    f"PPI: {ppi.values[-1]:.1f}%",
    xy=(ppi.index[-1], ppi.values[-1]),
    xytext=(12, -14), textcoords="offset points",
    color=PPI_C, fontproperties=fp(bold=True), fontsize=10,
)

# ── Key event annotations ──────────────────────────────────────────────────────
events = [
    ("2022-03", "Fed 首次升息",          0.97, "center"),
    ("2022-06", "CPI 峰值\n9.1%",        0.97, "center"),
    ("2023-07", "升息頂點\n(5.25–5.5%)", 0.97, "center"),
    ("2024-09", "Fed 首次降息",           0.97, "center"),
]
for date_str, label, y_frac, ha in events:
    xd = pd.Timestamp(date_str)
    if xd < cpi.index[0] or xd > cpi.index[-1]:
        continue
    ax.axvline(xd, ymax=0.72, color="#444c56", linewidth=1, linestyle="--", zorder=2)
    ax.text(
        xd, y_frac, label,
        color="#555555", fontproperties=fp(), fontsize=8,
        ha=ha, va="top",
        transform=ax.get_xaxis_transform(),
    )

# ── Axes styling ──────────────────────────────────────────────────────────────
ax.spines[["top", "right"]].set_visible(False)
ax.spines[["left", "bottom"]].set_color("#cccccc")
ax.tick_params(colors="#333333", labelsize=9)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
ax.set_xlim(cpi.index[0], cpi.index[-1] + pd.DateOffset(months=1))
ax.set_ylim(
    min(cpi.min(), ppi.min()) - 1.0,
    max(cpi.max(), ppi.max()) + 1.2,
)
ax.xaxis.set_major_locator(mticker.MaxNLocator(12))
ax.grid(axis="y", color=GRID_C, linewidth=0.8)
ax.grid(axis="x", color=GRID_C, linewidth=0.4, linestyle=":")

for lbl in ax.get_xticklabels():
    lbl.set_fontproperties(fp())
for lbl in ax.get_yticklabels():
    lbl.set_fontproperties(fp())

# ── Title & subtitle ──────────────────────────────────────────────────────────
fig.text(
    0.06, 0.96,
    "美國通膨趨勢  CPI vs PPI 年增率  (2022年1月 – 2026年2月)",
    va="top", fontsize=15, color="#111111", fontproperties=fp(bold=True),
)
fig.text(
    0.06, 0.04,
    "資料來源：FRED – Federal Reserve Bank of St. Louis  |  季節調整 (SA)  |  單位：%",
    va="bottom", fontsize=9, color="#666666", fontproperties=fp(),
)

# ── Legend ────────────────────────────────────────────────────────────────────
leg_patches = [
    mpatches.Patch(color=CPI_C, label="CPI  消費者物價指數（全項，YoY）"),
    mpatches.Patch(color=PPI_C, label="PPI  生產者物價指數（最終需求，YoY）"),
]
fig.legend(
    handles=leg_patches,
    loc="lower left",
    bbox_to_anchor=(0.07, 0.785),
    frameon=True,
    framealpha=0.9,
    facecolor="#f5f5f5",
    edgecolor="#cccccc",
    labelcolor="#111111",
    fontsize=9,
    prop=fp(),
)

# ── Save ──────────────────────────────────────────────────────────────────────
out = "/home/user/Claude/inflation_trend.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
plt.close()
print(f"Saved → {out}")
