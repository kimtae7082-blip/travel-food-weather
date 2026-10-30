"""외부 서비스 연결. 키는 서버에서만 읽고 응답/로그에 노출하지 않습니다."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import math
import os
from pathlib import Path
from time import monotonic
from urllib.parse import urlparse

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
# 좌표는 시·도 전체의 날씨가 아닌 기본 검색 도시의 대표 지점입니다.
CENTERS = {
    "서울": ("서울", 37.5665, 126.9780), "부산": ("부산", 35.1796, 129.0756),
    "대구": ("대구", 35.8714, 128.6014), "인천": ("인천", 37.4563, 126.7052),
    "광주": ("광주", 35.1595, 126.8526), "대전": ("대전", 36.3504, 127.3845),
    "울산": ("울산", 35.5384, 129.3114), "세종": ("세종", 36.4800, 127.2890),
    "경기": ("수원", 37.2636, 127.0286), "강원": ("강릉", 37.7519, 128.8761),
    "충북": ("단양", 36.9845, 128.3655), "충남": ("공주", 36.4465, 127.1190),
    "전북": ("전주", 35.8242, 127.1480), "전남": ("순천", 34.9506, 127.4872),
    "경북": ("경주", 35.8562, 129.2247), "경남": ("통영", 34.8544, 128.4332),
    "제주": ("서귀포", 33.2541, 126.5601),
}
_weather_cache = {}


def now():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def settings():
    """.env를 매 요청에 다시 읽습니다. 시스템 환경변수가 파일보다 우선합니다."""
    keys = ("KAKAO_REST_API_KEY", "BOOKING_API_TOKEN", "BOOKING_AFFILIATE_ID", "BOOKING_ENV")
    try:
        # 키에 ${...}가 포함돼도 다른 값으로 치환하거나 os.environ에 남기지 않습니다.
        data = dotenv_values(ROOT / ".env", encoding="utf-8-sig", interpolate=False)
    except (OSError, UnicodeError):
        data = {}
    return {key: str((os.environ[key] if key in os.environ else data.get(key)) or "").strip()
            for key in keys}


def connection_status():
    config = settings()
    return {"places": "configured" if config["KAKAO_REST_API_KEY"] else "needs_key",
            "weather": "available", "hotel_prices": "configured" if
            config["BOOKING_API_TOKEN"] and config["BOOKING_AFFILIATE_ID"] else "needs_partner_access",
            "hotel_environment": "production" if config["BOOKING_ENV"] == "production" else "sandbox"}


class ProviderError(Exception):
    pass


def request_json(method, url, **kwargs):
    try:
        with httpx.Client(timeout=15, follow_redirects=False) as client:
            response = client.request(method, url, **kwargs)
        if response.status_code in (401, 403):
            raise ProviderError("API 키 또는 서비스 이용 권한을 확인해 주세요.")
        if response.status_code == 429:
            raise ProviderError("서비스 요청 한도를 초과했습니다. 잠시 후 다시 검색해 주세요.")
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError()
        return data
    except (httpx.HTTPError, ValueError):
        raise ProviderError("외부 서비스에 연결하지 못했어요. 잠시 후 다시 시도해 주세요.") from None


def safe_link(value, domains):
    if not isinstance(value, str):
        return None
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    if any(parsed.hostname == host or parsed.hostname.endswith("." + host) for host in domains):
        return value.replace("http://", "https://", 1)
    return None


def weather_label(code):
    if code == 0: return "맑음"
    if code in (1, 2): return "대체로 맑음 / 구름 조금"
    if code == 3: return "흐림"
    if code in (45, 48): return "안개"
    if code in (51, 53, 55, 56, 57): return "이슬비"
    if code in (61, 63, 65, 66, 67, 80, 81, 82): return "비 / 소나기"
    if code in (71, 73, 75, 77, 85, 86): return "눈"
    if code in (95, 96, 99): return "뇌우"
    return "상태 정보 미제공"


def weather(region):
    base = {"region": region, "temperature": None, "valid_at": None, "fetched_at": None,
            "source_url": "https://open-meteo.com/", "issued_at": None}
    if region not in CENTERS:
        return {**base, "status": "select_region", "message": "날씨를 볼 지역을 선택해 주세요."}
    cached = _weather_cache.get(region)
    if cached and monotonic() - cached[0] < 600:
        return cached[1]
    city, lat, lon = CENTERS[region]
    try:
        data = request_json("GET", "https://api.open-meteo.com/v1/forecast", params={
            "latitude": lat, "longitude": lon, "current": "temperature_2m,weather_code",
            "timezone": "Asia/Seoul", "forecast_days": 1,
        })
        current = data["current"]
        temperature = current["temperature_2m"]
        if not isinstance(temperature, (int, float)) or not math.isfinite(temperature):
            raise ValueError()
        result = {**base, "status": "live", "city": city, "temperature": temperature,
                  "valid_at": current["time"], "fetched_at": now(),
                  "message": weather_label(current.get("weather_code")),
                  "measurement": "기상 모델 기반 현재 추정값 · 관측 실측값 아님"}
        _weather_cache[region] = (monotonic(), result)
        return result
    except (ProviderError, KeyError, TypeError, ValueError) as exc:
        return {**base, "city": city, "status": "unavailable", "message": str(exc) if isinstance(exc, ProviderError) else "날씨 응답을 해석하지 못했습니다."}


def search_places(region, category, query, page):
    key = settings()["KAKAO_REST_API_KEY"]
    if not key:
        return {"items": [], "total": 0, "status": "needs_key", "mode": "live",
                "message": "실제 장소 검색은 카카오 REST API 키를 등록하면 시작됩니다.", "has_more": False}
    categories = [category] if category != "all" else ["scenery", "stay", "food"]
    fetched = now()

    def search_one(kind):
        code, term = {"stay": ("AD5", "숙소"), "scenery": ("AT4", "관광명소"), "food": ("FD6", "음식점")}[kind]
        # 키워드 검색은 선택 시·도와 질의어를 사용. 빈 질의는 대표 도시명 사용.
        location = "" if region == "전체" else region
        default_city = CENTERS[region][0] if region in CENTERS else "대한민국"
        text = f"{location} {query.strip() or default_city} {term}".strip()
        data = request_json("GET", "https://dapi.kakao.com/v2/local/search/keyword.json",
                            headers={"Authorization": f"KakaoAK {key}"},
                            params={"query": text, "category_group_code": code, "page": page, "size": 9})
        if not isinstance(data.get("documents"), list) or not isinstance(data.get("meta"), dict):
            raise ProviderError("장소 응답 형식을 확인할 수 없습니다.")
        results = []
        for place in data.get("documents", []):
            address = place.get("road_address_name") or place.get("address_name") or "주소 미제공"
            results.append({"id": f"kakao-{place['id']}", "region": region, "city": address,
                            "name": place["place_name"], "category": kind, "audience": "both",
                            "description": place.get("category_name", "분류 정보 미제공"),
                            "tags": "실제 장소 검색·여행 유형 적합성 미검증",
                            "address": address, "phone": place.get("phone") or "미제공",
                            "source_url": safe_link(place.get("place_url"), ["kakao.com"]),
                            "provider": "카카오 로컬", "fetched_at": fetched, "checked_at": None,
                            "operating_status": "현재 영업 여부는 별도 확인 필요", "is_demo": 0})
        meta = data.get("meta", {})
        return results, not meta.get("is_end", True)

    items, more, warnings = [], False, []
    with ThreadPoolExecutor(max_workers=3) as executor:
        jobs = [(kind, executor.submit(search_one, kind)) for kind in categories]
        for kind, job in jobs:
            try:
                batch, has_more = job.result()
                items.extend(batch)
                more = more or has_more
            except (ProviderError, KeyError, TypeError) as exc:
                warnings.append(f"{kind}: {exc}" if isinstance(exc, ProviderError) else "장소 응답 형식을 확인할 수 없습니다.")
    return {"items": items, "total": len(items), "mode": "live", "page": page, "has_more": more,
            "status": "partial" if warnings and items else "unavailable" if warnings else "live",
            "message": " / ".join(warnings) if warnings else "카카오 로컬 검색 결과입니다. 맛·편안함·가족 적합성을 보장하는 추천 순위가 아닙니다.",
            "fetched_at": fetched}


def hotel_prices(region, checkin, checkout, adults, children):
    config = settings()
    if not config["BOOKING_API_TOKEN"] or not config["BOOKING_AFFILIATE_ID"]:
        return {"status": "needs_partner_access", "items": [], "message": "숙박 가격 자동 조회는 Booking.com Demand API 제휴 승인과 키 등록이 필요합니다."}
    production = config["BOOKING_ENV"] == "production"
    host = "https://demandapi.booking.com/3.2" if production else "https://demandapi-sandbox.booking.com/3.2"
    headers = {"Authorization": f"Bearer {config['BOOKING_API_TOKEN']}", "X-Affiliate-Id": config["BOOKING_AFFILIATE_ID"]}
    guests = {"number_of_adults": adults, "number_of_rooms": 1,
              "allocation": [{"number_of_adults": adults, "children": children}], "children": children}
    payload = {"booker": {"country": "kr", "platform": "desktop"}, "checkin": checkin.isoformat(),
               "checkout": checkout.isoformat(), "currency": "KRW", "guests": guests,
               "rows": 10, "sort": {"by": "price", "direction": "ascending"}, "extras": ["extra_charges", "products"]}
    if region in CENTERS:
        city, lat, lon = CENTERS[region]
        payload["coordinates"] = {"latitude": lat, "longitude": lon, "radius": 10}
        area = f"{city} 대표 지점 반경 10km"
    else:
        payload["country"] = "kr"
        area = "대한민국"
    try:
        data = request_json("POST", host + "/accommodations/search", headers=headers, json=payload)
        offers = data.get("data", [])
        if not isinstance(offers, list):
            raise ProviderError("가격 응답 형식을 확인할 수 없습니다.")
        details = {}
        warning = ""
        if offers:
            try:
                info = request_json("POST", host + "/accommodations/details", headers=headers,
                                    json={"accommodations": [o["id"] for o in offers], "languages": ["ko", "en-gb"]})
                details = {o["id"]: o for o in info.get("data", [])}
            except (ProviderError, KeyError, TypeError):
                warning = "숙소명 상세 조회가 실패하여 일부 이름은 숙소 ID로 표시됩니다."
        items = []
        fetched = now()
        for offer in offers:
            price = offer.get("price", {}).get("total", {})
            amount = price.get("booker_currency")
            currency = offer.get("currency", {}).get("booker")
            try:
                valid_amount = Decimal(str(amount))
                if not valid_amount.is_finite() or valid_amount < 0 or currency != "KRW":
                    continue
            except (InvalidOperation, ValueError):
                continue
            detail = details.get(offer["id"], {})
            name = detail.get("name") or {}
            if isinstance(name, dict):
                name = name.get("ko") or name.get("en-gb") or next(iter(name.values()), "")
            items.append({"id": offer["id"], "name": str(name or f"숙소 ID {offer['id']}"),
                          "total": str(valid_amount), "currency": currency,
                          "url": safe_link(offer.get("url"), ["booking.com"]),
                          "operating_status": detail.get("accommodation_status", "미제공"),
                          "fetched_at": fetched})
        return {"status": "live" if production else "sandbox", "items": items, "area": area,
                "checkin": checkin.isoformat(), "checkout": checkout.isoformat(), "adults": adults,
                "children": children, "rooms": 1, "fetched_at": fetched,
                "message": ("실제 판매 가격" if production else "테스트 환경의 가격 · 실제 판매 가격 아님")
                + " · 전체 숙박 기간·1객실 합계. 예약 시 최종 요금·취소 조건을 다시 확인하세요. " + warning,
                "has_more": bool(data.get("metadata", {}).get("next_page"))}
    except (ProviderError, KeyError, TypeError, AttributeError) as exc:
        return {"status": "unavailable", "items": [], "message": str(exc) if isinstance(exc, ProviderError) else "가격 응답을 해석하지 못했습니다."}
