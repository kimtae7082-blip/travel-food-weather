"""여행 한곳: HTML/CSS/JS + FastAPI + SQLite로 만든 로컬 시제품."""
from contextlib import asynccontextmanager, closing
from pathlib import Path
import sqlite3
from typing import Literal
from datetime import date, datetime, timezone, timedelta

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import providers

ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / "travel.db"
REGIONS = [
    ("서울", "성동", "서울숲", "공원·도심 산책"),
    ("부산", "수영", "광안리", "바다·야경"),
    ("대구", "중구", "근대골목", "골목·건축"),
    ("인천", "송도", "센트럴파크", "수변·도시 풍경"),
    ("광주", "양림동", "양림역사문화마을", "골목·문화"),
    ("대전", "서구", "한밭수목원", "정원·산책"),
    ("울산", "동구", "대왕암공원", "해안·숲"),
    ("세종", "세종", "세종호수공원", "호수·산책"),
    ("경기", "수원", "수원화성", "성곽·역사"),
    ("강원", "강릉", "경포호", "호수·바다"),
    ("충북", "단양", "도담삼봉", "강·풍경"),
    ("충남", "공주", "공산성", "역사·강"),
    ("전북", "전주", "전주한옥마을", "한옥·골목"),
    ("전남", "순천", "순천만국가정원", "정원·자연"),
    ("경북", "경주", "동궁과 월지", "역사·야경"),
    ("경남", "통영", "강구안", "항구·풍경"),
    ("제주", "서귀포", "서귀포 치유의 숲", "숲·휴식"),
]


def initialize_database():
    with closing(sqlite3.connect(DATABASE)) as connection, connection:
        connection.executescript((ROOT / "schema.sql").read_text(encoding="utf-8"))
        if connection.execute("SELECT COUNT(*) FROM places").fetchone()[0]:
            return
        rows = []
        for region, city, scenery, theme in REGIONS:
            rows.extend([
                (region, city, scenery, "scenery", "both",
                 f"{city}의 풍경 탐방 후보입니다. 여행 테마: {theme}. 보행 편의와 현재 이용 조건은 확인이 필요합니다.",
                 theme + "·이용 조건 미확인"),
                (region, city, f"{city} 가족 숙소 예시", "stay", "family",
                 "실제 업체가 아닌 화면 구성용 가상 숙소입니다. 가족 객실·주차·침대 구성을 비교하는 자리입니다.",
                 "가상 업체·가족 객실 비교·가격 미연결"),
                (region, city, f"{city} 1인 숙소 예시", "stay", "solo",
                 "실제 업체가 아닌 화면 구성용 가상 숙소입니다. 1인 총결제액·개별 욕실·교통 동선을 비교하는 자리입니다.",
                 "가상 업체·1인 객실 비교·가격 미연결"),
                (region, city, f"{city} 음식 탐방 예시", "food", "both",
                 "실제 업체가 아닌 화면 구성용 가상 식당입니다. 메뉴·1인 주문·유아 의자 정보를 연결할 자리입니다.",
                 "가상 업체·영업 미확인·메뉴 연결 예정"),
            ])
        connection.executemany(
            "INSERT INTO places(region,city,name,category,audience,description,tags) VALUES(?,?,?,?,?,?,?)", rows
        )


@asynccontextmanager
async def lifespan(app):
    initialize_database()
    yield


app = FastAPI(title="여행 한곳", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(ROOT / "static" / "index.html")


@app.get("/api/regions")
def regions():
    return {"regions": [r[0] for r in REGIONS]}


@app.get("/api/places")
def places(
    region: str = Query(default="전체", max_length=20),
    audience: Literal["family", "solo"] = "family",
    category: Literal["all", "stay", "scenery", "food"] = "all",
    q: str = Query(default="", max_length=100),
    mode: Literal["live", "demo"] = "live",
    page: int = Query(default=1, ge=1, le=45),
):
    if region != "전체" and region not in providers.CENTERS:
        raise HTTPException(422, "지원하는 지역을 선택해 주세요.")
    if mode == "live":
        return providers.search_places(region, category, q, page)
    clauses, parameters = ["audience IN (?, 'both')"], [audience]
    if region != "전체":
        clauses.append("region = ?")
        parameters.append(region)
    if category != "all":
        clauses.append("category = ?")
        parameters.append(category)
    if q.strip():
        clauses.append("(instr(name, ?) > 0 OR instr(city, ?) > 0 OR instr(tags, ?) > 0)")
        parameters.extend([q.strip()] * 3)
    with closing(sqlite3.connect(DATABASE)) as connection:
        connection.row_factory = sqlite3.Row
        result = connection.execute(
            "SELECT * FROM places WHERE " + " AND ".join(clauses)
            + " ORDER BY CASE category WHEN 'scenery' THEN 0 WHEN 'stay' THEN 1 ELSE 2 END, id",
            parameters,
        ).fetchall()
    return {"items": [dict(row) for row in result], "total": len(result), "mode": "demo", "status": "demo", "has_more": False,
            "message": "화면 확인용 예시 데이터입니다. 실제 업체 검색이 아닙니다."}


@app.get("/api/weather")
def weather(region: str = Query(default="강원", max_length=20)):
    if region != "전체" and region not in providers.CENTERS:
        raise HTTPException(422, "지원하는 지역을 선택해 주세요.")
    return providers.weather(region)


@app.get("/api/status")
def status():
    return providers.connection_status()


@app.get("/api/hotel-links")
def hotel_links(region: str = Query(default="강원", max_length=20), q: str = Query(default="", max_length=100)):
    if region != "전체" and region not in providers.CENTERS:
        raise HTTPException(422, "지원하는 지역을 선택해 주세요.")
    return providers.hotel_app_links(region, q)


@app.get("/api/hotel-prices")
def hotel_prices(
    checkin: date, checkout: date,
    region: str = Query(default="강원", max_length=20),
    adults: int = Query(default=2, ge=1, le=8),
    children: str = Query(default="", max_length=40),
):
    today = datetime.now(timezone(timedelta(hours=9))).date()
    if region != "전체" and region not in providers.CENTERS:
        raise HTTPException(422, "지원하는 지역을 선택해 주세요.")
    if checkin < today or checkout <= checkin or (checkout-checkin).days > 90 or (checkout-today).days > 500:
        raise HTTPException(422, "오늘 이후 체크인, 1~90박, 500일 이내 체크아웃 날짜를 선택해 주세요.")
    try:
        ages = [int(age.strip()) for age in children.split(",")] if children.strip() else []
        if len(ages) > 6 or any(age < 0 or age > 17 for age in ages):
            raise ValueError()
    except ValueError:
        raise HTTPException(422, "아이 나이는 0~17세를 쉼표로 구분해 최대 6명까지 입력해 주세요.") from None
    return providers.hotel_prices(region, checkin, checkout, adults, ages)
