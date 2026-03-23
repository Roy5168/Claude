"""
台灣市場資料擷取工具
從台灣證交所 (TWSE) OpenAPI 與櫃買中心 (TPEX) OpenAPI 擷取指定日期的市場資料
"""
import json
import sys
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError


def fetch_json(url):
    """取得 JSON 資料"""
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_taiex_daily(date_str):
    """從 TWSE OpenAPI 取得加權指數每日行情 (當月資料)"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK"
    data = fetch_json(url)
    # 回傳當月每日行情，篩選指定日期
    for row in data:
        if row.get("日期", "") == date_str:
            return row
    return None


def fetch_institutional_investors():
    """從 TWSE OpenAPI 取得三大法人買賣超 (當日資料)"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/BFI82U"
    return fetch_json(url)


def fetch_taiex_index():
    """從 TWSE OpenAPI 取得大盤指數"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX"
    return fetch_json(url)


def fetch_bond_yield():
    """從 TPEX OpenAPI 取得公債殖利率資料"""
    # 嘗試多個可能的 TPEX 端點
    endpoints = [
        "https://www.tpex.org.tw/openapi/v1/tpex_bond_benchmark_yield",
        "https://www.tpex.org.tw/openapi/v1/tpex_bond_government_yield",
    ]
    for url in endpoints:
        try:
            return fetch_json(url)
        except Exception:
            continue
    return None


def fetch_tpex_swagger():
    """取得 TPEX 所有可用 API 端點"""
    url = "https://www.tpex.org.tw/openapi/swagger.json"
    data = fetch_json(url)
    paths = data.get("paths", {})
    bond_paths = {k: v for k, v in paths.items() if "bond" in k.lower() or "債" in str(v)}
    return paths, bond_paths


def format_date_for_twse(date_input):
    """將日期轉換為 TWSE 使用的民國年格式 (例: 115/03/20)"""
    dt = datetime.strptime(date_input, "%Y-%m-%d")
    roc_year = dt.year - 1911
    return f"{roc_year}/{dt.month:02d}/{dt.day:02d}"


def main():
    # 預設日期
    target_date = sys.argv[1] if len(sys.argv) > 1 else "2026-03-20"
    roc_date = format_date_for_twse(target_date)
    print(f"擷取日期: {target_date} (民國: {roc_date})")
    print("=" * 60)

    # 1. 取得加權指數每日行情
    print("\n【一、台股收盤行情】")
    try:
        taiex = fetch_taiex_daily(roc_date)
        if taiex:
            print(f"  日期:       {taiex.get('日期', 'N/A')}")
            print(f"  開盤指數:   {taiex.get('開盤指數', 'N/A')}")
            print(f"  最高指數:   {taiex.get('最高指數', 'N/A')}")
            print(f"  最低指數:   {taiex.get('最低指數', 'N/A')}")
            print(f"  收盤指數:   {taiex.get('收盤指數', 'N/A')}")
            print(f"  漲跌點數:   {taiex.get('漲跌點數', 'N/A')}")
            print(f"  成交金額:   {taiex.get('成交金額', 'N/A')}")
        else:
            print(f"  找不到 {roc_date} 的資料 (API 僅提供當月資料)")
    except Exception as e:
        print(f"  取得失敗: {e}")

    # 2. 取得三大法人買賣超
    print("\n【二、三大法人買賣超】")
    try:
        investors = fetch_institutional_investors()
        if investors:
            for row in investors:
                name = row.get("單位名稱", "N/A")
                buy = row.get("買進金額", "N/A")
                sell = row.get("賣出金額", "N/A")
                diff = row.get("買賣差額", "N/A")
                print(f"  {name}: 買進 {buy}, 賣出 {sell}, 買賣差額 {diff}")
    except Exception as e:
        print(f"  取得失敗: {e}")

    # 3. 取得公債殖利率
    print("\n【三、公債殖利率】")
    try:
        # 先列出 TPEX 有哪些 bond 相關的 API
        paths, bond_paths = fetch_tpex_swagger()
        if bond_paths:
            print("  TPEX 債券相關 API 端點:")
            for path in sorted(bond_paths.keys()):
                print(f"    https://www.tpex.org.tw/openapi{path}")
        else:
            print("  搜尋所有含 'bond' 的 API 端點:")
            for path in sorted(paths.keys()):
                if "bond" in path.lower():
                    print(f"    https://www.tpex.org.tw/openapi{path}")
    except Exception as e:
        print(f"  取得 TPEX swagger 失敗: {e}")

    try:
        bond_data = fetch_bond_yield()
        if bond_data:
            print("\n  公債殖利率資料:")
            for row in bond_data[:10]:
                print(f"    {json.dumps(row, ensure_ascii=False)}")
    except Exception as e:
        print(f"  取得殖利率資料失敗: {e}")

    print("\n" + "=" * 60)
    print("資料來源:")
    print("  台灣證交所 OpenAPI: https://openapi.twse.com.tw/")
    print("  櫃買中心 OpenAPI:   https://www.tpex.org.tw/openapi/")


if __name__ == "__main__":
    main()
