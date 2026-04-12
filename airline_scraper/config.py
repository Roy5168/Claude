"""
設定檔 - 集中管理所有設定參數
"""

import os
from dataclasses import dataclass, field


@dataclass
class AmadeusConfig:
    """Amadeus API 設定"""
    client_id: str = ""
    client_secret: str = ""
    # 正式環境: https://api.amadeus.com
    # 測試環境: https://test.api.amadeus.com
    base_url: str = "https://test.api.amadeus.com"

    def __post_init__(self):
        self.client_id = self.client_id or os.getenv("AMADEUS_CLIENT_ID", "")
        self.client_secret = self.client_secret or os.getenv("AMADEUS_CLIENT_SECRET", "")

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)


@dataclass
class ScraperConfig:
    """網頁爬蟲設定"""
    # 請求延遲（秒）- 隨機化範圍
    min_delay: float = 3.0
    max_delay: float = 8.0

    # 每批次最大請求數
    batch_size: int = 5

    # 批次間休息時間（秒）
    batch_pause: float = 30.0

    # 最大重試次數
    max_retries: int = 3

    # 瀏覽器啟動設定
    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080

    # 代理設定（建議使用住宅代理）
    proxy: str = ""  # 格式: http://user:pass@host:port

    # User-Agent 輪替清單
    user_agents: list = field(default_factory=lambda: [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    ])


# 航空公司 IATA 代碼對照
AIRLINE_CODES = {
    "china_airlines": "CI",
    "eva_air": "BR",
    "starlux": "JX",
}

AIRLINE_NAMES = {
    "CI": "中華航空 China Airlines",
    "BR": "長榮航空 EVA Air",
    "JX": "星宇航空 Starlux Airlines",
}

# 台灣主要機場
TAIWAN_AIRPORTS = {
    "TPE": "台灣桃園國際機場",
    "TSA": "台北松山機場",
    "KHH": "高雄國際機場",
    "RMQ": "台中國際機場",
}

# 熱門航線（從台灣出發）
POPULAR_ROUTES = [
    {"origin": "TPE", "destination": "NRT", "name": "台北→東京成田"},
    {"origin": "TPE", "destination": "HND", "name": "台北→東京羽田"},
    {"origin": "TPE", "destination": "KIX", "name": "台北→大阪關西"},
    {"origin": "TPE", "destination": "ICN", "name": "台北→首爾仁川"},
    {"origin": "TPE", "destination": "HKG", "name": "台北→香港"},
    {"origin": "TPE", "destination": "BKK", "name": "台北→曼谷"},
    {"origin": "TPE", "destination": "SIN", "name": "台北→新加坡"},
    {"origin": "TPE", "destination": "LAX", "name": "台北→洛杉磯"},
    {"origin": "TPE", "destination": "SFO", "name": "台北→舊金山"},
    {"origin": "TPE", "destination": "AMS", "name": "台北→阿姆斯特丹"},
]
