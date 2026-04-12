"""
星宇航空 (Starlux Airlines, JX) 網頁爬蟲

技術特徵：
- 現代化 SPA 架構，前端 API 驅動
- 較新的航空公司，網站架構相對現代化
- 策略：API 攔截為主要方式
"""

import asyncio
import logging
import time
from typing import Optional

from airline_scraper.scrapers.base_scraper import BaseAirlineScraper
from airline_scraper.utils.anti_detect import random_delay, human_like_typing
from airline_scraper.utils.data_models import (
    FlightOffer,
    FlightSegment,
    SearchResult,
)

logger = logging.getLogger(__name__)


class StarluxScraper(BaseAirlineScraper):
    """星宇航空官網爬蟲"""

    AIRLINE_CODE = "JX"
    AIRLINE_NAME = "星宇航空 Starlux Airlines"
    BASE_URL = "https://www.starlux-airlines.com"
    SEARCH_URL = "https://www.starlux-airlines.com/zh-TW"

    async def search_flights(
        self,
        origin: str = "TPE",
        destination: str = "NRT",
        departure_date: str = "",
        return_date: str = "",
        cabin: str = "ECONOMY",
        passengers: int = 1,
    ) -> SearchResult:
        """搜尋星宇航空航班"""
        start_time = time.time()
        self._intercepted_apis.clear()

        try:
            await self.throttler.throttle()
            await self.rotate_session_if_needed()

            logger.info(
                f"[JX] 搜尋航班: {origin} → {destination}, "
                f"日期: {departure_date}"
            )

            # 1. 前往首頁
            await self._page.goto(
                self.SEARCH_URL,
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await random_delay(2, 4)

            # 2. 處理彈窗
            await self._handle_popups()

            # 3. 填寫搜尋表單
            await self._fill_search_form(
                origin, destination, departure_date, return_date, cabin, passengers
            )

            # 4. 送出搜尋
            await self._submit_search()

            # 5. 等待結果
            await self._wait_for_results(timeout=20)

            # 6. 解析結果
            offers = self._parse_results(self._intercepted_apis)

            if not offers:
                offers = await self._parse_from_dom()

            duration = time.time() - start_time
            return SearchResult(
                query_origin=origin,
                query_destination=destination,
                query_date=departure_date,
                query_return_date=return_date,
                query_cabin=cabin,
                query_passengers=passengers,
                offers=offers,
                search_duration_sec=duration,
            )

        except Exception as e:
            logger.error(f"[JX] 搜尋失敗: {e}")
            return SearchResult(
                query_origin=origin,
                query_destination=destination,
                query_date=departure_date,
                query_return_date=return_date,
                error=str(e),
                search_duration_sec=time.time() - start_time,
            )

    async def _handle_popups(self) -> None:
        """處理彈窗"""
        try:
            selectors = [
                "button:has-text('接受')",
                "button:has-text('同意')",
                "button:has-text('我知道了')",
                "button:has-text('Accept')",
                "button:has-text('Got it')",
                "[class*='cookie'] button",
                ".modal-close",
            ]
            for sel in selectors:
                btn = self._page.locator(sel)
                if await btn.count() > 0:
                    await btn.first.click()
                    await random_delay(0.5, 1)
                    break
        except Exception:
            pass

    async def _fill_search_form(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        cabin: str,
        passengers: int,
    ) -> None:
        """填寫星宇航空搜尋表單"""
        page = self._page

        # 行程類型
        if not return_date:
            try:
                oneway = page.locator(
                    "label:has-text('單程'), [data-value='oneway'], "
                    "input[value='oneway']"
                )
                if await oneway.count() > 0:
                    await oneway.first.click()
                    await random_delay(0.5, 1)
            except Exception:
                pass

        # 出發地
        await self._fill_airport_field("origin", origin)
        await random_delay(1, 2)

        # 目的地
        await self._fill_airport_field("destination", destination)
        await random_delay(1, 2)

        # 日期
        await self._select_date(departure_date)
        if return_date:
            await self._select_date(return_date)

    async def _fill_airport_field(self, field_type: str, code: str) -> None:
        """填寫機場欄位"""
        selectors = [
            f"input[name*='{field_type}']",
            f"[data-testid='{field_type}']",
            f"input[placeholder*='{'出發' if field_type == 'origin' else '目的'}']",
            f"#{field_type}-airport",
        ]

        for selector in selectors:
            try:
                el = self._page.locator(selector)
                if await el.count() > 0:
                    await el.first.click()
                    await random_delay(0.3, 0.6)
                    await el.first.fill("")
                    await human_like_typing(self._page, selector, code)
                    await random_delay(1, 2)

                    # 選擇下拉建議
                    suggestion = self._page.locator(
                        f"li:has-text('{code}'), "
                        f"[class*='option']:has-text('{code}'), "
                        f"[class*='suggestion']:has-text('{code}'), "
                        f"[class*='dropdown'] *:has-text('{code}')"
                    )
                    if await suggestion.count() > 0:
                        await suggestion.first.click()
                    else:
                        await self._page.keyboard.press("Enter")
                    return
            except Exception:
                continue

    async def _select_date(self, date_str: str) -> None:
        """選擇日期"""
        try:
            year, month, day = date_str.split("-")
            day_int = str(int(day))

            # 嘗試點擊日曆中的日期
            date_selectors = [
                f"[data-date='{date_str}']",
                f"td[data-day='{day_int}']",
                f".calendar-day[data-value='{date_str}']",
                f"button[aria-label*='{date_str}']",
            ]

            for sel in date_selectors:
                el = self._page.locator(sel)
                if await el.count() > 0:
                    await el.first.click()
                    await random_delay(0.5, 1)
                    return
        except Exception as e:
            logger.debug(f"[JX] 日期選擇: {e}")

    async def _submit_search(self) -> None:
        """送出搜尋"""
        selectors = [
            "button:has-text('搜尋航班')",
            "button:has-text('搜尋')",
            "button:has-text('Search')",
            "button[type='submit']",
            "[data-testid='search-submit']",
            ".search-btn",
        ]

        for selector in selectors:
            try:
                btn = self._page.locator(selector)
                if await btn.count() > 0:
                    await btn.first.click()
                    logger.info("[JX] 搜尋已送出")
                    return
            except Exception:
                continue

        await self._page.keyboard.press("Enter")

    async def _wait_for_results(self, timeout: int = 20) -> None:
        """等待結果"""
        logger.info("[JX] 等待搜尋結果...")
        for _ in range(timeout):
            await asyncio.sleep(1)
            if self._intercepted_apis:
                return
            try:
                for ind in [
                    "[class*='flight']",
                    "[class*='result']",
                    "[class*='fare']",
                    "[class*='itinerary']",
                ]:
                    if await self._page.locator(ind).count() > 0:
                        await random_delay(2, 3)
                        return
            except Exception:
                pass

    async def _parse_from_dom(self) -> list[FlightOffer]:
        """DOM 解析備援"""
        offers = []
        try:
            cards = self._page.locator(
                "[class*='flight-card'], [class*='result-item'], "
                "[class*='fare-card']"
            )
            count = await cards.count()

            for i in range(min(count, 20)):
                try:
                    card = cards.nth(i)
                    text = await card.inner_text()
                    offer = FlightOffer(
                        source="website_jx_dom",
                        airline_code="JX",
                        airline_name=self.AIRLINE_NAME,
                        origin="",
                        destination="",
                        departure_date="",
                        price_twd=0,
                    )
                    offers.append(offer)
                except Exception:
                    continue
        except Exception:
            pass

        return offers

    def _parse_results(self, intercepted: list[dict]) -> list[FlightOffer]:
        """解析攔截的 API 回應"""
        offers = []

        for api_data in intercepted:
            data = api_data.get("data", {})

            flights = (
                data.get("flights", [])
                or data.get("flightOffers", [])
                or data.get("data", {}).get("flights", [])
                or data.get("results", [])
            )

            if not flights and isinstance(data, list):
                flights = data

            for flight in flights:
                try:
                    offer = self._parse_single_flight(flight)
                    if offer:
                        offers.append(offer)
                except Exception as e:
                    logger.debug(f"[JX] 解析航班: {e}")

        if not offers and intercepted:
            logger.info(f"[JX] 攔截到 {len(intercepted)} 個 API 回應但未成功解析")
            for api in intercepted:
                logger.info(f"  - URL: {api.get('url', 'unknown')}")

        return offers

    def _parse_single_flight(self, flight: dict) -> Optional[FlightOffer]:
        """解析單一航班"""
        if not isinstance(flight, dict):
            return None

        price = (
            flight.get("price", {}).get("total")
            or flight.get("totalPrice")
            or flight.get("fare", {}).get("amount")
            or 0
        )

        segments_raw = (
            flight.get("segments", [])
            or flight.get("legs", [])
            or flight.get("itinerary", [])
        )

        segments = []
        for seg in segments_raw:
            if isinstance(seg, dict):
                segment = FlightSegment(
                    airline_code="JX",
                    flight_number=seg.get("flightNumber", ""),
                    departure_airport=seg.get("origin", seg.get("from", "")),
                    arrival_airport=seg.get("destination", seg.get("to", "")),
                    departure_time=seg.get("departureTime", ""),
                    arrival_time=seg.get("arrivalTime", ""),
                    duration=seg.get("duration", ""),
                    aircraft=seg.get("aircraft", ""),
                )
                segments.append(segment)

        return FlightOffer(
            source="website_jx",
            airline_code="JX",
            airline_name=self.AIRLINE_NAME,
            origin=segments[0].departure_airport if segments else "",
            destination=segments[-1].arrival_airport if segments else "",
            departure_date=segments[0].departure_time[:10] if segments else "",
            price_twd=float(price) if price else 0,
            price_currency="TWD",
            cabin_class=flight.get("cabin", "ECONOMY"),
            segments=[vars(s) for s in segments],
        )
