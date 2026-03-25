#!/usr/bin/env python3
"""台灣金融市場日報 — 擷取台債殖利率、台股指數、三大法人、隔夜拆款利率、RP利率"""

import sys
import csv
import io
import tempfile
import os
from datetime import datetime, timedelta

import requests
import xlrd

HEADERS = {"User-Agent": "Mozilla/5.0"}


# ── 日期工具 ──────────────────────────────────────────────

def prev_business_day(dt):
    """往前推一個工作日（跳過週末）"""
    dt -= timedelta(days=1)
    while dt.weekday() >= 5:  # 5=Sat, 6=Sun
        dt -= timedelta(days=1)
    return dt


def latest_business_day():
    """取得最近的交易日（若今天是週末或盤前則往前推）"""
    now = datetime.now()
    dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if dt.weekday() >= 5:
        return prev_business_day(dt + timedelta(days=1))
    if now.hour < 15:
        return prev_business_day(dt)
    return dt


# ── 台債指標債殖利率 ──────────────────────────────────────

def fetch_bond_yield(dt):
    """下載 BDdys100 XLS，解析 5Y/10Y 殖利率與漲跌bp"""
    yyyymmdd = dt.strftime("%Y%m%d")
    yyyy = dt.strftime("%Y")
    yyyymm = dt.strftime("%Y%m")
    url = (
        f"https://www.tpex.org.tw/storage/bond_zone/tradeinfo/govbond/"
        f"{yyyy}/{yyyymm}/BDdys100.{yyyymmdd}-C.xls"
    )
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as f:
        f.write(resp.content)
        tmp = f.name

    try:
        wb = xlrd.open_workbook(tmp)
        ws = wb.sheet_by_index(0)
        results = []
        for row_idx in [5, 6]:  # Row5=5Y, Row6=10Y
            tenor = int(ws.cell_value(row_idx, 0))
            bond_code = ws.cell_value(row_idx, 1)
            avg_yield = ws.cell_value(row_idx, 2)
            change_bp = ws.cell_value(row_idx, 4)
            results.append({
                "tenor": tenor,
                "code": bond_code,
                "yield": avg_yield,
                "change_bp": change_bp,
            })
        return results
    finally:
        os.unlink(tmp)


# ── 台股加權指數 ──────────────────────────────────────────

def fetch_taiex(dt):
    """TWSE MI_INDEX API，取加權指數收盤與漲跌"""
    date_str = dt.strftime("%Y%m%d")
    url = (
        f"https://www.twse.com.tw/exchangeReport/MI_INDEX"
        f"?response=json&date={date_str}&type=IND"
    )
    data = requests.get(url, headers=HEADERS).json()
    for row in data["tables"][0]["data"]:
        if "發行量加權" in row[0]:
            is_up = "red" in row[2]
            change = row[3].lstrip("-")
            pct = row[4].lstrip("-")
            direction = "+" if is_up else "-"
            return {
                "close": row[1],
                "direction": direction,
                "change": change,
                "pct": pct,
            }
    return None


# ── 三大法人買賣超 ────────────────────────────────────────

def fetch_institutional(dt):
    """TWSE BFI82U API，取三大法人買賣超"""
    date_str = dt.strftime("%Y%m%d")
    url = (
        f"https://www.twse.com.tw/fund/BFI82U"
        f"?response=json&dayDate={date_str}&type=day"
    )
    data = requests.get(url, headers=HEADERS).json()
    if "data" not in data or not data["data"]:
        return None
    d = data["data"]
    parse = lambda s: int(s.replace(",", ""))
    return {
        "foreign": parse(d[3][3]),
        "sit": parse(d[2][3]),
        "dealer": parse(d[0][3]) + parse(d[1][3]),
    }


# ── 金融業隔夜拆款利率 ───────────────────────────────────

