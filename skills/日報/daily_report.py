#!/usr/bin/env python3
"""
台灣金融市場日報
用法：
  python daily_report.py            # 最近一個交易日
  python daily_report.py 2026/3/30  # 指定日期（西元年）
依賴：pip install xlrd
"""

import sys
import os
import json
import csv
import io
import ssl
import tempfile
import urllib.request
from datetime import date, datetime, timedelta

# macOS Python 不使用系統憑證庫，需要略過 SSL 驗證（本機工具腳本使用）
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

try:
    import xlrd
except ImportError:
    print("請先安裝依賴：pip install xlrd")
    sys.exit(1)

HEADERS = {'User-Agent': 'Mozilla/5.0'}


# ── 日期工具 ──────────────────────────────────────────────

def prev_weekday(d: date) -> date:
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def resolve_target_date(arg=None):
    if arg:
        target = datetime.strptime(arg.strip().replace('-', '/'), "%Y/%m/%d").date()
    else:
        now = datetime.now()
        today = now.date()
        wd = today.weekday()
        if wd == 5:
            target = today - timedelta(days=1)
        elif wd == 6:
            target = today - timedelta(days=2)
        elif now.hour < 15:
            target = prev_weekday(today)
        else:
            target = today
    return target, prev_weekday(target)


# ── HTTP 工具 ─────────────────────────────────────────────

def fetch_bytes(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20, context=SSL_CTX) as r:
        return r.read()


def fetch_json(url):
    return json.loads(fetch_bytes(url))


def download_xls(url, path):
    try:
        data = fetch_bytes(url)
        with open(path, 'wb') as f:
            f.write(data)
        return True
    except Exception:
        return False


# ── Step 2：台債指標債殖利率 ──────────────────────────────

def fetch_bond_yield(d):
    yyyymmdd = d.strftime("%Y%m%d")
    url = (f"https://www.tpex.org.tw/storage/bond_zone/tradeinfo/govbond"
           f"/{d.year}/{d.strftime('%Y%m')}/BDdys100.{yyyymmdd}-C.xls")
    path = os.path.join(tempfile.gettempdir(), f"bond_{yyyymmdd}.xls")
    if not download_xls(url, path):
        return None
    try:
        wb = xlrd.open_workbook(path)
        ws = wb.sheet_by_index(0)
        results = []
        for r in [5, 6]:
            results.append({
                'tenor':     int(ws.cell_value(r, 0)),
                'code':      ws.cell_value(r, 1),
                'yield':     ws.cell_value(r, 2),
                'change_bp': ws.cell_value(r, 4),
            })
        return results
    except Exception:
        return None


# ── Step 3：台股加權指數 + 成交量 ────────────────────────

def fetch_taiex(d):
    yyyymmdd = d.strftime("%Y%m%d")
    # 加權指數
    try:
        data = fetch_json(
            f"https://www.twse.com.tw/exchangeReport/MI_INDEX"
            f"?response=json&date={yyyymmdd}&type=IND"
        )
        index_row = None
        for row in data.get('tables', [{}])[0].get('data', []):
            if '發行量加權' in row[0]:
                index_row = row
                break
    except Exception:
        index_row = None

    # 成交量
    roc = f"{d.year - 1911}/{d.month:02d}/{d.day:02d}"
    vol = None
    try:
        vdata = fetch_json(
            f"https://www.twse.com.tw/exchangeReport/FMTQIK"
            f"?response=json&date={yyyymmdd}"
        )
        for row in vdata.get('data', []):
            if row[0] == roc:
                vol = int(row[2].replace(',', ''))
                break
    except Exception:
        pass

    if not index_row:
        return None
    return {
        'close': index_row[1],
        'sign':  '-' if '-' in index_row[2] else '+',
        'pts':   index_row[3],
        'pct':   index_row[4],
        'vol':   vol,
    }


# ── Step 4：三大法人買賣超 ───────────────────────────────

