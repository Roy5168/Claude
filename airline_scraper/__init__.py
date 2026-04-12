"""
台灣三大航空公司機票資料擷取系統
Taiwan Airlines Ticket Scraper

支援航空公司：
- 中華航空 (China Airlines, CI)
- 長榮航空 (EVA Air, BR)
- 星宇航空 (Starlux Airlines, JX)

策略層級：
1. 優先：Amadeus API（合法、穩定、高成功率）
2. 備援：智慧型網頁爬蟲（Playwright + 反偵測）
"""

__version__ = "1.0.0"
