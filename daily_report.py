"""
台灣市場日報產生器
將市場資料輸出為 Markdown 日報檔案

用法：
  python3 daily_report.py 2026-03-06              # 線上模式，輸出 market_data_20260306.md
  python3 daily_report.py 2026-03-06 --local      # 本地模式
  python3 daily_report.py 2026-03-06 --stdout     # 印至終端機，不寫檔
"""
import json
import os
import sys
from datetime import datetime
from urllib.request import urlopen, Request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

API_URLS = {
    "FMTQIK": "https://www.twse.com.tw/exchangeReport/FMTQIK?response=open_data",
    "BFI82U": "https://openapi.twse.com.tw/v1/exchangeReport/BFI82U",
    "bond_yield": "https://www.tpex.org.tw/openapi/v1/tpex_bond_benchmark_yield",
}


def fetch_online(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_local(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到檔案: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_data(name, local_mode=False):
    if local_mode:
        return load_local(f"{name}.json")
    return fetch_online(API_URLS[name])


def to_roc_date(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.year - 1911}/{dt.month:02d}/{dt.day:02d}"


def format_amount(amount_str):
    try:
        val = int(str(amount_str).replace(",", ""))
        return f"{val / 1e8:,.2f} 億元"
    except (ValueError, AttributeError):
        return str(amount_str)


def weekday_zh(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    names = ["一", "二", "三", "四", "五", "六", "日"]
    return names[dt.weekday()]


def generate_report(target_date, local_mode=False):
    roc_date = to_roc_date(target_date)
    wday = weekday_zh(target_date)
    display_date = target_date.replace("-", "/")

    lines = []
    lines.append(f"# 台灣市場資料 — {display_date}（週{wday}）")
    lines.append("")

    # ── 債券 ──
    lines.append("## 一、債券資料")
    lines.append("")
    lines.append("| 天期 | 指標債代號 | 平均殖利率 | 最高 | 最低 | 變動(bp) |")
    lines.append("|------|-----------|-----------|------|------|---------|")
    try:
        bond_data = get_data("bond_yield", local_mode)
        found_bond = False
        for tenor_label in ["5年", "10年"]:
            row = next((r for r in bond_data
                        if r.get("日期") == roc_date and r.get("天期") == tenor_label), None)
            if row:
                found_bond = True
                lines.append(
                    f"| {tenor_label}期 "
                    f"| {row.get('指標債券代號', 'N/A')} "
                    f"| {row.get('平均殖利率', 'N/A')}% "
                    f"| {row.get('最高殖利率', 'N/A')}% "
                    f"| {row.get('最低殖利率', 'N/A')}% "
                    f"| {row.get('變動(bp)', 'N/A')} |"
                )
            else:
                lines.append(f"| {tenor_label}期 | — | — | — | — | — |")
        if not found_bond:
            lines.append(f"> 找不到 {roc_date} 的債券資料")
    except Exception as e:
        lines.append(f"> 取得債券資料失敗: {e}")
    lines.append("")

    # ── 股市 ──
    lines.append("## 二、股市資訊")
    lines.append("")
    lines.append("### 台股收盤行情")
    lines.append("")
    lines.append("| 項目 | 數據 |")
    lines.append("|------|------|")
    try:
        taiex_data = get_data("FMTQIK", local_mode)
        taiex = next((r for r in taiex_data if r.get("日期") == roc_date), None)
        if taiex:
            close_idx = taiex.get("發行量加權股價指數", "N/A")
            change = taiex.get("漲跌點數", "N/A")
            volume = format_amount(taiex.get("成交金額", "0"))
            lines.append(f"| 收盤指數 | **{close_idx} 點** |")
            lines.append(f"| 漲跌點數 | **{change} 點** |")
            lines.append(f"| 成交金額 | {volume} |")
        else:
            lines.append(f"| — | 找不到 {roc_date} 的資料 |")
    except Exception as e:
        lines.append(f"> 取得股市資料失敗: {e}")
    lines.append("")

    # ── 三大法人 ──
    lines.append("### 三大法人買賣超金額")
    lines.append("")
    lines.append("| 法人 | 買進 | 賣出 | 買賣超 |")
    lines.append("|------|------|------|--------|")
    try:
        all_investors = get_data("BFI82U", local_mode)
        if all_investors and "日期" in all_investors[0]:
            investors = [r for r in all_investors if r.get("日期") == roc_date]
        else:
            investors = all_investors

        if investors:
            for row in investors:
                name = row.get("單位名稱", "N/A")
                buy = format_amount(row.get("買進金額", "0"))
                sell = format_amount(row.get("賣出金額", "0"))
                diff = format_amount(row.get("買賣差額", "0"))
                lines.append(f"| {name} | {buy} | {sell} | {diff} |")
        else:
            lines.append(f"| — | 找不到 {roc_date} 的三大法人資料 | | |")
    except Exception as e:
        lines.append(f"> 取得三大法人資料失敗: {e}")
    lines.append("")

    # ── 來源 ──
    lines.append("---")
    lines.append("")
    lines.append("## 資料來源")
    lines.append("")
    if local_mode:
        lines.append(f"- 本地資料目錄: `{DATA_DIR}/`")
    else:
        lines.append("- 台灣證交所 OpenAPI: https://openapi.twse.com.tw/")
        lines.append("- 櫃買中心 OpenAPI: https://www.tpex.org.tw/openapi/")
    lines.append("")

    return "\n".join(lines)


def main():
    args = sys.argv[1:]
    target_date = datetime.today().strftime("%Y-%m-%d")
    local_mode = False
    stdout_mode = False

    for arg in args:
        if arg == "--local":
            local_mode = True
        elif arg == "--stdout":
            stdout_mode = True
        elif not arg.startswith("-"):
            # Accept both 2026-03-06 and 2026/3/6 formats
            target_date = arg.replace("/", "-")
            # Normalize to YYYY-MM-DD
            try:
                dt = datetime.strptime(target_date, "%Y-%m-%d")
                target_date = dt.strftime("%Y-%m-%d")
            except ValueError:
                print(f"日期格式錯誤: {arg}，請使用 YYYY-MM-DD 或 YYYY/M/D")
                sys.exit(1)

    report = generate_report(target_date, local_mode)

    if stdout_mode:
        print(report)
    else:
        date_compact = target_date.replace("-", "")
        filename = f"market_data_{date_compact}.md"
        output_path = os.path.join(SCRIPT_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"日報已輸出至: {filename}")


if __name__ == "__main__":
    main()
