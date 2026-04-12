"""
網頁爬蟲基底類別
使用 Playwright 進行網頁自動化，搭配反偵測措施
"""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import Optional

from airline_scraper.config import ScraperConfig
from airline_scraper.utils.anti_detect import (
    get_stealth_scripts,
    get_browser_launch_args,
    random_delay,
    RequestThrottler,
    SessionRotator,
)
from airline_scraper.utils.data_models import SearchResult

logger = logging.getLogger(__name__)


class BaseAirlineScraper(ABC):
    """航空公司網站爬蟲基底類別"""

    AIRLINE_CODE: str = ""
    AIRLINE_NAME: str = ""
    BASE_URL: str = ""

    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.throttler = RequestThrottler(
            min_delay=self.config.min_delay,
            max_delay=self.config.max_delay,
            batch_size=self.config.batch_size,
            batch_pause=self.config.batch_pause,
        )
        self.session_rotator = SessionRotator()
        self._browser = None
        self._context = None
        self._page = None
        self._intercepted_apis: list[dict] = []

    async def start_browser(self) -> None:
        """啟動瀏覽器（帶反偵測設定）"""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "請安裝 Playwright:\n"
                "  pip install playwright\n"
                "  playwright install chromium"
            )

        self._playwright = await async_playwright().start()

        launch_args = get_browser_launch_args()
        launch_options = {
            "headless": self.config.headless,
            "args": launch_args,
        }

        # 代理設定
        if self.config.proxy:
            launch_options["proxy"] = {"server": self.config.proxy}

        self._browser = await self._playwright.chromium.launch(**launch_options)
        await self._create_new_context()

        logger.info(
            f"[{self.AIRLINE_CODE}] 瀏覽器啟動完成 "
            f"(headless={self.config.headless})"
        )

    async def _create_new_context(self) -> None:
        """建立新的瀏覽器上下文（用於 session 輪替）"""
        if self._context:
            await self._context.close()

        user_agent = random.choice(self.config.user_agents)

        self._context = await self._browser.new_context(
            viewport={
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
            user_agent=user_agent,
            locale="zh-TW",
            timezone_id="Asia/Taipei",
            # 地理位置偽裝（台北）
            geolocation={"latitude": 25.0330, "longitude": 121.5654},
            permissions=["geolocation"],
        )

        # 注入反偵測腳本
        await self._context.add_init_script(get_stealth_scripts())

        self._page = await self._context.new_page()

        # 設定 API 攔截器
        self._intercepted_apis.clear()
        self._page.on("response", self._on_response)

        logger.debug(f"[{self.AIRLINE_CODE}] 新 session 建立，UA: {user_agent[:50]}...")

    async def _on_response(self, response) -> None:
        """
        攔截網路回應 - 關鍵技術
        航空公司網站的 SPA 前端都會呼叫後端 API
        攔截這些 JSON 回應比解析 HTML 更穩定
        """
        try:
            url = response.url
            content_type = response.headers.get("content-type", "")

            # 攔截 JSON API 回應
            if "application/json" in content_type and response.status == 200:
                # 篩選可能是航班搜尋結果的 API
                keywords = [
                    "flight", "search", "offer", "fare", "price",
                    "availability", "itinerary", "booking",
                ]
                url_lower = url.lower()
                if any(kw in url_lower for kw in keywords):
                    try:
                        body = await response.json()
                        self._intercepted_apis.append({
                            "url": url,
                            "status": response.status,
                            "data": body,
                        })
                        logger.debug(
                            f"[{self.AIRLINE_CODE}] 攔截到 API: "
                            f"{url[:80]}..."
                        )
                    except Exception:
                        pass
        except Exception:
            pass

    async def rotate_session_if_needed(self) -> None:
        """需要時輪替 session"""
        if self.session_rotator.should_rotate():
            logger.info(f"[{self.AIRLINE_CODE}] 輪替 session...")
            await self._create_new_context()
            await random_delay(2.0, 5.0)

    async def close(self) -> None:
        """關閉瀏覽器"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info(f"[{self.AIRLINE_CODE}] 瀏覽器已關閉")

    @abstractmethod
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str = "",
        cabin: str = "ECONOMY",
        passengers: int = 1,
    ) -> SearchResult:
        """
        搜尋航班（子類別必須實作）

        參數：
            origin: 出發機場 IATA
            destination: 目的地 IATA
            departure_date: "YYYY-MM-DD"
            return_date: 回程日期（選填）
            cabin: 艙等
            passengers: 乘客人數
        """
        ...

    @abstractmethod
    def _parse_results(self, raw_data: dict) -> list:
        """解析搜尋結果（子類別必須實作）"""
        ...

    async def __aenter__(self):
        await self.start_browser()
        return self

    async def __aexit__(self, *args):
        await self.close()
