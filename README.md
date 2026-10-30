# 여행 한곳

가족·개인 여행의 숙소, 풍경·산책, 음식 탐방, 날씨를 한 화면에서 찾는 로컬 시제품입니다.
HTML/CSS/JavaScript + FastAPI + SQLite(SQL)를 사용합니다.

## 실제 서비스 연결 (업데이트)

현재 실행 화면은 **실제 검색 모드**로 시작합니다. API 키가 없으면 빈 결과와 등록 안내를 보여 주며 예시 업체로 몰래 대체하지 않습니다. 예시는 검색 데이터 메뉴에서 직접 선택할 수 있습니다.

| 기능 | 연결 상태 |
| --- | --- |
| 현재 날씨 | Open-Meteo 실제 API 연결. 대표 도시 모델 추정값·기준 시각·조회 시각 표시, 10분 캐시 |
| 숙소·풍경·음식점 | 카카오 로컬 연결 코드 완료. 사용자 REST API 키 필요. 실제 인증 응답은 미검증 |
| 날짜·인원별 숙박 가격 | Booking.com Demand API 3.2 연결 코드 완료. 제휴 승인·키·Affiliate ID 필요. 실제 인증 응답은 미검증 |
| 가격 테스트/실서비스 구분 | 기본값 sandbox. 테스트 가격은 실제 가격으로 표시하지 않음 |

### 첫 단계: 카카오 장소 검색 연결

