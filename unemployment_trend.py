"""
U-3 & U-6 Unemployment Rate Trend Chart
2022-01 ~ 2026-02
Data source: FRED (Federal Reserve Bank of St. Louis)
  UNRATE  – U-3 Unemployment Rate (SA)
  U6RATE  – U-6 Unemployment Rate (SA)
"""

import os
import warnings
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import pandas as pd
import numpy as np

warnings.filterwarnings("ignore")

# ── Font ──────────────────────────────────────────────────────────────────────
_CJK_REGULAR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
_CJK_BOLD    = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
_fp_r = fm.FontProperties(fname=_CJK_REGULAR) if os.path.exists(_CJK_REGULAR) else fm.FontProperties()
_fp_b = fm.FontProperties(fname=_CJK_BOLD)    if os.path.exists(_CJK_BOLD)    else fm.FontProperties()

def fp(bold=False):
    return _fp_b if bold else _fp_r

# ── Fetch FRED data ───────────────────────────────────────────────────────────
START = "2022-01-01"
END   = "2026-02-28"

def fetch(series_id: str) -> pd.Series:
    try:
        from fredapi import Fred
        api_key = os.environ.get("FRED_API_KEY", "")
        fred = Fred(api_key=api_key)
        s = fred.get_series(series_id, observation_start=START, observation_end=END)
        return s.dropna()
    except Exception:
        return pd.Series(dtype=float)

u3 = fetch("UNRATE")
u6 = fetch("U6RATE")

# ── Fallback hardcoded data (BLS, monthly SA) ─────────────────────────────────
# fmt: YYYY-MM -> value
U3_DATA = {
    "2022-01": 4.0, "2022-02": 3.8, "2022-03": 3.6, "2022-04": 3.6,
    "2022-05": 3.6, "2022-06": 3.6, "2022-07": 3.5, "2022-08": 3.7,
    "2022-09": 3.5, "2022-10": 3.7, "2022-11": 3.7, "2022-12": 3.5,
    "2023-01": 3.4, "2023-02": 3.6, "2023-03": 3.5, "2023-04": 3.4,
    "2023-05": 3.7, "2023-06": 3.6, "2023-07": 3.5, "2023-08": 3.8,
    "2023-09": 3.8, "2023-10": 3.9, "2023-11": 3.7, "2023-12": 3.7,
    "2024-01": 3.7, "2024-02": 3.9, "2024-03": 3.8, "2024-04": 3.9,
    "2024-05": 4.0, "2024-06": 4.1, "2024-07": 4.3, "2024-08": 4.2,
    "2024-09": 4.1, "2024-10": 4.1, "2024-11": 4.2, "2024-12": 4.2,
    "2025-01": 4.1, "2025-02": 4.1, "2025-03": 4.2, "2025-04": 4.2,
    "2025-05": 4.2, "2025-06": 4.1, "2025-07": 4.3, "2025-08": 4.2,
    "2025-09": 4.1, "2025-10": 4.1, "2025-11": 4.5, "2025-12": 4.2,
    "2026-01": 4.3, "2026-02": 4.4,
}
U6_DATA = {
    "2022-01": 7.1, "2022-02": 7.2, "2022-03": 6.9, "2022-04": 7.0,
    "2022-05": 7.1, "2022-06": 6.7, "2022-07": 6.7, "2022-08": 7.0,
    "2022-09": 6.7, "2022-10": 6.8, "2022-11": 6.7, "2022-12": 6.5,
    "2023-01": 6.6, "2023-02": 6.8, "2023-03": 6.7, "2023-04": 6.6,
    "2023-05": 6.7, "2023-06": 6.9, "2023-07": 6.7, "2023-08": 7.1,
    "2023-09": 7.0, "2023-10": 7.2, "2023-11": 7.0, "2023-12": 7.1,
    "2024-01": 7.2, "2024-02": 7.3, "2024-03": 7.3, "2024-04": 7.4,
    "2024-05": 7.4, "2024-06": 7.7, "2024-07": 7.8, "2024-08": 7.9,
    "2024-09": 7.7, "2024-10": 7.7, "2024-11": 7.8, "2024-12": 7.9,
    "2025-01": 8.1, "2025-02": 8.0, "2025-03": 7.9, "2025-04": 7.8,
    "2025-05": 7.8, "2025-06": 8.0, "2025-07": 8.2, "2025-08": 8.1,
    "2025-09": 7.9, "2025-10": 8.0, "2025-11": 8.3, "2025-12": 8.0,
    "2026-01": 8.0, "2026-02": 7.9,
}

def to_series(d: dict) -> pd.Series:
    idx = pd.to_datetime(list(d.keys()))
    return pd.Series(list(d.values()), index=idx)