def fetch_inst(d):
    yyyymmdd = d.strftime("%Y%m%d")
    try:
        data = fetch_json(
            f"https://www.twse.com.tw/fund/BFI82U"
            f"?response=json&dayDate={yyyymmdd}&type=day"
        )
        rows = data.get('data', [])
        if not rows:
            return None
        result = {}
        for row in rows:
            val = int(row[3].replace(',', '').replace('+', '')) / 1e8
            result[row[0]] = val
        result['自營商合計'] = (result.get('自營商(自行買賣)', 0)
                               + result.get('自營商(避險)', 0))
        return result
    except Exception:
        return None


# ── Step 5：金融業隔夜拆款利率 ───────────────────────────

def fetch_cbc_rate(target, prev):
    try:
        raw = fetch_bytes("https://www.cbc.gov.tw/public/data/OpenData/WebF2.csv")
        text = raw.decode('big5', errors='replace')
        rates = {}
        for line in text.splitlines():
            parts = line.strip().split(',')
            if len(parts) >= 2:
                try:
                    rates[parts[0].strip()] = float(parts[1].strip())
                except ValueError:
                    pass
        fmt = lambda d: f"{d.year}/{d.month}/{d.day}"
        return rates.get(fmt(target)), rates.get(fmt(prev))
    except Exception:
        return None, None


# ── Step 6：2-10天期附買回利率 ───────────────────────────

def fetch_repo(d):
    yyyymmdd = d.strftime("%Y%m%d")
    url = (f"https://www.tpex.org.tw/storage/bond_zone/tradeinfo/govbond"
           f"/{d.year}/{d.strftime('%Y%m')}/BDdcs001.{yyyymmdd}-C.xls")
    path = os.path.join(tempfile.gettempdir(), f"repo_{yyyymmdd}.xls")
    if not download_xls(url, path):
        return None, None
    try:
        wb = xlrd.open_workbook(path)
        ws = wb.sheet_by_name('BDdcs01b')
        # 搜尋 TWD 列
        twd_row = None
        for r in range(ws.nrows):
            if ws.cell_value(r, 0) == 'TWD':
                twd_row = r
                break
        if twd_row is None:
            return None, None
        # 在原始附買回區塊中找 2-10 天期
        for r in range(twd_row, ws.nrows):
            if ws.cell_value(r, 4) == '2-10':
                is_repo = False
                for rr in range(r, twd_row - 1, -1):
                    v = str(ws.cell_value(rr, 1))
                    if '原始附買回' in v:
                        is_repo = True
                        break
                    elif '原始附賣回' in v:
                        break
                if is_repo:
                    return ws.cell_value(r, 7), ws.cell_value(r, 8)
        return None, None
    except Exception:
        return None, None


# ── 輸出 ─────────────────────────────────────────────────

def sgn(v, unit='', decimals=2):
    return f"{v:+.{decimals}f}{unit}"


