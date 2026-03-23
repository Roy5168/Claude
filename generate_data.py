#!/usr/bin/env python3
"""Generate realistic market data from 2026/1/2 to 2026/3/18 for local testing."""

import json
import random
import datetime
import os

random.seed(42)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Taiwan holidays in 2026 (non-trading days besides weekends)
TW_HOLIDAYS_2026 = {
    datetime.date(2026, 1, 1),   # 元旦
    datetime.date(2026, 2, 14),  # 除夕前調整放假
    datetime.date(2026, 2, 16),  # 除夕
    datetime.date(2026, 2, 17),  # 春節初一
    datetime.date(2026, 2, 18),  # 春節初二
    datetime.date(2026, 2, 19),  # 春節初三
    datetime.date(2026, 2, 20),  # 春節初四
    datetime.date(2026, 2, 28),  # 和平紀念日 (Saturday, observed Friday 2/27)
    datetime.date(2026, 2, 27),  # 228補假
}

def is_trading_day(d):
    if d.weekday() >= 5:  # Saturday/Sunday
        return False
    if d in TW_HOLIDAYS_2026:
        return False
    return True

def to_roc(d):
    return f"{d.year - 1911}/{d.month:02d}/{d.day:02d}"

def fmt_amount(val):
    """Format an integer amount with commas."""
    neg = val < 0
    s = f"{abs(val):,}"
    return f"-{s}" if neg else s

def generate_trading_days(start, end):
    days = []
    d = start
    while d <= end:
        if is_trading_day(d):
            days.append(d)
        d += datetime.timedelta(days=1)
    return days

def generate_taiex(trading_days):
    """Generate TAIEX closing data."""
    records = []
    index = 22800.0  # Starting index around early Jan 2026

    for d in trading_days:
        change = random.gauss(15, 180)  # slight upward bias, ~180pt std dev
        index += change
        index = max(index, 18000)  # floor

        volume_shares = random.randint(4_000_000_000, 9_000_000_000)
        volume_amount = random.randint(200_000_000_000, 500_000_000_000)
        transactions = random.randint(1_500_000, 4_000_000)

        records.append({
            "日期": to_roc(d),
            "成交股數": fmt_amount(volume_shares),
            "成交金額": fmt_amount(volume_amount),
            "成交筆數": fmt_amount(transactions),
            "發行量加權股價指數": f"{index:,.2f}",
            "漲跌點數": f"{change:+.2f}" if change >= 0 else f"{change:.2f}",
        })
    return records, index

def generate_bonds(trading_days):
    """Generate bond yield data for 5Y, 10Y, 20Y, 30Y."""
    records = []

    tenors = [
        {"天期": "5年",  "代號": "A10509", "base": 1.150},
        {"天期": "10年", "代號": "A11003", "base": 1.380},
        {"天期": "20年", "代號": "A11203", "base": 1.750},
        {"天期": "30年", "代號": "A11305", "base": 1.980},
    ]

    current = {t["天期"]: t["base"] for t in tenors}

    for d in trading_days:
        for t in tenors:
            bp_change = random.gauss(0, 1.5)  # basis point change
            bp_change = round(bp_change * 2) / 2  # round to 0.5bp
            current[t["天期"]] += bp_change / 100
            current[t["天期"]] = max(current[t["天期"]], 0.5)

            avg = round(current[t["天期"]], 3)
            spread = round(random.uniform(0.003, 0.008), 3)
            high = round(avg + spread / 2, 3)
            low = round(avg - spread / 2, 3)

            records.append({
                "日期": to_roc(d),
                "債券種類": "公債",
                "天期": t["天期"],
                "指標債券代號": t["代號"],
                "平均殖利率": f"{avg:.3f}",
                "最高殖利率": f"{high:.3f}",
                "最低殖利率": f"{low:.3f}",
                "變動(bp)": str(bp_change),
            })
    return records

def generate_investors(trading_days):
    """Generate institutional investor buy/sell data."""
    records = []

    for d in trading_days:
        # Generate each institution's data
        institutions = []

        # 自營商(自行買賣)
        buy = random.randint(10_000_000_000, 25_000_000_000)
        sell = random.randint(10_000_000_000, 25_000_000_000)
        institutions.append(("自營商(自行買賣)", buy, sell))

        # 自營商(避險)
        buy = random.randint(15_000_000_000, 40_000_000_000)
        sell = random.randint(15_000_000_000, 40_000_000_000)
        institutions.append(("自營商(避險)", buy, sell))

        # 投信
        buy = random.randint(5_000_000_000, 50_000_000_000)
        sell = random.randint(5_000_000_000, 50_000_000_000)
        institutions.append(("投信", buy, sell))

        # 外資及陸資(不含外資自營商)
        buy = random.randint(100_000_000_000, 350_000_000_000)
        sell = random.randint(100_000_000_000, 350_000_000_000)
        institutions.append(("外資及陸資(不含外資自營商)", buy, sell))

        # 外資自營商
        buy = random.randint(500_000_000, 3_000_000_000)
        sell = random.randint(500_000_000, 3_000_000_000)
        institutions.append(("外資自營商", buy, sell))

        total_buy = sum(b for _, b, _ in institutions)
        total_sell = sum(s for _, _, s in institutions)
        institutions.append(("合計", total_buy, total_sell))

        for name, b, s in institutions:
            records.append({
                "日期": to_roc(d),
                "單位名稱": name,
                "買進金額": fmt_amount(b),
                "賣出金額": fmt_amount(s),
                "買賣差額": fmt_amount(b - s),
            })
    return records

def main():
    start = datetime.date(2026, 1, 2)
    end = datetime.date(2026, 3, 18)

    trading_days = generate_trading_days(start, end)
    print(f"Generated {len(trading_days)} trading days from {start} to {end}")

    # Generate new data
    taiex_new, last_index = generate_taiex(trading_days)
    bonds_new = generate_bonds(trading_days)
    investors_new = generate_investors(trading_days)

    print(f"  TAIEX: {len(taiex_new)} records, final index: {last_index:,.2f}")
    print(f"  Bonds: {len(bonds_new)} records")
    print(f"  Investors: {len(investors_new)} records")

    # Load existing data (3/19 and 3/20)
    def load(fn):
        path = os.path.join(DATA_DIR, fn)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    existing_taiex = load("FMTQIK.json")
    existing_bonds = load("bond_yield.json")
    existing_investors = load("BFI82U.json")

    # Filter out dates that overlap with new data
    new_dates = {to_roc(d) for d in trading_days}
    existing_taiex = [r for r in existing_taiex if r["日期"] not in new_dates]
    existing_bonds = [r for r in existing_bonds if r["日期"] not in new_dates]
    existing_investors = [r for r in existing_investors if r["日期"] not in new_dates]

    # Merge: new data first (earlier dates), then existing (later dates)
    all_taiex = taiex_new + existing_taiex
    all_bonds = bonds_new + existing_bonds
    all_investors = investors_new + existing_investors

    # Sort by date
    all_taiex.sort(key=lambda r: r["日期"])
    all_bonds.sort(key=lambda r: (r["日期"], r["天期"]))
    all_investors.sort(key=lambda r: r["日期"])

    # Write back
    def save(fn, data):
        path = os.path.join(DATA_DIR, fn)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  Wrote {len(data)} records to {fn}")

    save("FMTQIK.json", all_taiex)
    save("bond_yield.json", all_bonds)
    save("BFI82U.json", all_investors)

    print("\nDone!")

if __name__ == "__main__":
    main()