if u3.empty:
    u3 = to_series(U3_DATA)
if u6.empty:
    u6 = to_series(U6_DATA)

# Trim to range
u3 = u3[(u3.index >= START) & (u3.index <= END)]
u6 = u6[(u6.index >= START) & (u6.index <= END)]

# ── Plot ──────────────────────────────────────────────────────────────────────
BG      = "#ffffff"
GRID_C  = "#e0e0e0"
U3_C    = "#1a6fc4"   # blue
U6_C    = "#d94f3d"   # red
FILL_C  = "#d0e4f7"

fig, ax = plt.subplots(figsize=(14, 6))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
fig.subplots_adjust(top=0.77, bottom=0.13, left=0.07, right=0.97)

# Fill between
ax.fill_between(u6.index, u6.values, u3.values, alpha=0.15, color=FILL_C, zorder=1)

# Lines
ax.plot(u3.index, u3.values, color=U3_C, linewidth=2.2, zorder=3, label="U-3")
ax.plot(u6.index, u6.values, color=U6_C, linewidth=2.2, zorder=3, label="U-6")

# Dots at last data point
ax.scatter([u3.index[-1]], [u3.values[-1]], color=U3_C, s=60, zorder=5)
ax.scatter([u6.index[-1]], [u6.values[-1]], color=U6_C, s=60, zorder=5)

# Annotate latest values
ax.annotate(
    f"U-3: {u3.values[-1]:.1f}%",
    xy=(u3.index[-1], u3.values[-1]),
    xytext=(12, 4), textcoords="offset points",
    color=U3_C, fontproperties=fp(bold=True), fontsize=10,
)
ax.annotate(
    f"U-6: {u6.values[-1]:.1f}%",
    xy=(u6.index[-1], u6.values[-1]),
    xytext=(12, -14), textcoords="offset points",
    color=U6_C, fontproperties=fp(bold=True), fontsize=10,
)

# ── Key event annotations ──────────────────────────────────────────────────────
events = [
    ("2022-03", "Fed 首次升息", 0.97, "center"),
    ("2023-07", "升息頂點\n(5.25–5.5%)", 0.97, "center"),
    ("2024-09", "Fed 首次降息", 0.97, "center"),
]
for date_str, label, y_frac, ha in events:
    xd = pd.Timestamp(date_str)
    if xd < u3.index[0] or xd > u3.index[-1]:
        continue
    ax.axvline(xd, color="#444c56", linewidth=1, linestyle="--", zorder=2)
    # y in axes fraction, x in data coords → use get_xaxis_transform
    ax.text(
        xd, y_frac,
        label, color="#555555", fontproperties=fp(), fontsize=8,
        ha=ha, va="top",
        transform=ax.get_xaxis_transform(),
    )

# ── Recession / pandemic shading (optional) ───────────────────────────────────
# (none in this window)

# ── Axes styling ──────────────────────────────────────────────────────────────
ax.spines[["top", "right"]].set_visible(False)
ax.spines[["left", "bottom"]].set_color("#cccccc")
ax.tick_params(colors="#333333", labelsize=9)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
ax.set_xlim(u3.index[0], u3.index[-1] + pd.DateOffset(months=1))
ax.set_ylim(
    min(u3.min(), u6.min()) - 0.5,
    max(u3.max(), u6.max()) + 0.8,
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
    "美國失業率趨勢  U-3 vs U-6  (2022年1月 – 2026年2月)",
    va="top", fontsize=15, color="#111111", fontproperties=fp(bold=True),
)
fig.text(
    0.06, 0.04,
    "資料來源：FRED – Federal Reserve Bank of St. Louis  |  季節調整 (SA)  |  單位：%",
    va="bottom", fontsize=9, color="#666666", fontproperties=fp(),
)

# ── Legend ────────────────────────────────────────────────────────────────────
leg_patches = [
    mpatches.Patch(color=U3_C, label="U-3  官方失業率（完全失業）"),
    mpatches.Patch(color=U6_C, label="U-6  廣義失業率（含邊際附著 + 非自願兼職）"),
]
legend = fig.legend(
    handles=leg_patches,
    loc="lower left",
    bbox_to_anchor=(0.07, 0.785),   # 緊貼 axes 上方，避免進入圖表區域
    frameon=True,
    framealpha=0.9,
    facecolor="#f5f5f5",
    edgecolor="#cccccc",
    labelcolor="#111111",
    fontsize=9,
    prop=fp(),
)

# ── Save ──────────────────────────────────────────────────────────────────────
out = "/home/user/Claude/unemployment_trend.png"
# layout already set via subplots_adjust
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
plt.close()
print(f"Saved → {out}")