def fetch_overnight_rate(target_dt):
    """CBC CSV，取目標日與前一日利率，計算變動(bp)"""
    url = "https://www.cbc.gov.tw/public/data/OpenData/WebF2.csv"
    resp = requests.get(url, headers=HEADERS)
    text = resp.content.decode("big5", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = [(r[0].strip(), float(r[1])) for r in reader if len(r) >= 2 and r[1].strip().replace(".", "").isdigit()]

    # 找目標日期（格式 YYYY/M/D）
    target_str = f"{target_dt.year}/{target_dt.month}/{target_dt.day}"
    prev_dt = prev_business_day(target_dt)
    prev_str = f"{prev_dt.year}/{prev_dt.month}/{prev_dt.day}"

    target_rate = prev_rate = None
    for date_str, rate in rows:
        if date_str == target_str:
            target_rate = rate
        elif date_str == prev_str:
            prev_rate = rate

    # 若找不到目標日，取最後兩筆
    if target_rate is None:
        if len(rows) >= 2:
            target_rate = rows[-1][1]
            prev_rate = rows[-2][1]
            target_str = rows[-1][0]
            prev_str = rows[-2][0]
        elif len(rows) >= 1:
            target_rate = rows[-1][1]
            target_str = rows[-1][0]

    diff_bp = (target_rate - prev_rate) * 100 if target_rate and prev_rate else None
    return {
        "date": target_str,
        "rate": target_rate,
        "prev_date": prev_str if prev_rate else None,
        "prev_rate": prev_rate,
        "diff_bp": diff_bp,
    }


# ── 2-10天期附買回利率 ────────────────────────────────────

def _download_repo_xls(dt):
    """下載 BDdcs001 XLS 並解析 BDdcs01b 活頁 2-10天期"""
    yyyymmdd = dt.strftime("%Y%m%d")
    yyyy = dt.strftime("%Y")
    yyyymm = dt.strftime("%Y%m")
    url = (
        f"https://www.tpex.org.tw/storage/bond_zone/tradeinfo/govbond/"
        f"{yyyy}/{yyyymm}/BDdcs001.{yyyymmdd}-C.xls"
    )
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    with tempfile.NamedTemporaryFile(suffix=".xls", delete=False) as f:
        f.write(resp.content)
        tmp = f.name

    try:
        wb = xlrd.open_workbook(tmp)
        ws = wb.sheet_by_name("BDdcs01b")
        rate = ws.cell_value(9, 7)   # 加權平均利率
        amount = ws.cell_value(9, 8)  # 金額（元）
        return {"rate": rate, "amount": amount}
    finally:
        os.unlink(tmp)


def fetch_repo_rate(target_dt):
    """取當日與前一交易日的 2-10天期 RP 資料"""
    prev_dt = prev_business_day(target_dt)
    today = _download_repo_xls(target_dt)
    prev = _download_repo_xls(prev_dt)
    diff_bp = (today["rate"] - prev["rate"]) * 100
    return {
        "rate": today["rate"],
        "amount": today["amount"],
        "prev_rate": prev["rate"],
        "prev_amount": prev["amount"],
        "diff_bp": diff_bp,
    }


# ── 輸出格式 ─────────────────────────────────────────────

def format_report(dt, bonds, taiex, inst, inst_prev, overnight, repo):
    date_str = dt.strftime("%Y/%m/%d")
    prev_dt = prev_business_day(dt)
    prev_str = prev_dt.strftime("%m/%d")

    lines = [f"## 台灣金融市場日報（{date_str}）", ""]

    # 台債殖利率
    lines.append("### 台債指標債殖利率")
    for b in bonds:
        bp = b["change_bp"]
        sign = "+" if bp >= 0 else ""
        lines.append(f"- {b['tenor']}年期：{b['yield']}%（{sign}{bp}bp）　指標券：{b['code']}")
    lines.append("")

    # 台股指數
    lines.append("### 台股加權指數")
    lines.append(f"- 收盤：{taiex['close']}（{taiex['direction']}{taiex['change']}，{taiex['direction']}{taiex['pct']}%）")
    lines.append("")

    # 三大法人
    lines.append("### 三大法人買賣超（億元）")
    for label, key in [("外資", "foreign"), ("投信", "sit"), ("自營商", "dealer")]:
        val = inst[key] / 1e8
        pval = inst_prev[key] / 1e8
        diff = val - pval
        lines.append(f"- {label}：{val:+.2f}（前日 {pval:+.2f}，變動 {diff:+.2f}）")
    lines.append("")

    # 隔夜拆款利率
    lines.append("### 金融業隔夜拆款利率")
    if overnight["prev_rate"] is not None:
        diff_bp = overnight["diff_bp"]
        sign = "+" if diff_bp >= 0 else ""
        lines.append(
            f"- 加權平均：{overnight['rate']}%"
            f"（前日 {overnight['prev_rate']}%，變動 {sign}{diff_bp:.1f}bp）"
        )
    else:
        lines.append(f"- 加權平均：{overnight['rate']}%（前日資料不可用）")
    lines.append("")

    # RP 利率
    lines.append("### 2-10天期附買回利率")
    sign = "+" if repo["diff_bp"] >= 0 else ""
    lines.append(
        f"- 加權平均：{repo['rate']}%"
        f"（前日 {repo['prev_rate']}%，變動 {sign}{repo['diff_bp']:.2f}bp）"
    )
    lines.append(
        f"- 成交金額：{repo['amount']/1e8:.2f} 億元"
        f"（前日 {repo['prev_amount']/1e8:.2f} 億元）"
    )

    return "\n".join(lines)


# ── 主程式 ────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        date_input = sys.argv[1].replace("-", "/")
        dt = datetime.strptime(date_input, "%Y/%m/%d")
    else:
        dt = latest_business_day()

    prev_dt = prev_business_day(dt)

    print(f"擷取 {dt.strftime('%Y/%m/%d')} 日報資料中...\n")

    bonds = fetch_bond_yield(dt)
    taiex = fetch_taiex(dt)
    inst = fetch_institutional(dt)
    inst_prev = fetch_institutional(prev_dt)
    overnight = fetch_overnight_rate(dt)
    repo = fetch_repo_rate(dt)

    report = format_report(dt, bonds, taiex, inst, inst_prev, overnight, repo)
    print(report)


if __name__ == "__main__":
    main()
