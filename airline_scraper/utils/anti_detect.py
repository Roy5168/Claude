"""
反偵測工具模組
提供瀏覽器指紋偽裝、請求頻率控制等功能
"""

import asyncio
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def random_delay(min_sec: float = 2.0, max_sec: float = 6.0) -> None:
    """模擬人類操作的隨機延遲"""
    delay = random.uniform(min_sec, max_sec)
    logger.debug(f"等待 {delay:.1f} 秒...")
    await asyncio.sleep(delay)


async def human_like_mouse_move(page, target_x: int, target_y: int) -> None:
    """模擬人類滑鼠移動軌跡（非直線）"""
    current = await page.evaluate("() => ({x: 0, y: 0})")
    steps = random.randint(5, 15)

    for i in range(steps):
        progress = (i + 1) / steps
        # 加入隨機偏移模擬自然移動
        jitter_x = random.randint(-3, 3)
        jitter_y = random.randint(-2, 2)
        x = int(current["x"] + (target_x - current["x"]) * progress + jitter_x)
        y = int(current["y"] + (target_y - current["y"]) * progress + jitter_y)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.01, 0.05))


async def human_like_typing(page, selector: str, text: str) -> None:
    """模擬人類打字速度（有隨機間隔）"""
    await page.click(selector)
    await asyncio.sleep(random.uniform(0.3, 0.8))

    for char in text:
        await page.keyboard.type(char)
        # 模擬打字間隔：大多數快速，偶爾停頓
        if random.random() < 0.1:
            await asyncio.sleep(random.uniform(0.2, 0.5))
        else:
            await asyncio.sleep(random.uniform(0.05, 0.15))


def get_stealth_scripts() -> str:
    """
    返回注入瀏覽器的反偵測 JavaScript
    用於隱藏 Playwright/自動化工具的特徵
    """
    return """
    // 覆蓋 navigator.webdriver 屬性
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });

    // 覆蓋 Chrome 自動化相關屬性
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {},
    };

    // 偽裝 plugins 陣列
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Native Client', filename: 'internal-nacl-plugin' },
        ],
    });

    // 偽裝語言設定
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-TW', 'zh', 'en-US', 'en'],
    });

    // 隱藏自動化標記
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) =>
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters);

    // 偽裝 WebGL 資訊
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.call(this, parameter);
    };
    """


def get_browser_launch_args() -> list:
    """返回瀏覽器啟動參數，用於降低被偵測的風險"""
    return [
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-infobars",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--window-size=1920,1080",
        "--start-maximized",
        "--lang=zh-TW",
    ]


class RequestThrottler:
    """
    請求節流器
    確保請求頻率不會過高，避免觸發反爬蟲機制
    """

    def __init__(
        self,
        min_delay: float = 3.0,
        max_delay: float = 8.0,
        batch_size: int = 5,
        batch_pause: float = 30.0,
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.batch_size = batch_size
        self.batch_pause = batch_pause
        self._request_count = 0

    async def throttle(self) -> None:
        """在每次請求前調用，自動控制頻率"""
        self._request_count += 1

        if self._request_count % self.batch_size == 0:
            pause = self.batch_pause + random.uniform(-5, 10)
            logger.info(
                f"已完成 {self._request_count} 個請求，"
                f"休息 {pause:.0f} 秒避免觸發限制..."
            )
            await asyncio.sleep(pause)
        else:
            await random_delay(self.min_delay, self.max_delay)

    def reset(self) -> None:
        self._request_count = 0


class SessionRotator:
    """
    Session 輪替器
    定期更換瀏覽器上下文，避免 session 指紋被追蹤
    """

    def __init__(self, max_requests_per_session: int = 15):
        self.max_requests = max_requests_per_session
        self._count = 0

    def should_rotate(self) -> bool:
        self._count += 1
        if self._count >= self.max_requests:
            self._count = 0
            return True
        return False
