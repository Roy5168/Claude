"""
長榮航空 (EVA Air, BR) 網頁爬蟲

技術特徵：
- 官網基於 Windows Server / IIS
- 使用 Cloudflare Rocket Loader
- 部分功能需要登入（2FA）
- 策略：API 攔截為主，頁面解析為輔
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


class EvaAirScraper(BaseAirlineScraper):
    """長榮航空官網爬蟲"""

    AIRLINE_CODE = "BR"
    AIRLINE_NAME = "長榮航空 EVA Air"
    BASE_URL = "https://www.evaair.com"
    SEARCH_URL = "https://www.evaair.com/zh-tw/index.html"

    async def search_flights(
        self,
        origin: str = "TPE",
        destination: str = "NRT",
        departure_date: str = "",
        return_date: str = "",
        cabin: str = "ECONOMY",
        passengers: int = 1,
    ) -> SearchResult:
        """搜尋長榮航空航班"""
        start_time = time.time()
        self._intercepted_apis.clear()

        try:
            await self.throttler.throttle()
            await self.rotate_session_if_needed()

            logger.info(
                f"[BR] 搜尋航班: {origin} → {destination}, "
                f"日期: {departure_date}"
            )

            # 1. 前往首頁（搜尋表單在首頁）
            await self._page.goto(
                self.SEARCH_URL,
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await random_delay(3, 5)

            # 2. 處理 Cookie/隱私彈窗
            await self._handle_popups()

            # 3. 填寫搜尋表單
            await self._fill_search_form(
                origin, destination, departure_date, return_date, cabin, passengers
            )

            # 4. 送出搜尋
            await self._submit_search()

            # 5. 等待結果
            await self._wait_for_results(timeout=25)

            # 6. 解析結果
            offers = self._parse_results(self._intercepted_apis)

            # 7. 如果 API 攔截失敗，嘗試從頁面 DOM 解析
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
            logger.error(f"[BR] 搜尋失敗: {e}")
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
            popup_selectors = [
                "button:has-text('接受所有Cookie')",
                "button:has-text('接受')",
                "button:has-text('同意')",
                "button:has-text('Accept')",
                ".cookie-consent button",
                "#onetrust-accept-btn-handler",
            ]
            for selector in popup_selectors:
                btn = self._page.locator(selector)
                if await btn.count() > 0:
                    await btn.first.click()
                    await random_delay(1, 2)
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
        """填寫長榮航空搜尋表單"""
        page = self._page

        # 行程類型
        if not return_date:
            try:
                one_way = page.locator(
                    "label:has-text('單程'), input[value='OW'], "
                    "[data-trip-type='oneway']"
                )
                if await one_way.count() > 0:
                    await one_way.first.click()
                    await random_delay(0.5, 1)
            except Exception:
                pass

        # 出發地
        origin_selectors = [
            "#departure-airport",
            "input[name*='depart']",
            "input[placeholder*='出發']",
            "[data-testid='departure']",
            "input[name*='origin']",
        ]
        await self._fill_airport(origin_selectors, origin)

        # 目的地
        dest_selectors = [
            "#arrival-airport",
            "input[name*='arriv']",
            "input[placeholder*='目的']",
            "[data-testid='arrival']",
            "input[name*='dest']",
        ]
        await self._fill_airport(dest_selectors, destination)

        # 日期
        await self._fill_date(departure_date, "departure")
        if return_date:
            await self._fill_date(return_date, "return")

        # 艙等
        cabin_map = {
            "ECONOMY": "經濟艙",
            "PREMIUM_ECONOMY": "豪華經濟艙",
            "BUSINESS": "商務艙",
        }
        cabin_text = cabin_map.get(cabin, "經濟艙")
        try:
            cabin_selector = page.locator(
                f"select option:has-text('{cabin_text}'), "
                f"[data-cabin]:has-text('{cabin_text}')"
            )
            if await cabin_selector.count() > 0:
                await cabin_selector.first.click()
        except Exception:
            pass

    async def _fill_airport(self, selectors: list[str], code: str) -> None:
        """填寫機場代碼"""
        for selector in selectors:
            try:
                el = self._page.locator(selector)
                if await el.count() > 0:
                    await el.first.click()
                    await random_delay(0.3, 0.8)
                    await el.first.fill("")
                    await human_like_typing(self._page, selector, code)
                    await random_delay(1, 2)

                    # 選擇建議
                    suggestion = self._page.locator(
                        f"li:has-text('{code}'), "
                        f"[class*='option']:has-text('{code}'), "
                        f".dropdown-item:has-text('{code}')"
                    )
                    if await suggestion.count() > 0:
                        await suggestion.first.click()
                    else:
                        await self._page.keyboard.press("Enter")
                    return
            except Exception:
                continue

    async def _fill_date(self, date_str: str, date_type: str) -> None:
        """填寫日期"""
        try:
            date_selectors = [
                f"input[name*='{date_type}']",
                f"#{'departure' if date_type == 'departure' else 'return'}-date",
                f"[data-testid='{date_type}-date']",
            ]

            for selector in date_selectors:
                el = self._page.locator(selector)
                if await el.count() > 0:
                    await el.first.click()
                    await random_delay(0.5, 1)
                    break

            # 嘗試直接輸入或點擊日曆
            year, month, day = date_str.split("-")
            day_selector = (
                f"[data-date='{date_str}'], "
                f"td[data-day='{int(day)}'][data-month='{int(month)-1}'], "
                f".calendar-day:has-text('{int(day)}')"
            )
            day_el = self._page.locator(day_selector)
            if await day_el.count() > 0:
                await day_el.first.click()
                await random_delay(0.5, 1)
        except Exception as e:
            logger.debug(f"[BR] 日期填寫可能需要調整: {e}")

    async def _submit_search(self) -> None:
        """送出搜尋"""
        selectors = [
            "button:has-text('搜尋航班')",
            "button:has-text('搜尋')",
            "button:has-text('Search')",
            "button[type='submit']",
            "#search-flight-btn",
            ".btn-search",
        ]

        for selector in selectors:
            try:
                btn = self._page.locator(selector)
                if await btn.count() > 0:
                    await btn.first.click()
                    logger.info("[BR] 搜尋已送出")
                    return
            except Exception:
                continue

        await self._page.keyboard.press("Enter")

    async def _wait_for_results(self, timeout: int = 25) -> None:
        """等待結果載入"""
        logger.info("[BR] 等待搜尋結果...")
        for _ in range(timeout):
            await asyncio.sleep(1)
            if self._intercepted_apis:
                return
            try:
                indicators = [
                    "[class*='flight-result']",
                    "[class*='fare-result']",
                    "[class*='search-result']",
                    ".flight-info",
                    "[class*='itinerary']",
                ]
                for ind in indicators:
                    if await self._page.locator(ind).count() > 0:
                        await random_delay(2, 3)
                        return
            except Exception:
                pass

    async def _parse_from_dom(self) -> list[FlightOffer]:
        """
        備援方案：從頁面 DOM 直接解析航班資訊
        當 API 攔截失敗時使用
        """
        offers = []
        try:
            # 嘗試取得頁面上的航班卡片
            flight_cards = self._page.locator(
                "[class*='flight-card'], [class*='flight-row'], "
                "[class*='result-item'], [class*='itinerary-card']"
            )
            count = await flight_cards.count()

            for i in range(min(count, 20)):
                try:
                    card = flight_cards.nth(i)
                    text = await card.inner_text()

                    # 從文字內容中提取關鍵資訊
                    # (這部分需要根據實際 DOM 結構調整)
                    offer = FlightOffer(
                        source="website_br_dom",
                        airline_code="BR",
                        airline_name=self.AIRLINE_NAME,
                        origin="",
                        destination="",
                        departure_date="",
                        price_twd=0,
                        cabin_class="ECONOMY",
                    )
                    # 此處需要根據實際頁面結構提取具體資訊
                    offers.append(offer)
                except Exception:
                    continue

        except Exception as e:
            logger.debug(f"[BR] DOM 解析失敗: {e}")

        return offers

    def _parse_results(self, intercepted: list[dict]) -> list[FlightOffer]:
        """解析攔截到的 API 回應"""
        offers = []

        for api_data in intercepted:
            data = api_data.get("data", {})

            flights = (
                data.get("flights", [])
                or data.get("flightList", [])
                or data.get("data", {}).get("flights", [])
                or data.get("fareList", [])
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
                    logger.debug(f"[BR] 解析航班失敗: {e}")

        if not offers and intercepted:
            logger.info(
                f"[BR] 攔截到 {len(intercepted)} 個 API 回應但未成功解析"
            )
            for api in intercepted:
                logger.info(f"  - URL: {api.get('url', 'unknown')}")

        return offers

    def _parse_single_flight(self, flight: dict) -> Optional[FlightOffer]:
        """解析單一航班"""
        if not isinstance(flight, dict):
            return None

        price = (
            flight.get("price", {}).get("total")
            or flight.get("totalFare")
            or flight.get("fare", {}).get("totalAmount")
            or flight.get("lowestFare")
            or 0
        )

        segments_raw = (
            flight.get("segments", [])
            or flight.get("legs", [])
            or flight.get("flightSegments", [])
        )

        segments = []
        for seg in segments_raw:
            if isinstance(seg, dict):
                segment = FlightSegment(
                    airline_code="BR",
                    flight_number=seg.get("flightNumber", seg.get("flightNo", "")),
                    departure_airport=seg.get("departureAirport", seg.get("origin", "")),
                    arrival_airport=seg.get("arrivalAirport", seg.get("destination", "")),
                    departure_time=seg.get("departureDateTime", seg.get("departure", "")),
                    arrival_time=seg.get("arrivalDateTime", seg.get("arrival", "")),
                    duration=seg.get("flyingTime", seg.get("duration", "")),
                    aircraft=seg.get("aircraftType", seg.get("equipment", "")),
                )
                segments.append(segment)

        return FlightOffer(
            source="website_br",
            airline_code="BR",
            airline_name=self.AIRLINE_NAME,
            origin=segments[0].departure_airport if segments else "",
            destination=segments[-1].arrival_airport if segments else "",
            departure_date=segments[0].departure_time[:10] if segments else "",
            price_twd=float(price) if price else 0,
            price_currency="TWD",
            cabin_class=flight.get("cabinClass", flight.get("cabin", "ECONOMY")),
            segments=[vars(s) for s in segments],
        )