def print_report(target, prev,
                 bond_t, taiex_t, taiex_p,
                 inst_t, inst_p,
                 cbc_t, cbc_p,
                 repo_t_rate, repo_t_amt,
                 repo_p_rate, repo_p_amt):

    print(f"\n## 台灣金融市場日報（{target.strftime('%Y/%m/%d')}）\n")

    # 台債
    print("### 台債指標債殖利率\n")
    print("| 到期年限 | 指標券 | 殖利率(%) | 漲跌(bp) |")
    print("|:--------:|:------:|:---------:|:--------:|")
    if bond_t:
        for b in bond_t:
            chg = b['change_bp']
            chg_str = f"{chg:+.2f}" if chg != 0 else '0.00'
            print(f"| {b['tenor']}年期 | {b['code']} | {b['yield']:.4f} | {chg_str} |")
    else:
        print("| 無資料 | - | - | - |")

    # 加權指數
    print("\n### 台股加權指數\n")
    print("| 指數 | 收盤 | 漲跌點數 | 漲跌幅(%) | 當日成交量(億元) | 前日成交量(億元) | 變動(億元) |")
    print("|:----:|-----:|:--------:|:---------:|----------------:|----------------:|-----------:|")
    if taiex_t:
        t_vol = taiex_t['vol'] / 1e8 if taiex_t.get('vol') else None
        p_vol = taiex_p['vol'] / 1e8 if taiex_p and taiex_p.get('vol') else None
        t_vol_s = f"{t_vol:,.2f}" if t_vol else '-'
        p_vol_s = f"{p_vol:,.2f}" if p_vol else '-'
        vol_chg = f"{t_vol - p_vol:+.2f}" if t_vol and p_vol else '-'
        print(f"| 加權指數 | {taiex_t['close']} | {taiex_t['sign']}{taiex_t['pts']} "
              f"| {taiex_t['pct']} | {t_vol_s} | {p_vol_s} | {vol_chg} |")
    else:
        print("| 無資料 | - | - | - | - | - | - |")

    # 三大法人
    td = target.strftime('%m/%d')
    pd = prev.strftime('%m/%d')
    print(f"\n### 三大法人買賣超（億元）\n")
    print(f"| 法人 | 當日({td}) | 前日({pd}) | 變動 |")
    print("|:----:|-----------:|-----------:|-----:|")
    if inst_t and inst_p:
        items = [
            ('外資',   '外資及陸資(不含外資自營商)'),
            ('投信',   '投信'),
            ('自營商', '自營商合計'),
        ]
        for label, key in items:
            t = inst_t.get(key, 0)
            p = inst_p.get(key, 0)
            print(f"| {label} | {t:+.2f} | {p:+.2f} | {t-p:+.2f} |")
        tt = inst_t.get('合計', 0)
        pp = inst_p.get('合計', 0)
        print(f"| **合計** | **{tt:+.2f}** | **{pp:+.2f}** | **{tt-pp:+.2f}** |")
    else:
        print("| 無資料 | - | - | - |")

    # 隔夜拆款
    print("\n### 金融業隔夜拆款利率\n")
    print("| 項目 | 當日(%) | 前日(%) | 變動(bp) |")
    print("|:----:|:-------:|:-------:|:--------:|")
    if cbc_t and cbc_p:
        diff = (cbc_t - cbc_p) * 100
        print(f"| 加權平均 | {cbc_t:.3f} | {cbc_p:.3f} | {diff:+.2f} |")
    elif cbc_t:
        print(f"| 加權平均 | {cbc_t:.3f} | N/A（CSV延遲）| - |")
    else:
        print("| 無資料（CSV更新延遲） | - | - | - |")

    # RP 利率
    print(f"\n### 2-10天期附買回利率\n")
    print(f"| 項目 | 當日({td}) | 前日({pd}) | 變動 |")
    print("|:----:|-----------:|-----------:|-----:|")
    if repo_t_rate and repo_p_rate:
        rate_chg = (repo_t_rate - repo_p_rate) * 100
        amt_t = repo_t_amt / 1e8
        amt_p = repo_p_amt / 1e8
        print(f"| 加權平均利率(%) | {repo_t_rate:.4f} | {repo_p_rate:.4f} | {rate_chg:+.2f}bp |")
        print(f"| 成交金額（億元） | {amt_t:.2f} | {amt_p:.2f} | {amt_t-amt_p:+.2f} |")
    else:
        print("| 無資料 | - | - | - |")
    print()


# ── 主程式 ───────────────────────────────────────────────

def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    target, prev = resolve_target_date(arg)

    print(f"目標日期：{target.strftime('%Y/%m/%d')}　前一交易日：{prev.strftime('%Y/%m/%d')}")
    print("擷取資料中...", end='', flush=True)

    bond_t     = fetch_bond_yield(target)
    taiex_t    = fetch_taiex(target)
    taiex_p    = fetch_taiex(prev)
    inst_t     = fetch_inst(target)
    inst_p     = fetch_inst(prev)
    cbc_t, cbc_p = fetch_cbc_rate(target, prev)
    repo_t_rate, repo_t_amt = fetch_repo(target)
    repo_p_rate, repo_p_amt = fetch_repo(prev)

    print(" 完成")

    print_report(
        target, prev,
        bond_t, taiex_t, taiex_p,
        inst_t, inst_p,
        cbc_t, cbc_p,
        repo_t_rate, repo_t_amt,
        repo_p_rate, repo_p_amt,
    )


if __name__ == '__main__':
    main()
