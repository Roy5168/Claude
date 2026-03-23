"""
台灣市場資料擷取工具
支援兩種模式：
  1. --online   從 TWSE/TPEX OpenAPI 線上擷取（預設）
  2. --local    從本地 data/ 目錄讀取 JSON 檔案

用法：
  python3 fetch_market_data.py 2026-03-20              # 線上模式
  python3 fetch_market_data.py 2026-03-20 --local      # 本地模式
  python3 fetch_market_data.py 2026-03-20 --download    # 下載 JSON 到 data/
"""
import json
import os
import sys
from datetime import datetime
from urllib.request import urlopen, Request


# ── 設定 ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

API_URLS = {
    "FMTQIK": "https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK",
    "BFI82U": "https://openapi.twse.com.tw/v1/exchangeReport/BFI82U",
    "bond_yield": "https://www.tpex.org.tw/openapi/v1/tpex_bond_benchmark_yield",
}


# ── 資料讀取 ──────────────────────────────────────────
def fetch_online(url):
    """從 API 取得 JSON"""
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_local(filename):
    """從本地 data/ 目錄讀取 JSON"""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到檔案: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_data(name, local_mode=False):
    """依模式取得資料：本地或線上"""
    if local_mode:
        return load_local(f"{name}.json")
    return fetch_online(API_URLS[name])


def download_all():
    """下載所有 API 資料到 data/ 目錄"""
    os.makedirs(DATA_DIR, exist_ok=True)
    for name, url in API_URLS.items():
        path = os.path.join(DATA_DIR, f"{name}.json")
        print(f"  下載 {name} -> {path} ...", end=" ")
        try:
            data = fetch_online(url)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"OK ({len(data)} 筆)")
        except Exception as e:
            print(f"失敗: {e}")


# ── 日期轉換 ─────────────────────────────────────────
def to_roc_date(date_input):
    """西元日期 -> 民國年格式 (115/03/20)"""
    dt = datetime.strptime(date_input, "%Y-%m-%d")
    return f"{dt.year - 1911}/{dt.month:02d}/{dt.day:02d}"


# ── 格式化輸出 ────────────────────────────────────────
def format_amount(amount_str):
    """將金額字串轉為億元顯示"""
    try:
        val = int(amount_str.replace(",", ""))
        return f"{val / 1e8:,.2f} 億元"
    except (ValueError, AttributeError):
        return amount_str


def print_header(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ── 主程式 ────────────────────────────────────────────
def main():
    # 解析參數
    args = sys.argv[1:]
    target_date = "2026-03-20"
    local_mode = False
    download_mode = False

    for arg in args:
        if arg == "--local":
            local_mode = True
        elif arg == "--download":
            download_mode = True
        elif not arg.startswith("-"):
            target_date = arg

    roc_date = to_roc_date(target_date)
    mode_label = "本地檔案" if local_mode else "線上 API"

    # 下載模式
    if download_mode:
        print("下載 API 資料到 data/ 目錄...")
        download_all()
        print("\n下載完成！可用 --local 模式讀取。")
        return

    print(f"擷取日期: {target_date} (民國: {roc_date})")
    print(f"資料來源: {mode_label}")

    # ── 1. 債券資料 ──
    print_header("一、債券資料")
    try:
        bond_data = get_data("bond_yield", local_mode)
        target_5y = None
        target_10y = None
        for row in bond_data:
            date_match = row.get("日期", "") == roc_date
            tenor = row.get("天期", "")
            if date_match and tenor == "5年":
                target_5y = row
            elif date_match and tenor == "10年":
                target_10y = row

        print(f"\n  {'天期':<12} {'指標債代號':<14} {'平均殖利率':>10} {'最高':>8} {'最低':>8} {'變動(bp)':>10}")
        print(f"  {'─' * 66}")

        if target_5y:
            print(f"  {'5年期':<12} {target_5y.get('指標債券代號', 'N/A'):<14} "
                  f"{target_5y.get('平均殖利率', 'N/A'):>10}% "
                  f"{target_5y.get('最高殖利率', 'N/A'):>7}% "
                  f"{target_5y.get('最低殖利率', 'N/A'):>7}% "
                  f"{target_5y.get('變動(bp)', 'N/A'):>9}")
        else:
            print(f"  {'5年期':<12} 無資料")

        if target_10y:
            print(f"  {'10年期':<11} {target_10y.get('指標債券代號', 'N/A'):<14} "
                  f"{target_10y.get('平均殖利率', 'N/A'):>10}% "
                  f"{target_10y.get('最高殖利率', 'N/A'):>7}% "
                  f"{target_10y.get('最低殖利率', 'N/A'):>7}% "
                  f"{target_10y.get('變動(bp)', 'N/A'):>9}")
        else:
            print(f"  {'10年期':<11} 無資料")

    except Exception as e:
        print(f"  取得失敗: {e}")

    # ── 2. 股市資訊 ──
    print_header("二、股市收盤行情")
    try:
        taiex_data = get_data("FMTQIK", local_mode)
        taiex = None
        for row in taiex_data:
            if row.get("日期", "") == roc_date:
                taiex = row
                break

        if taiex:
            close_idx = taiex.get("發行量加權股價指數", "N/A")
            change = taiex.get("漲跌點數", "N/A")
            volume = format_amount(taiex.get("成交金額", "0"))
            print(f"\n  收盤指數:   {close_idx} 點")
            print(f"  漲跌點數:   {change} 點")
            print(f"  成交金額:   {volume}")
        else:
            print(f"  找不到 {roc_date} 的資料")
    except Exception as e:
        print(f"  取得失敗: {e}")

    # ── 3. 三大法人 ──
    print_header("三、三大法人買賣超金額")
    try:
        all_investors = get_data("BFI82U", local_mode)

        # 依日期篩選（若資料有日期欄位）
        if all_investors and "日期" in all_investors[0]:
            investors = [r for r in all_investors if r.get("日期", "") == roc_date]
        else:
            investors = all_investors

        if not investors:
            print(f"\n  找不到 {roc_date} 的三大法人資料")
        else:
            print(f"\n  {'法人':<28} {'買進':>16} {'賣出':>16} {'買賣超':>16}")
            print(f"  {'─' * 78}")

            for row in investors:
                name = row.get("單位名稱", "N/A")
                buy = format_amount(row.get("買進金額", "0"))
                sell = format_amount(row.get("賣出金額", "0"))
                diff = format_amount(row.get("買賣差額", "0"))
                print(f"  {name:<26} {buy:>16} {sell:>16} {diff:>16}")

    except Exception as e:
        print(f"  取得失敗: {e}")

    # ── 來源 ──
    print(f"\n{'─' * 60}")
    print("  資料來源:")
    if local_mode:
        print(f"    本地目錄: {DATA_DIR}/")
    else:
        print("    台灣證交所 OpenAPI: https://openapi.twse.com.tw/")
        print("    櫃買中心 OpenAPI:   https://www.tpex.org.tw/openapi/")
    print(f"{'─' * 60}")


if __name__ == "__main__":
    main()
