"""
Amadeus API 客戶端
這是推薦的主要資料來源 - 合法、穩定、高成功率

使用前需要：
1. 註冊 Amadeus for Developers: https://developers.amadeus.com/
2. 建立應用程式，取得 API Key 和 Secret
3. 設定環境變數 AMADEUS_CLIENT_ID 和 AMADEUS_CLIENT_SECRET

免費額度：每月 2,000 次 API 呼叫（測試環境）
"""

import asyncio
import logging
import time
from typing import Optional

import httpx

from airline_scraper.config import AmadeusConfig, AIRLINE_NAMES
from airline_scraper.utils.data_models import (
    FlightOffer,
    FlightSegment,
    SearchResult,
)

logger = logging.getLogger(__name__)


class AmadeusClient:
    """Amadeus Flight Offers Search API 客戶端"""

    def __init__(self, config: Optional[AmadeusConfig] = None):
        self.config = config or AmadeusConfig()
        self._token: str = ""
        self._token_expires: float = 0
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()

    async def _ensure_token(self) -> None:
        """取得或刷新 OAuth2 access token"""
        if self._token and time.time() < self._token_expires - 60:
            return

        if not self.config.is_configured:
            raise ValueError(
                "Amadeus API 未設定。請設定環境變數：\n"
                "  export AMADEUS_CLIENT_ID='your_client_id'\n"
                "  export AMADEUS_CLIENT_SECRET='your_client_secret'\n"
                "註冊：https://developers.amadeus.com/"
            )

        url = f"{self.config.base_url}/v1/security/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }

        response = await self._client.post(
            url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        result = response.json()

        self._token = result["access_token"]
        self._token_expires = time.time() + result["expires_in"]
        logger.info("Amadeus access token 取得成功")

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str = "",
        adults: int = 1,
        cabin: str = "ECONOMY",
        currency: str = "TWD",
        max_results: int = 50,
        airline_codes: Optional[list[str]] = None,
    ) -> SearchResult:
        """
        搜尋航班報價

        參數：
            origin: 出發機場 IATA 代碼 (如 "TPE")
            destination: 目的地機場 IATA 代碼 (如 "NRT")
            departure_date: 出發日期 "YYYY-MM-DD"
            return_date: 回程日期（選填，留空為單程）
            adults: 成人人數
            cabin: 艙等 ECONOMY/PREMIUM_ECONOMY/BUSINESS/FIRST
            currency: 顯示幣別
            max_results: 最大結果數
            airline_codes: 限定航空公司代碼列表 (如 ["CI", "BR", "JX"])
        """
        start_time = time.time()
        await self._ensure_token()

        # 建構搜尋參數
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": adults,
            "travelClass": cabin,
            "currencyCode": currency,
            "max": max_results,
        }

        if return_date:
            params["returnDate"] = return_date

        # 限定航空公司（台灣三大：CI, BR, JX）
        if airline_codes:
            params["includedAirlineCodes"] = ",".join(airline_codes)

        url = f"{self.config.base_url}/v2/shopping/flight-offers"
        headers = {"Authorization": f"Bearer {self._token}"}

        logger.info(
            f"搜尋航班: {origin} → {destination}, "
            f"日期: {departure_date}, 艙等: {cabin}"
        )

        try:
            response = await self._client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as e:
            error_msg = f"Amadeus API 錯誤: {e.response.status_code}"
            try:
                error_detail = e.response.json()
                errors = error_detail.get("errors", [])
                if errors:
                    error_msg += f" - {errors[0].get('detail', '')}"
            except Exception:
                pass
            logger.error(error_msg)
            return SearchResult(
                query_origin=origin,
                query_destination=destination,
                query_date=departure_date,
                query_return_date=return_date,
                query_cabin=cabin,
                error=error_msg,
                search_duration_sec=time.time() - start_time,
            )

        # 解析結果
        offers = self._parse_offers(data, origin, destination, departure_date, return_date)
        duration = time.time() - start_time

        result = SearchResult(
            query_origin=origin,
            query_destination=destination,
            query_date=departure_date,
            query_return_date=return_date,
            query_cabin=cabin,
            query_passengers=adults,
            offers=offers,
            search_duration_sec=duration,
        )

        logger.info(f"找到 {len(offers)} 個航班報價 (耗時 {duration:.1f}s)")
        return result

    def _parse_offers(
        self,
        data: dict,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: str,
    ) -> list[FlightOffer]:
        """解析 Amadeus API 回傳的航班報價"""
        offers = []
        dictionaries = data.get("dictionaries", {})
        carriers = dictionaries.get("carriers", {})

        for item in data.get("data", []):
            try:
                price_info = item.get("price", {})
                price_total = float(price_info.get("grandTotal", 0))
                currency = price_info.get("currency", "TWD")

                # 解析航段
                segments = []
                primary_airline = ""
                for itinerary in item.get("itineraries", []):
                    for seg in itinerary.get("segments", []):
                        carrier_code = seg.get("carrierCode", "")
                        if not primary_airline:
                            primary_airline = carrier_code

                        departure = seg.get("departure", {})
                        arrival = seg.get("arrival", {})

                        flight_seg = FlightSegment(
                            airline_code=carrier_code,
                            flight_number=f"{carrier_code}{seg.get('number', '')}",
                            departure_airport=departure.get("iataCode", ""),
                            arrival_airport=arrival.get("iataCode", ""),
                            departure_time=departure.get("at", ""),
                            arrival_time=arrival.get("at", ""),
                            duration=seg.get("duration", "").replace("PT", "").lower(),
                            aircraft=seg.get("aircraft", {}).get("code", ""),
                        )
                        segments.append(flight_seg)

                # 解析艙等與座位資訊
                traveler_pricings = item.get("travelerPricings", [])
                cabin_class = ""
                booking_class = ""
                if traveler_pricings:
                    fare_details = traveler_pricings[0].get("fareDetailsBySegment", [])
                    if fare_details:
                        cabin_class = fare_details[0].get("cabin", "ECONOMY")
                        booking_class = fare_details[0].get("class", "")

                # 剩餘座位
                seats = item.get("numberOfBookableSeats", 0)

                airline_name = carriers.get(
                    primary_airline,
                    AIRLINE_NAMES.get(primary_airline, primary_airline),
                )

                offer = FlightOffer(
                    source="amadeus",
                    airline_code=primary_airline,
                    airline_name=airline_name,
                    origin=origin,
                    destination=destination,
                    departure_date=departure_date,
                    return_date=return_date,
                    price_twd=price_total if currency == "TWD" else 0,
                    price_currency="TWD",
                    price_original=price_total,
                    currency_original=currency,
                    trip_type="round_trip" if return_date else "one_way",
                    cabin_class=cabin_class or "ECONOMY",
                    segments=[s.to_dict() if hasattr(s, 'to_dict') else vars(s) for s in segments],
                    booking_class=booking_class,
                    seats_available=seats,
                    refundable=not item.get("nonHomogeneous", False),
                )
                offers.append(offer)

            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"解析報價時發生錯誤: {e}")
                continue

        return offers

    async def search_taiwan_airlines(
        self,
        origin: str = "TPE",
        destination: str = "NRT",
        departure_date: str = "",
        return_date: str = "",
        cabin: str = "ECONOMY",
    ) -> SearchResult:
        """
        專門搜尋台灣三大航空公司的航班
        自動限定 CI（中華航空）、BR（長榮航空）、JX（星宇航空）
        """
        return await self.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            cabin=cabin,
            airline_codes=["CI", "BR", "JX"],
        )
