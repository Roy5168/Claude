#!/usr/bin/env python3
"""
台灣三大航空公司機票資料擷取系統 - 主程式

使用方式：
    # 方法一：使用 Amadeus API（推薦，合法且穩定）
    python -m airline_scraper.main --method api --origin TPE --dest NRT --date 2026-05-15

    # 方法二：使用網頁爬蟲（API 無法取得時的備援）
    python -m airline_scraper.main --method scrape --airline CI --origin TPE --dest NRT --date 2026-05-15

    # 方法三：同時搜尋三家航空公司（API）
    python -m airline_scraper.main --method api --origin TPE --dest NRT --date 2026-05-15 --all

    # 匯出結果
    python -m airline_scraper.main --method api --origin TPE --dest NRT --date 2026-05-15 --output json
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta

from airline_scraper.config import (
    AmadeusConfig,
    ScraperConfig,
    AIRLINE_CODES,
    AIRLINE_NAMES,
    POPULAR_ROUTES,
)
from airline_scraper.api.amadeus_client import AmadeusClient
from airline_scraper.scrapers.china_airlines import ChinaAirlinesScraper
from airline_scraper.scrapers.eva_air import EvaAirScraper
from airline_scraper.scrapers.starlux import StarluxScraper
from airline_scraper.utils.data_models import (
    SearchResult,
    save_to_json,
    save_to_csv,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


SCRAPER_MAP = {
    "CI": ChinaAirlinesScraper,
    "BR": EvaAirScraper,
    "JX": StarluxScraper,
}


async def search_via_api(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = "",
    cabin: str = "ECONOMY",
    airlines: list[str] | None = None,
) -> SearchResult:
    """透過 Amadeus API 搜尋航班"""
    config = AmadeusConfig()

    if not config.is_configured:
        logger.error(
            "Amadeus API 未設定！請設定環境變數：\n"
            "  export AMADEUS_CLIENT_ID='your_id'\n"
            "  export AMADEUS_CLIENT_SECRET='your_secret'\n"
            "註冊：https://developers.amadeus.com/"
        )
        sys.exit(1)

    airline_codes = airlines or ["CI", "BR", "JX"]

    async with AmadeusClient(config) as client:
        result = await client.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            cabin=cabin,
            airline_codes=airline_codes,
        )

    return result


async def search_via_scraper(
    airline_code: str,
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = "",
    cabin: str = "ECONOMY",
    headless: bool = True,
    proxy: str = "",
) -> SearchResult:
    """透過網頁爬蟲搜尋航班"""
    scraper_class = SCRAPER_MAP.get(airline_code)
    if not scraper_class:
        logger.error(f"不支援的航空公司代碼: {airline_code}")
        logger.info(f"支援的代碼: {list(SCRAPER_MAP.keys())}")
        sys.exit(1)

    config = ScraperConfig(headless=headless, proxy=proxy)

    async with scraper_class(config) as scraper:
        result = await scraper.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            cabin=cabin,
        )

    return result


async def search_all_scrapers(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = "",
    cabin: str = "ECONOMY",
    headless: bool = True,
) -> list[SearchResult]:
    """依序搜尋三家航空公司（避免同時啟動太多瀏覽器）"""
    results = []

    for code, scraper_class in SCRAPER_MAP.items():
        logger.info(f"\n{'='*50}")
        logger.info(f"搜尋 {AIRLINE_NAMES.get(code, code)}...")
        logger.info(f"{'='*50}")

        config = ScraperConfig(headless=headless)
        try:
            async with scraper_class(config) as scraper:
                result = await scraper.search_flights(
                    origin=origin,
                    destination=destination,
                    departure_date=departure_date,
                    return_date=return_date,
                    cabin=cabin,
                )
                results.append(result)
        except Exception as e:
            logger.error(f"[{code}] 搜尋失敗: {e}")
            results.append(SearchResult(
                query_origin=origin,
                query_destination=destination,
                query_date=departure_date,
                error=str(e),
            ))

    return results


def print_results(results: list[SearchResult]) -> None:
    """印出搜尋結果摘要"""
    print("\n" + "=" * 70)
    print("  台灣三大航空機票搜尋結果")
    print("=" * 70)

    total_offers = 0
    for result in results:
        offers = result.offers if isinstance(result, SearchResult) else result.get("offers", [])
        total_offers += len(offers)

        route = f"{result.query_origin} → {result.query_destination}"
        date = result.query_date
        print(f"\n航線: {route} | 日期: {date}")

        if result.error:
            print(f"  ⚠ 錯誤: {result.error}")
            continue

        if not offers:
            print("  沒有找到符合條件的航班")
            continue

        # 按價格排序
        if isinstance(result, SearchResult):
            result.sort_by_price()

        print(f"  找到 {len(offers)} 個航班報價：\n")
        print(f"  {'航空':<10} {'航班':<10} {'價格(TWD)':<12} {'艙等':<12} {'來源'}")
        print(f"  {'-'*60}")

        for offer in offers[:15]:  # 最多顯示 15 筆
            if isinstance(offer, dict):
                airline = offer.get("airline_code", "")
                price = offer.get("price_twd", 0)
                cabin = offer.get("cabin_class", "")
                source = offer.get("source", "")
                flight_nums = " → ".join(
                    s.get("flight_number", "")
                    for s in offer.get("segments", [])
                ) or "N/A"
            else:
                airline = offer.airline_code
                price = offer.price_twd
                cabin = offer.cabin_class
                source = offer.source
                flight_nums = " → ".join(
                    s.get("flight_number", "")
                    for s in offer.segments
                ) or "N/A"

            name = AIRLINE_NAMES.get(airline, airline)[:8]
            print(
                f"  {name:<10} {flight_nums:<10} "
                f"${price:>10,.0f} {cabin:<12} {source}"
            )

    print(f"\n共找到 {total_offers} 個航班報價")
    print("=" * 70)


def export_results(
    results: list[SearchResult],
    output_format: str,
    output_dir: str = "airline_scraper/output",
) -> None:
    """匯出結果"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_format in ("json", "both"):
        path = f"{output_dir}/flights_{timestamp}.json"
        save_to_json(results, path)
        logger.info(f"JSON 已匯出: {path}")

    if output_format in ("csv", "both"):
        path = f"{output_dir}/flights_{timestamp}.csv"
        save_to_csv(results, path)
        logger.info(f"CSV 已匯出: {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="台灣三大航空公司機票資料擷取系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  # API 搜尋（推薦）
  python -m airline_scraper.main --method api -o TPE -d NRT --date 2026-05-15

  # 網頁爬蟲搜尋（指定航空公司）
  python -m airline_scraper.main --method scrape --airline CI -o TPE -d NRT --date 2026-05-15

  # 搜尋所有航空公司並匯出
  python -m airline_scraper.main --method api -o TPE -d NRT --date 2026-05-15 --output both

  # 來回票搜尋
  python -m airline_scraper.main --method api -o TPE -d NRT --date 2026-05-15 --return-date 2026-05-22

  # 列出熱門航線
  python -m airline_scraper.main --routes
        """,
    )

    parser.add_argument(
        "--method", choices=["api", "scrape"], default="api",
        help="資料來源方式: api (Amadeus, 推薦) 或 scrape (網頁爬蟲)",
    )
    parser.add_argument(
        "-o", "--origin", default="TPE",
        help="出發機場 IATA 代碼 (預設: TPE)",
    )
    parser.add_argument(
        "-d", "--dest", default="NRT",
        help="目的地機場 IATA 代碼 (預設: NRT)",
    )
    parser.add_argument(
        "--date", default="",
        help="出發日期 YYYY-MM-DD (預設: 14天後)",
    )
    parser.add_argument(
        "--return-date", default="",
        help="回程日期 YYYY-MM-DD (選填)",
    )
    parser.add_argument(
        "--cabin", choices=["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"],
        default="ECONOMY",
        help="艙等 (預設: ECONOMY)",
    )
    parser.add_argument(
        "--airline", choices=["CI", "BR", "JX"],
        help="指定航空公司（僅 scrape 模式）",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="搜尋全部三家航空公司",
    )
    parser.add_argument(
        "--output", choices=["json", "csv", "both"],
        help="匯出格式",
    )
    parser.add_argument(
        "--no-headless", action="store_true",
        help="顯示瀏覽器視窗（除錯用）",
    )
    parser.add_argument(
        "--proxy", default="",
        help="代理伺服器 (格式: http://user:pass@host:port)",
    )
    parser.add_argument(
        "--routes", action="store_true",
        help="列出熱門航線",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="顯示詳細日誌",
    )

    return parser


async def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 列出熱門航線
    if args.routes:
        print("\n熱門航線（從台灣出發）：")
        print(f"  {'航線':<20} {'出發':<6} {'目的地'}")
        print(f"  {'-'*40}")
        for route in POPULAR_ROUTES:
            print(
                f"  {route['name']:<20} {route['origin']:<6} {route['destination']}"
            )
        return

    # 預設日期：14天後
    departure_date = args.date
    if not departure_date:
        departure_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

    print(f"\n搜尋條件：")
    print(f"  方式: {'Amadeus API' if args.method == 'api' else '網頁爬蟲'}")
    print(f"  航線: {args.origin} → {args.dest}")
    print(f"  日期: {departure_date}")
    if args.return_date:
        print(f"  回程: {args.return_date}")
    print(f"  艙等: {args.cabin}")
    print()

    results = []

    if args.method == "api":
        # API 搜尋
        result = await search_via_api(
            origin=args.origin,
            destination=args.dest,
            departure_date=departure_date,
            return_date=args.return_date,
            cabin=args.cabin,
        )
        results.append(result)

    elif args.method == "scrape":
        if args.all:
            results = await search_all_scrapers(
                origin=args.origin,
                destination=args.dest,
                departure_date=departure_date,
                return_date=args.return_date,
                cabin=args.cabin,
                headless=not args.no_headless,
            )
        else:
            airline = args.airline or "CI"
            result = await search_via_scraper(
                airline_code=airline,
                origin=args.origin,
                destination=args.dest,
                departure_date=departure_date,
                return_date=args.return_date,
                cabin=args.cabin,
                headless=not args.no_headless,
                proxy=args.proxy,
            )
            results.append(result)

    # 顯示結果
    print_results(results)

    # 匯出
    if args.output:
        export_results(results, args.output)


if __name__ == "__main__":
    asyncio.run(main())