1. [카카오 개발자 사이트](https://developers.kakao.com/)에서 사용할 앱의 **REST API 키**와 로컬 API 이용 권한을 준비합니다. JavaScript 키가 아닙니다. 계정·앱·이용 조건 동의는 본인이 진행해야 합니다.
2. 이 폴더의 `.env`를 VS Code에서 엽니다. 이번 수정에서 기존 JSON 설정을 옮겼습니다. 파일이 없는 새 환경에서는 `.env.example`을 복사해 `.env`라는 이름으로 저장합니다.
3. `KAKAO_REST_API_KEY=`의 오른쪽에 키를 저장합니다. 키는 채팅이나 HTML/JavaScript에 붙이지 마세요.
4. 업데이트된 서버가 실행된 상태에서 브라우저를 새로고침하고 실제 검색을 누릅니다.

정상 결과: 가상 업체가 아닌 장소명·주소·전화번호·카카오맵 출처가 나타납니다. 키 등록은 연결 성공과 다르며, 권한/한도 오류는 화면에서 확인합니다.

`.env`는 Git에서 제외되며 웹으로 제공하지 않습니다. 공유할 수 있는 양식은 `.env.example`입니다. 시스템 환경변수에 같은 이름이 있으면 빈 값까지 포함해 환경변수가 우선합니다. `.env`는 매 요청에 다시 읽으므로 키 변경·삭제는 다음 검색부터 반영됩니다. 파일 내용으로 시스템 환경변수를 변경하지 않습니다.

형식 예시 (발급받은 키는 `.env`에서 직접 입력):

```dotenv
KAKAO_REST_API_KEY=
BOOKING_API_TOKEN=
BOOKING_AFFILIATE_ID=
BOOKING_ENV=sandbox
```

`=` 왼쪽 이름은 그대로 두고 오른쪽 값만 바꿉니다. 값에 공백이나 `#`가 있다면 따옴표로 감쌉니다. `${...}` 자동 치환은 하지 않습니다. `.env`는 암호화된 파일이 아니므로 공유하지 않습니다. 이전 `settings.local.json`과 `settings.example.json`은 사용하지 않습니다.

### 다음 단계: 숙박 가격 연결

Booking.com 일반 회원 계정이나 일반 제휴 링크만으로는 API를 사용할 수 없습니다. **Demand API 사용 권한이 있는 제휴 계정**의 `BOOKING_API_TOKEN`과 `BOOKING_AFFILIATE_ID`가 필요합니다.

- 승인된 키를 `.env`의 해당 항목에 저장합니다.
- 테스트용 키는 `BOOKING_ENV`를 `sandbox`로 유지합니다. 테스트 데이터는 실제 판매 가격이 아닙니다.
- 실서비스 접근 권한과 키가 준비된 경우에만 `BOOKING_ENV`를 `production`으로 바꿉니다.
- 화면에서 지역·체크인·체크아웃·성인·아이 나이를 입력하고 **가격 조회**를 누릅니다. 아이가 없으면 빈칸으로 둡니다. 한 객실만 지원합니다.
- 표시 금액은 API의 **원화 전체 기간 총액**만 사용합니다. 금액이 없거나 통화가 다르면 임의 계산해 표시하지 않습니다.
- 날짜는 오늘 이후, 1~90박, 500일 이내여야 합니다. 현재 요금 요청의 거주국·기기 기준은 대한민국·데스크톱입니다.
- 검색 범위는 선택 시·도의 **대표 도시 지점 반경 10km**이며 시·도 전체가 아닙니다. `전체`는 대한민국 검색입니다. 장소 검색어는 가격 조회에 적용하지 않습니다.
- 카카오 숙소와 Booking.com 가격을 이름만으로 짝짓지 않습니다. 가격 결과는 별도 목록으로 표시합니다.
- 일부 결과만 조회하며 모든 숙소·모든 판매처 최저가를 보장하지 않습니다. 실제 예약은 판매 페이지에서 최종 금액·취소 조건을 확인합니다.

### 날씨의 의미와 이용 조건

날씨는 시·도 전체가 아니라 기본 검색 도시(강원=강릉, 경기=수원, 제주=서귀포 등)의 모델 기반 현재 추정값입니다. 검색어를 입력해도 날씨 지점은 변하지 않습니다. 여행 날짜의 예보나 기상청 관측 실측값이 아닙니다. 데이터 기준 시각과 조회 시각을 구분하고 실패 시 숫자를 생성하지 않습니다.

Open-Meteo 무료 API는 학습·비상업용으로 연결했습니다. 광고·구독 등 상업용으로 공개하기 전에 해당 서비스 요금제·이용 조건에 맞는 연결로 변경해야 합니다. 출처는 화면에 표시합니다. 외부 서비스 가입·결제·제휴 신청은 자동으로 수행하지 않았습니다.

공식 문서:
- [카카오 로컬 API](https://developers.kakao.com/docs/latest/ko/local/dev-guide)
- [Open-Meteo API](https://open-meteo.com/en/docs), [이용 조건](https://open-meteo.com/en/terms)
- [Booking.com 인증](https://developers.booking.com/demand/docs/development-guide/authentication), [3.2 숙소 검색](https://developers.booking.com/demand/docs/open-api/3.2/demand-api/accommodations/accommodations/search)

## 최초 버전의 기능과 데이터

- 전국 17개 시·도 선택, 가족/개인 유형 검색, 분류 탭, 도시·장소·태그 검색
- SQLite 데이터 검색, 결과 없음·서버 오류 안내, 상세 정보 창
- 모바일 화면 대응, 키보드 조작, 직접 제작한 SVG 일러스트
- 날씨 서비스 미연결 상태와 기상청 링크

## 예시 모드의 한계

- 실제 식당·숙소 검색, 영업 상태·최신 후기, 가격·빈방·예약
- 여행일 예보: 현재는 모델 기반 현재 날씨만 연결했습니다.
- 명소 현재 운영·이용 조건 검증, 업체별 출처와 최종 확인일

식당·숙소는 모두 가상 업체입니다. 명소는 실제 명칭을 사용한 예시이며 현재 이용 조건은 미확인입니다.
가족·개인 구분은 화면 동작 예시이며 검증된 추천 등급이 아닙니다.
사진 대신 직접 제작한 일러스트를 사용했습니다. 실제 사진은 이용 허락과 개인정보 검수 후 추가해야 합니다.
여행 날짜·인원은 별도 가격 조회 폼에서 입력합니다. 예산 필터는 현재 제공하지 않습니다.

## 실행 (Windows PowerShell / VS Code 터미널)

1. VS Code에서 이 폴더를 열고 터미널을 엽니다.
2. 최초 설치 시 다음 명령을 한 줄씩 실행합니다.

```powershell
python -m venv --without-pip .venv
python -m pip --python .venv install -r requirements.txt
```

가상환경이 이미 있다면 첫 명령은 생략합니다. 이번 업데이트에서는 `.env`를 읽는 `python-dotenv`를 추가했으므로 기존 사용자도 아래 설치 명령을 한 번 실행합니다. 현재 작업 환경에는 설치를 완료했습니다.

```powershell
python -m pip --python .venv install -r requirements.txt
```

3. 서버를 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

4. 브라우저에서 http://127.0.0.1:8000 을 엽니다.
정상 결과: ‘여행 한곳’ 화면에 실제 날씨와 장소 검색 키 등록 상태가 나타납니다.
키가 없다면 장소 결과는 비어 있습니다. 예시 모드를 선택하면 강원 가족여행 예시 3곳이 나타납니다.
8000번이 사용 중이면 명령의 포트를 8001로 바꾸고 http://127.0.0.1:8001 을 엽니다.
이미 실행된 서버에는 Python 변경이 자동 반영되지 않습니다. 기존 터미널에서 Ctrl+C 후 다시 실행하세요.
이번 `.env` 전환 코드도 서버를 한 번 재시작해야 적용됩니다. 이후 `.env`의 키 값만 수정할 때는 다시 시작할 필요가 없습니다.
중지: 실행 중인 터미널에서 Ctrl+C.

## 확인

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check static/app.js
node --check static/live.js
```

실행 환경은 Windows의 Python 3.12.10입니다. Python 3.14.7에서는 직접 실행 검증하지 않았습니다.
SQL 문법은 Python 기본 sqlite3 모듈을 사용합니다. 의존성 버전은 requirements.txt에 고정했습니다.

## 파일

- main.py: 검색 API와 데이터베이스 초기화
- providers.py: 실제 날씨·장소·숙박 가격 API 연결
- .env: 사용자 키 저장 (웹 비공개·Git 제외)
- .env.example: 키가 없는 공유용 설정 양식
- schema.sql: 저장할 정보의 구조
- static/index.html, style.css, connections.css, live.js: 현재 화면과 검색 동작
- static/app.js: 최초 시제품의 이전 스크립트 (현재 HTML에서 사용하지 않음)
- static/landscape.svg: 직접 제작한 일러스트
- travel.db: 첫 실행 시 자동 생성되는 예시 데이터베이스
- tests/test_app.py: 필터·입력 검증·미연결 상태 확인
- tests/test_providers.py: 모의 외부 응답을 이용한 연결·가격·오류 처리 검사

FastAPI 구현 참고: https://fastapi.tiangolo.com/tutorial/static-files/ 및 https://fastapi.tiangolo.com/tutorial/query-params/

설정 파일 처리 참고: https://bbc2.github.io/python-dotenv/
