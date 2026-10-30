"""OpenWeather 현재 날씨, 한국관광공사 TourAPI, API 없는 숙소 앱 연결."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
import hashlib
import math
import os
from pathlib import Path
from time import monotonic
from urllib.parse import urlparse, unquote

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
CENTERS = {
    '서울': ('서울',37.5665,126.9780), '부산': ('부산',35.1796,129.0756),
    '대구': ('대구',35.8714,128.6014), '인천': ('인천',37.4563,126.7052),
    '광주': ('광주',35.1595,126.8526), '대전': ('대전',36.3504,127.3845),
    '울산': ('울산',35.5384,129.3114), '세종': ('세종',36.4800,127.2890),
    '경기': ('수원',37.2636,127.0286), '강원': ('강릉',37.7519,128.8761),
    '충북': ('단양',36.9845,128.3655), '충남': ('공주',36.4465,127.1190),
    '전북': ('전주',35.8242,127.1480), '전남': ('순천',34.9506,127.4872),
    '경북': ('경주',35.8562,129.2247), '경남': ('통영',34.8544,128.4332),
    '제주': ('서귀포',33.2541,126.5601),
}
REGION_NAMES = {
    '서울': ['서울특별시','서울'], '부산': ['부산광역시','부산'],
    '대구': ['대구광역시','대구'], '인천': ['인천광역시','인천'],
    '광주': ['광주광역시','광주'], '대전': ['대전광역시','대전'],
    '울산': ['울산광역시','울산'], '세종': ['세종특별자치시','세종시','세종'],
    '경기': ['경기도','경기'], '강원': ['강원특별자치도','강원도','강원'],
    '충북': ['충청북도','충북'], '충남': ['충청남도','충남'],
    '전북': ['전북특별자치도','전라북도','전북'], '전남': ['전라남도','전남'],
    '경북': ['경상북도','경북'], '경남': ['경상남도','경남'],
    '제주': ['제주특별자치도','제주도','제주'],
}
TOUR_BASE = 'https://apis.data.go.kr/B551011/KorService2'
TOUR_SOURCE = 'https://www.data.go.kr/data/15101578/openapi.do'
_weather_cache = {}
_region_cache = {}


def now():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')


def settings():
    keys = ('OPENWEATHER_API_KEY','TOUR_API_KEY')
    try:
        data = dotenv_values(ROOT/'.env',encoding='utf-8-sig',interpolate=False)
    except (OSError,UnicodeError):
        data = {}
    return {k:str((os.environ[k] if k in os.environ else data.get(k)) or '').strip() for k in keys}


def connection_status():
    config=settings()
    return {'places':'configured' if config['TOUR_API_KEY'] else 'needs_key',
            'weather':'configured' if config['OPENWEATHER_API_KEY'] else 'needs_key',
            'places_provider':'한국관광공사 TourAPI', 'weather_provider':'OpenWeather',
            'hotel_prices':'external_app', 'hotel_provider':'아고다', 'hotel_environment':None}


class ProviderError(Exception):
    pass


def request_json(method,url,**kwargs):
    try:
        with httpx.Client(timeout=15,follow_redirects=False) as client:
            response=client.request(method,url,**kwargs)
        if response.status_code in (401,403):
            raise ProviderError('API 키 또는 서비스 활용 승인 상태를 확인해 주세요.')
        if response.status_code==429:
            raise ProviderError('서비스 요청 한도를 초과했습니다. 잠시 후 다시 검색해 주세요.')
        response.raise_for_status()
        data=response.json()
        if not isinstance(data,dict):raise ValueError()
        return data
    except (httpx.HTTPError,ValueError):
        raise ProviderError('외부 서비스에 연결하지 못했어요. API 키와 네트워크를 확인해 주세요.') from None


def safe_link(value,domains):
    if not isinstance(value,str):return None
    parsed=urlparse(value)
    if parsed.scheme not in ('http','https') or not parsed.hostname:return None
    if any(parsed.hostname==host or parsed.hostname.endswith('.'+host) for host in domains):
        return value.replace('http://','https://',1)
    return None


def weather(region):
    base={'region':region,'temperature':None,'valid_at':None,'fetched_at':None,'issued_at':None,
          'source_url':'https://openweathermap.org/','provider':'OpenWeather'}
    if region not in CENTERS:
        return {**base,'status':'select_region','message':'날씨를 볼 지역을 선택해 주세요.'}
    city,lat,lon=CENTERS[region]
    base['city']=city
    key=settings()['OPENWEATHER_API_KEY']
    if not key:
        return {**base,'status':'needs_key','message':'.env의 OPENWEATHER_API_KEY에 발급받은 키를 저장해 주세요.'}
    cache_key=(region,hashlib.sha256(key.encode()).hexdigest())
    cached=_weather_cache.get(cache_key)
    if cached and monotonic()-cached[0]<600:return cached[1]
    try:
        data=request_json('GET','https://api.openweathermap.org/data/2.5/weather',params={
            'lat':lat,'lon':lon,'appid':key,'units':'metric','lang':'kr'})
        temp=data['main']['temp']
        if isinstance(temp,bool) or not isinstance(temp,(int,float)) or not math.isfinite(temp):raise ValueError()
        stamp=data['dt']
        valid=datetime.fromtimestamp(stamp,timezone(timedelta(hours=9))).isoformat(timespec='seconds')
        conditions=data.get('weather') or []
        description=conditions[0].get('description','상태 정보 미제공') if conditions else '상태 정보 미제공'
        result={**base,'status':'live','temperature':temp,'valid_at':valid,'fetched_at':now(),
                'message':description,'measurement':'OpenWeather 현재 날씨 데이터 · 여행일 예보 아님'}
        if len(_weather_cache)>100:_weather_cache.clear()
        _weather_cache[cache_key]=(monotonic(),result)
        return result
    except (ProviderError,KeyError,TypeError,ValueError,OverflowError,OSError) as exc:
        return {**base,'status':'unavailable','message':str(exc) if isinstance(exc,ProviderError) else '날씨 응답을 해석하지 못했습니다.'}


def tour_request(endpoint,key,**params):
    data=request_json('GET',f'{TOUR_BASE}/{endpoint}',params={
        'serviceKey':unquote(key),'MobileOS':'ETC','MobileApp':'TravelOne',
        '_type':'json','numOfRows':30,'pageNo':1,**params})
    response=data.get('response',data)
    header=response.get('header',{})
    if str(header.get('resultCode')) not in ('0000','00'):
        raise ProviderError('TourAPI 응답 오류입니다. 인증키·국문 관광정보 서비스 활용 승인·요청 한도를 확인해 주세요.')
    body=response.get('body',{})
    raw=body.get('items') or {}
    items=raw.get('item') or [] if isinstance(raw,dict) else []
    if isinstance(items,dict):items=[items]
    if not isinstance(items,list):raise ProviderError('TourAPI 목록 형식을 확인할 수 없습니다.')
    return items,int(body.get('totalCount',len(items)))


def region_code(region,key):
    if region=='전체':return None
    cache_key=hashlib.sha256(key.encode()).hexdigest()
    cached=_region_cache.get(cache_key)
    if not cached or monotonic()-cached[0]>86400:
        rows,_=tour_request('ldongCode2',key,numOfRows=100,lDongListYn='N')
        if len(_region_cache)>20:_region_cache.clear()
        _region_cache[cache_key]=(monotonic(),rows)
    else:rows=cached[1]
    for row in rows:
        if row.get('name',row.get('lDongRegnNm')) in REGION_NAMES[region]:
            code=row.get('code') or row.get('lDongRegnCd')
            if code:return str(code)
    raise ProviderError('선택한 지역의 TourAPI 법정동 코드를 찾지 못했습니다.')


def search_places(region,category,query,page):
    key=settings()['TOUR_API_KEY']
    if not key:
        return {'items':[],'total':0,'status':'needs_key','mode':'live','has_more':False,
                'message':'무료 TourAPI 활용 신청 후 .env의 TOUR_API_KEY에 인증키를 저장해 주세요.'}
    try:
        code=region_code(region,key)
    except (ProviderError,KeyError,TypeError,ValueError) as exc:
        return {'items':[],'total':0,'status':'unavailable','mode':'live','has_more':False,
                'message':str(exc) if isinstance(exc,ProviderError) else '지역 코드를 확인하지 못했습니다.'}
    common={'pageNo':page,'numOfRows':9,'arrange':'A'}
    if code:common['lDongRegnCd']=code
    type_ids={'scenery':'12','stay':'32','food':'39'}
    items=[];more=False;warnings=[];fetched=now()

    def fetch_one(kind):
        if query.strip():
            # 최신 키워드 검색 명세에는 contentTypeId가 없어 응답의 타입을 구분합니다.
            rows,total=tour_request('searchKeyword2',key,keyword=query.strip(),**common)
        else:
            rows,total=tour_request('areaBasedList2',key,contentTypeId=type_ids[kind],**common)
        output=[]
        for row in rows:
            actual_kind=next((k for k,v in type_ids.items() if str(row.get('contenttypeid'))==v),None)
            if actual_kind is None or (category!='all' and actual_kind!=category):continue
            name=row.get('title')
            ident=str(row.get('contentid',''))
            if not name or not ident.isdigit():continue
            address=' '.join(str(row.get(k) or '') for k in ('addr1','addr2')).strip()
            output.append({'id':f'tour-{ident}','content_id':ident,'region':region,'city':address or '주소 미제공',
                'name':name,'category':actual_kind,'audience':'both','description':'한국관광공사 등록 관광정보입니다. 방문 조건과 현재 운영 여부는 별도 확인이 필요합니다.',
                'tags':'공공 관광정보·여행 유형 적합성 미검증','address':address,'phone':row.get('tel') or '미제공',
                'provider':'한국관광공사 TourAPI','source_url':TOUR_SOURCE,'fetched_at':fetched,
                'provider_modified_at':row.get('modifiedtime') or None,'checked_at':None,
                'operating_status':'현재 영업 여부는 별도 확인 필요','is_demo':0})
        return output,page*9<total

    categories=[category] if category!='all' else ['scenery','stay','food']
    if query.strip():categories=['scenery']  # 하나의 통합 검색 응답을 서버에서 분류합니다.
    with ThreadPoolExecutor(max_workers=3) as executor:
        jobs=[executor.submit(fetch_one,k) for k in categories]
        for job in jobs:
            try:
                batch,has_more=job.result();items.extend(batch);more=more or has_more
            except (ProviderError,KeyError,TypeError,ValueError) as exc:
                warnings.append(str(exc) if isinstance(exc,ProviderError) else 'TourAPI 응답 형식을 확인할 수 없습니다.')
    return {'items':items,'total':len(items),'mode':'live','page':page,'has_more':more,
            'status':'partial' if warnings and items else 'unavailable' if warnings else 'live',
            'message':' / '.join(warnings) if warnings else '한국관광공사 등록 정보입니다. 전체 업체 목록·맛 평가·가족 적합성 순위가 아닙니다. 키워드 검색은 현재 페이지에서 분류하며 다음 결과도 확인해 주세요.',
            'fetched_at':fetched}


def hotel_app_links(region,query=''):
    city=CENTERS[region][0] if region in CENTERS else '대한민국'
    return {'status':'external_app','query':query.strip() or f'{city} 숙소',
            'links':[{'name':'아고다 열기','url':'https://www.agoda.com/ko-kr/'}],
            'message':'검색어를 복사한 뒤 아고다에서 검색해 주세요. 날짜·인원·가격은 아고다에서 직접 확인합니다. 자동 전송·가격 조회·예약·결제는 하지 않습니다.'}


def hotel_prices(region,checkin,checkout,adults,children):
    # 이전 API 주소도 오해 없이 안내합니다. 가격 숫자를 만들지 않습니다.
    return {'status':'external_app','items':[],**hotel_app_links(region)}
