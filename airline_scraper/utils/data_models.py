"""
資料模型 - 統一的航班資料結構
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, date
from typing import Optional
import json
import csv
import os


@dataclass
class FlightSegment:
    """航班段落資訊"""
    airline_code: str          # 航空公司代碼 (CI/BR/JX)
    flight_number: str         # 航班號碼
    departure_airport: str     # 出發機場 IATA 代碼
    arrival_airport: str       # 到達機場 IATA 代碼
    departure_time: str        # 出發時間 ISO 格式
    arrival_time: str          # 到達時間 ISO 格式
    duration: str              # 飛行時間 (如 "3h 25m")
    aircraft: str = ""         # 機型
    cabin_class: str = ""      # 艙等 (ECONOMY/BUSINESS/FIRST)
    stops: int = 0             # 轉機次數


@dataclass
class FlightOffer:
    """機票報價資訊"""
    source: str                     # 資料來源 (amadeus/website)
    airline_code: str               # 航空公司代碼
    airline_name: str               # 航空公司名稱
    origin: str                     # 出發地 IATA
    destination: str                # 目的地 IATA
    departure_date: str             # 出發日期
    return_date: str = ""           # 回程日期（單程則留空）
    price_twd: float = 0.0         # 票價（新台幣）
    price_currency: str = "TWD"     # 幣別
    price_original: float = 0.0    # 原始幣別票價
    currency_original: str = ""     # 原始幣別
    trip_type: str = "one_way"      # one_way / round_trip
    cabin_class: str = "ECONOMY"    # 艙等
    segments: list = field(default_factory=list)  # FlightSegment 列表
    booking_class: str = ""         # 訂位艙等代碼
    seats_available: int = 0        # 剩餘座位
    refundable: bool = False        # 是否可退票
    baggage_info: str = ""          # 行李資訊
    scraped_at: str = ""            # 擷取時間

    def __post_init__(self):
        if not self.scraped_at:
            self.scraped_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        data = asdict(self)
        return data


@dataclass
class SearchResult:
    """搜尋結果集合"""
    query_origin: str
    query_destination: str
    query_date: str
    query_return_date: str = ""
    query_cabin: str = "ECONOMY"
    query_passengers: int = 1
    offers: list = field(default_factory=list)  # FlightOffer 列表
    searched_at: str = ""
    search_duration_sec: float = 0.0
    error: str = ""

    def __post_init__(self):
        if not self.searched_at:
            self.searched_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    def sort_by_price(self, ascending: bool = True) -> None:
        self.offers.sort(
            key=lambda o: o.price_twd if isinstance(o, FlightOffer) else o.get("price_twd", 0),
            reverse=not ascending,
        )


def save_to_json(results: list[SearchResult], filepath: str) -> None:
    """將搜尋結果儲存為 JSON"""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    data = [r.to_dict() if isinstance(r, SearchResult) else r for r in results]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_to_csv(results: list[SearchResult], filepath: str) -> None:
    """將搜尋結果儲存為 CSV（扁平化）"""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    rows = []
    for result in results:
        offers = result.offers if isinstance(result, SearchResult) else result.get("offers", [])
        for offer in offers:
            row = offer.to_dict() if isinstance(offer, FlightOffer) else offer
            # 扁平化 segments
            segments_str = ""
            if row.get("segments"):
                segments_str = " → ".join(
                    f"{s.get('flight_number', '')} {s.get('departure_airport', '')}-{s.get('arrival_airport', '')}"
                    for s in row["segments"]
                )
            flat = {k: v for k, v in row.items() if k != "segments"}
            flat["segments_summary"] = segments_str
            flat["search_date"] = (
                result.query_date if isinstance(result, SearchResult)
                else result.get("query_date", "")
            )
            rows.append(flat)

    if not rows:
        return

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
