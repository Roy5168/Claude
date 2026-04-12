"""
中華航空 (China Airlines, CI) 網頁爬蟲

技術特徵：
- 官網使用 SPA 架構，航班搜尋結果由後端 API 動態載入
- 搜尋 API endpoint 格式為 JSON
- 策略：透過 Playwright 操作搜尋表單，攔截後端 API 回應
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


class ChinaAirlinesScraper(BaseAirlineScraper):
    """中華航空官網爬蟲"""

    AIRLINE_CODE = "CI"
    AIRLINE_NAME = "中華航空 China Airlines"
    BASE_URL = "https://www.china-airlines.com"
    SEARCH_URL = "https://www.china-airlines.com/tw/zh/booking/book-flights/flight-search"

    async def search_flights(
        self,
        origin: str = "TPE",
        destination: str = "NRT",
        departure_date: str = "",
        return_date: str = "",
        cabin: str = "ECONOMY",
        passengers: int = 1,
    ) -> SearchResult:
        """
        搜尋中華航空航班

        流程：
        1. 前往訂票頁面
        2. 填寫搜尋表單（出發/目的地/日期/艙等）
        3. 送出搜尋
        4. 等待並攔截後端 API 回應
        5. 解析航班資料
        """
        start_time = time.time()
        self._intercepted_apis.clear()

        try:
            await self.throttler.throttle()
            await self.rotate_session_if_needed()

            logger.info(
                f"[CI] 搜尋航班: {origin} → {destination}, "
                f"日期: {departure_date}"
            )

            # 1. 前往首頁建立正常瀏覽足跡
            await self._page.goto(
                self.BASE_URL + "/tw/zh",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await random_delay(2, 4)

            # 2. 前往航班搜尋頁面
            await self._page.goto(
                self.SEARCH_URL,
                wait_until="domcontentloaded",
                timeout=30000,
            )
            await random_delay(2, 4)

            # 3. 處理可能的 Cookie 同意彈窗
            try:
                cookie_btn = self._page.locator(
                    "button:has-text('接受'), button:has-text('同意'), "
                    "button:has-text('Accept')"
                )
                if await cookie_btn.count() > 0:
                    await cookie_btn.first.click()
                    await random_delay(1, 2)
            except Exception:
                pass

            # 4. 設定搜尋條件
            await self._fill_search_form(
                origin, destination, departure_date, return_date, cabin, passengers
            )

            # 5. 送出搜尋並等待結果
            await self._submit_search()

            # 6. 等待 API 回應被攔截
            await self._wait_for_flight_results(timeout=20)

            # 7. 解析攔截到的 API 資料
            offers = self._parse_results(self._intercepted_apis)

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
            logger.error(f"[CI] 搜尋失敗: {e}")
            return SearchResult(
                query_origin=origin,
                query_destination=destination,
                query_date=departure_date,
                query_return_date=return_date,
                error=str(e),
                search_duration_sec=time.time() - start_time,
            )

    async def _fill_search_form(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
        cabin: str,
        passengers: int,
    ) -> None:
        """填寫搜尋表單"""
        page = self._page

        # 選擇單程或來回
        if return_date:
            trip_selector = "[data-value='roundTrip'], #roundTrip, label:has-text('來回')"
        else:
            trip_selector = "[data-value='oneWay'], #oneWay, label:has-text('單程')"

        try:
            trip_btn = page.locator(trip_selector)
            if await trip_btn.count() > 0:
                await trip_btn.first.click()
                await random_delay(0.5, 1)
        except Exception:
            logger.debug("[CI] 無法找到行程類型選擇器，嘗試繼續")

        # 填寫出發地
        origin_selectors = [
            "input[name='origin']",
            "input[placeholder*='出發']",
            "input[placeholder*='From']",
            "#origin",
            "[data-testid='origin-input']",
        ]
        await self._try_fill_input(origin_selectors, origin)
        await random_delay(1, 2)

        # 選擇自動完成建議
        await self._select_autocomplete(origin)

        # 填寫目的地
        dest_selectors = [
            "input[name='destination']",
            "input[placeholder*='目的']",
            "input[placeholder*='To']",
            "#destination",
            "[data-testid='destination-input']",
        ]
        await self._try_fill_input(dest_selectors, destination)
        await random_delay(1, 2)
        await self._select_autocomplete(destination)

        # 選擇日期
        await self._select_date(departure_date, is_departure=True)
        if return_date:
            await self._select_date(return_date, is_departure=False)

    async def _try_fill_input(self, selectors: list[str], value: str) -> None:
        """嘗試多個選擇器填寫輸入框"""
        for selector in selectors:
            try:
                element = self._page.locator(selector)
                if await element.count() > 0:
                    await element.first.click()
                    await element.first.fill("")
                    await human_like_typing(self._page, selector, value)
                    return
            except Exception:
                continue
        logger.warning(f"[CI] 找不到輸入框，嘗試的選擇器: {selectors}")

    async def _select_autocomplete(self, code: str) -> None:
        """選擇自動完成下拉選單中的選項"""
        await random_delay(1, 2)
        try:
            suggestion = self._page.locator(
                f"li:has-text('{code}'), "
                f"[class*='suggestion']:has-text('{code}'), "
                f"[class*='autocomplete'] [class*='item']:has-text('{code}')"
            )
            if await suggestion.count() > 0:
                await suggestion.first.click()
                await random_delay(0.5, 1)
        except Exception:
            # 嘗試按 Enter 確認
            await self._page.keyboard.press("Enter")

    async def _select_date(self, date_str: str, is_departure: bool) -> None:
        """選擇日期（從日曆元件）"""
        # 日期格式: YYYY-MM-DD
        parts = date_str.split("-")
        if len(parts) != 3:
            return

        year, month, day = parts

        try:
            # 嘗試點擊日期輸入框
            date_type = "departure" if is_departure else "return"
            date_selectors = [
                f"input[name*='{date_type}']",
                f"[data-testid='{date_type}-date']",
                f"input[placeholder*='日期']",
            ]

            for selector in date_selectors:
                el = self._page.locator(selector)
                if await el.count() > 0:
                    await el.first.click()
                    break

            await random_delay(1, 2)

            # 在日曆中選擇日期
            day_int = str(int(day))  # 去除前導零
            date_cell = self._page.locator(
                f"[data-date='{date_str}'], "
                f"td[data-day='{day_int}'], "
                f"button:has-text('{day_int}')"
            )
            if await date_cell.count() > 0:
                await date_cell.first.click()
                await random_delay(0.5, 1)
        except Exception as e:
            logger.debug(f"[CI] 日期選擇可能需要調整: {e}")

    async def _submit_search(self) -> None:
        """送出搜尋"""
        submit_selectors = [
            "button[type='submit']:has-text('搜尋')",
            "button:has-text('搜尋航班')",
            "button:has-text('Search')",
            "button[type='submit']",
            "[data-testid='search-button']",
        ]

        for selector in submit_selectors:
            try:
                btn = self._page.locator(selector)
                if await btn.count() > 0:
                    await btn.first.click()
                    logger.info("[CI] 搜尋已送出")
                    return
            except Exception:
                continue

        # 備援：按 Enter
        await self._page.keyboard.press("Enter")

    async def _wait_for_flight_results(self, timeout: int = 20) -> None:
        """等待航班結果載入"""
        logger.info("[CI] 等待航班搜尋結果...")

        for _ in range(timeout):
            await asyncio.sleep(1)

            # 檢查是否有攔截到 flight API
            if self._intercepted_apis:
                logger.info(
                    f"[CI] 攔截到 {len(self._intercepted_apis)} 個 API 回應"
                )
                return

            # 檢查頁面是否有結果
            try:
                result_indicators = [
                    "[class*='flight-result']",
                    "[class*='flight-list']",
                    "[class*='search-result']",
                    "[class*='itinerary']",
                ]
                for indicator in result_indicators:
                    if await self._page.locator(indicator).count() > 0:
                        await random_delay(2, 3)
                        return
            except Exception:
                pass

        logger.warning("[CI] 等待超時，可能未找到結果或被攔截")

    def _parse_results(self, intercepted: list[dict]) -> list[FlightOffer]:
        """
        解析攔截到的 API 回應
        注意：實際的 API 結構需要根據實際攔截結果調整
        """
        offers = []

        for api_data in intercepted:
            data = api_data.get("data", {})
            url = api_data.get("url", "")

            # 嘗試解析不同格式的回應
            flights = (
                data.get("flights", [])
                or data.get("data", {}).get("flights", [])
                or data.get("flightOffers", [])
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
                    logger.debug(f"[CI] 解析單一航班失敗: {e}")

        # 如果 API 攔截未成功解析，記錄原始資料供除錯
        if not offers and intercepted:
            logger.info(
                f"[CI] 攔截到 {len(intercepted)} 個 API 但未成功解析，"
                "可能需要調整解析邏輯。攔截的 URL:"
            )
            for api in intercepted:
                logger.info(f"  - {api.get('url', 'unknown')}")

        return offers

    def _parse_single_flight(self, flight: dict) -> Optional[FlightOffer]:
        """解析單一航班資料（需根據實際 API 格式調整）"""
        if not isinstance(flight, dict):
            return None

        # 通用欄位名稱猜測
        price = (
            flight.get("price", {}).get("total")
            or flight.get("totalPrice")
            or flight.get("fare", {}).get("total")
            or flight.get("amount")
            or 0
        )

        segments_raw = (
            flight.get("segments", [])
            or flight.get("legs", [])
            or flight.get("itineraries", [])
        )

        segments = []
        for seg in segments_raw:
            if isinstance(seg, dict):
                segment = FlightSegment(
                    airline_code="CI",
                    flight_number=seg.get("flightNumber", seg.get("number", "")),
                    departure_airport=seg.get("origin", seg.get("departureAirport", "")),
                    arrival_airport=seg.get("destination", seg.get("arrivalAirport", "")),
                    departure_time=seg.get("departureTime", seg.get("departure", "")),
                    arrival_time=seg.get("arrivalTime", seg.get("arrival", "")),
                    duration=seg.get("duration", ""),
                    aircraft=seg.get("aircraft", seg.get("equipmentType", "")),
                )
                segments.append(segment)

        return FlightOffer(
            source="website_ci",
            airline_code="CI",
            airline_name=self.AIRLINE_NAME,
            origin=segments[0].departure_airport if segments else "",
            destination=segments[-1].arrival_airport if segments else "",
            departure_date=segments[0].departure_time[:10] if segments else "",
            price_twd=float(price) if price else 0,
            price_currency="TWD",
            cabin_class=flight.get("cabin", flight.get("cabinClass", "ECONOMY")),
            segments=[vars(s) for s in segments],
            seats_available=flight.get("seatsAvailable", 0),
        )
