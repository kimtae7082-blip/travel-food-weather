# 여행 한곳

HTML·CSS·JavaScript + FastAPI(Python) + SQLite(SQL)로 만든 국내 여행 검색 사이트입니다.

## 현재 연결 방식

| 기능 | 서비스 | 필요한 것 | 제공 범위 |
| --- | --- | --- | --- |
| 현재 날씨 | OpenWeather Current Weather API | 무료 계정 API 키 | 선택 시·도의 대표 도시 현재 날씨 |
| 숙소·풍경·음식점 | 한국관광공사 TourAPI | 공공데이터포털 활용 신청·인증키 | 공사에 등록된 관광정보 |
| 숙소 가격·예약 | 아고다 웹사이트 열기 | API 키·제휴 승인 불필요 | 숙소명 복사 후 아고다에서 직접 검색 |

OpenAI API는 사용하지 않습니다. 기존 카카오·Open-Meteo·Booking.com API는 호출하지 않습니다.
아고다 API를 사용하는 것이 아니라 공식 웹사이트로 이동하는 일반 링크입니다. 자동 가격 비교·객실 조회·예약·결제 기능은 아닙니다.

## 1. API 키 준비

### 날씨

1. [OpenWeather](https://home.openweathermap.org/users/sign_up)에 가입하고 이메일 인증·기본 날씨 API 키 활성화를 완료합니다.
2. 기본 **Current Weather API**를 사용합니다. One Call 구독은 이 코드에 필요하지 않습니다.
3. `.env`의 `OPENWEATHER_API_KEY=` 오른쪽에 키를 저장합니다.

[공식 요금 안내](https://openweathermap.org/price)는 기본 무료 날씨 서비스를 안내합니다. 계정의 실제 적용 상품·호출 한도를 확인하세요. 이 작업에서는 유료 상품 가입이나 결제를 하지 않았습니다.

### 장소·숙소 목록

1. [공공데이터포털의 한국관광공사_국문 관광정보 서비스_GW](https://www.data.go.kr/data/15101578/openapi.do)에서 활용 신청합니다.
2. 발급받은 인증키를 `.env`의 `TOUR_API_KEY=` 오른쪽에 저장합니다. Decoding 키를 권장하며 Encoding 키도 한 번 해제하여 요청합니다.
3. 국문 관광정보 서비스의 활용 승인 상태·허용 요청량을 확인합니다.

공식 페이지 기준 비용은 무료이며 개발단계는 자동승인, 운영단계는 심의승인입니다. 등록 정보가 모든 업체를 포함하거나 현재 영업을 보증하지는 않습니다.

`.env` 형식:

```dotenv
OPENWEATHER_API_KEY=
TOUR_API_KEY=
```

키는 채팅·HTML·JavaScript·GitHub에 넣지 않습니다. `.env`는 Git에서 제외하고 웹으로 제공하지 않습니다. 공유 가능한 양식은 `.env.example`입니다.
새 환경에서는 `.env.example`을 `.env`로 복사하세요. 기존 `.env`에는 새 항목만 추가했고 예전 키 값은 지우지 않았습니다. 예전 카카오·Booking 키는 현재 코드에서 사용하지 않으므로 필요 없다면 직접 제거할 수 있습니다.
시스템 환경변수가 있으면 `.env`보다 우선합니다. 설정 파일은 요청마다 다시 읽으므로 저장 후 다음 검색부터 적용됩니다. 잘못된 키를 등록해도 연결 성공으로 표시하지 않습니다.

## 2. 실행 (Windows / VS Code PowerShell)

이 폴더를 VS Code로 열고 터미널에서 한 줄씩 실행합니다. 이미 가상환경이 있다면 첫 명령은 생략합니다.

```powershell
python -m venv --without-pip .venv
python -m pip --python .venv install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001
```

브라우저: http://127.0.0.1:8001

기존 서버가 실행 중이라면 해당 터미널에서 Ctrl+C 후 새 코드로 다시 실행하세요. 포트 사용 중 오류가 나면 기존 서버를 확인하거나 8002처럼 다른 번호를 사용합니다.
이번 코드 변경은 서버 재시작이 필요합니다. 이후 `.env` 값만 바꿀 때는 다시 시작할 필요가 없습니다.

정상 결과:

- 키가 없으면 OpenWeather/TourAPI 등록 안내가 나타납니다. 데이터를 임의 생성하거나 예시 업체로 자동 대체하지 않습니다.
- 유효한 OpenWeather 키가 있으면 온도·날씨 설명·데이터 기준 시각·조회 시각이 나타납니다.
- 유효한 TourAPI 키가 있으면 등록된 장소·주소·전화·데이터 ID가 나타납니다.
- 숙소 앱 연결에서는 검색어 복사 후 아고다를 열어 붙여넣습니다. 날짜·인원은 아고다에서 직접 입력합니다.
- 화면 확인만 필요하면 검색 데이터 메뉴에서 예시 모드를 선택할 수 있습니다.

## 3. 검색·정보 해석

- TourAPI는 `KorService2` 공식 명세의 `areaBasedList2`, `searchKeyword2`, `ldongCode2`를 사용합니다.
- 시·도 코드는 API의 최신 법정동 코드 목록에서 찾고 하루 동안 캐시합니다.
- 빈 키워드 검색은 관광지(12)·숙박(32)·음식점(39)을 구분합니다.
- 키워드 API에는 분류 필터 요청 항목이 없어 현재 응답 페이지의 관광타입으로 분류합니다. 결과가 적거나 없어도 다음 페이지에 해당 분류가 있을 수 있습니다. 전체 결과를 한 번에 수집하지 않습니다.
- 조회 시각, 제공기관 데이터 수정 시각, 최종 영업 확인일은 서로 다릅니다. 데이터 조회만으로 현재 영업을 확인했다고 표시하지 않습니다.
- 원문 링크는 데이터 제공기관의 공식 안내 페이지이며 개별 업체의 홈페이지가 아닙니다. 관광정보 ID를 상세 화면에 함께 표시합니다.
- 가족·개인 적합성, 맛, 청결, 편안함은 검증한 추천 점수가 아닙니다. 실제 검색 목록은 여행 유형별 적합성 순으로 정렬되지 않습니다.
- 날씨는 대표 도시 지점(강원=강릉, 경기=수원, 제주=서귀포 등) 기준입니다. 장소 검색어와 날씨 위치는 별도이며 여행일 예보가 아닙니다.
- OpenWeather `dt`는 데이터 계산 기준 시각이고 조회 시각과 구분합니다. 10분 동안 캐시하며 API 키 변경·삭제 시 다른 키의 이전 캐시를 쓰지 않습니다.
- 이미지는 직접 제작한 일러스트입니다. API에서 받은 사진은 라이선스 검수 없이 표시하지 않습니다.
- 아고다에서 직접 확인하기는 키 없는 외부 링크 방식입니다. 앱 설치·앱 자동 실행·검색어·날짜 자동 전달·제휴 수익 추적을 보장하지 않습니다.
- 기존 `/api/hotel-prices` 주소는 호환 안내만 반환하며 금액을 생성하지 않습니다. 현재 화면은 `/api/hotel-links`를 사용합니다.

## 4. 검사

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/live.js
```

검증 환경은 Windows의 Python 3.12.10입니다. Python 3.14.7에서는 직접 실행 검증하지 않았습니다. 외부 응답의 자동 검사는 모의 데이터로 수행합니다. 실제 인증 성공은 본인의 유효한 키가 필요합니다.

## 파일

- `main.py`: FastAPI 화면·검색·날씨·숙소 앱 연결 주소
- `providers.py`: OpenWeather·TourAPI·숙소 링크 처리
- `.env`: 비공개 API 키 / `.env.example`: 공유용 빈 양식
- `requirements.txt`: 설치할 구성 요소
- `schema.sql`, `travel.db`: 예시 데이터 구조와 자동 생성 DB
- `static/index.html`, `style.css`, `connections.css`, `live.js`: 현재 화면과 동작
- `static/app.js`: 최초 시제품의 이전 스크립트 (현재 HTML에서는 사용하지 않음)
- `static/landscape.svg`: 직접 제작한 일러스트
- `tests/`: 설정·검색·외부 연결·오류 처리 검사

## 공식 자료

- [OpenWeather Current Weather API](https://openweathermap.org/current)
- [OpenWeather 무료·유료 상품](https://openweathermap.org/price)
- [TourAPI 국문 관광정보 명세](https://www.data.go.kr/data/15101578/openapi.do)
- [아고다 공식 사이트](https://www.agoda.com/ko-kr/)
- [아고다 API 제휴 절차](https://developer.agoda.com/demand/docs/getting-started): API 가격 연동은 일반 링크와 달리 제휴·인증이 필요합니다.
