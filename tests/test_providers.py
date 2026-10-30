"""외부 서비스는 모의 응답으로 검사합니다. 실제 인증 성공 검증은 별도입니다."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import httpx
import providers

CONFIG={'OPENWEATHER_API_KEY':'fake-weather-key','TOUR_API_KEY':'fake-tour-key'}


def tour_body(rows,total=None):
    return {'response':{'header':{'resultCode':'0000'},'body':{'items':{'item':rows},'totalCount':len(rows) if total is None else total}}}


def row(kind='12',ident='123'):
    return {'contentid':ident,'contenttypeid':kind,'title':'모의 장소','addr1':'강원특별자치도 강릉시','modifiedtime':'20261029120000'}


class ProviderTests(unittest.TestCase):
    def setUp(self):
        providers._weather_cache.clear()
        providers._region_cache.clear()

    def test_env_file_bom_quotes_and_no_expansion(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'.env').write_text('TOUR_API_KEY="fake-${UNCHANGED}-key"\n',encoding='utf-8-sig')
            with patch.object(providers,'ROOT',Path(folder)),patch.dict(os.environ,{},clear=True):
                self.assertEqual(providers.settings()['TOUR_API_KEY'],'fake-${UNCHANGED}-key')
                self.assertNotIn('TOUR_API_KEY',os.environ)

    def test_env_reload_clear_and_system_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder,'.env')
            with patch.object(providers,'ROOT',Path(folder)),patch.dict(os.environ,{},clear=True):
                for value in ('first','second',''):
                    path.write_text('TOUR_API_KEY='+value+'\n',encoding='utf-8')
                    self.assertEqual(providers.settings()['TOUR_API_KEY'],value)
                with patch.dict(os.environ,{'TOUR_API_KEY':'system'}):
                    self.assertEqual(providers.settings()['TOUR_API_KEY'],'system')

    def test_old_keys_not_used_and_status_no_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'.env').write_text('KAKAO_REST_API_KEY=obsolete\nBOOKING_API_TOKEN=old\n',encoding='utf-8')
            with patch.object(providers,'ROOT',Path(folder)),patch.dict(os.environ,{},clear=True):
                self.assertEqual(providers.settings(),{'OPENWEATHER_API_KEY':'','TOUR_API_KEY':''})
        with patch('providers.settings',return_value=CONFIG):
            status=providers.connection_status()
        self.assertEqual(status['hotel_prices'],'external_app')
        for value in CONFIG.values():self.assertNotIn(value,str(status))

    def test_weather_units_zero_time_and_cache(self):
        sample={'main':{'temp':0},'dt':1793264400,'weather':[{'description':'맑음'}]}
        with patch('providers.settings',return_value=CONFIG),patch('providers.request_json',return_value=sample) as request:
            first=providers.weather('강원');second=providers.weather('강원')
        self.assertEqual(first['temperature'],0)
        self.assertEqual(first['city'],'강릉')
        self.assertTrue(first['valid_at'].endswith('+09:00'))
        self.assertEqual(first,second)
        self.assertIsNone(first['issued_at'])
        self.assertEqual(request.call_count,1)
        self.assertEqual(request.call_args.kwargs['params']['units'],'metric')
        self.assertEqual(request.call_args.kwargs['params']['lang'],'kr')
        self.assertIn('/data/2.5/weather',request.call_args.args[1])
        self.assertNotIn(CONFIG['OPENWEATHER_API_KEY'],str(first))

    def test_weather_key_change_does_not_reuse_cached_result(self):
        sample={'main':{'temp':10},'dt':1793264400}
        with patch('providers.request_json',return_value=sample) as request:
            for key in ('one','two'):
                with patch('providers.settings',return_value={**CONFIG,'OPENWEATHER_API_KEY':key}):providers.weather('서울')
        self.assertEqual(request.call_count,2)
        with patch('providers.settings',return_value={**CONFIG,'OPENWEATHER_API_KEY':''}):
            self.assertEqual(providers.weather('서울')['status'],'needs_key')

    def test_weather_missing_key_invalid_response_and_failure(self):
        with patch('providers.settings',return_value={'OPENWEATHER_API_KEY':''}),patch('providers.request_json') as request:
            result=providers.weather('부산')
            self.assertEqual(result['status'],'needs_key');request.assert_not_called()
        for response in ({'main':{'temp':float('nan')},'dt':1},{'main':{'temp':True},'dt':1},{'main':{}}):
            with patch('providers.settings',return_value=CONFIG),patch('providers.request_json',return_value=response):
                self.assertEqual(providers.weather('부산')['status'],'unavailable')
        with patch('providers.settings',return_value=CONFIG),patch('providers.request_json',side_effect=providers.ProviderError('연결 실패')):
            self.assertIsNone(providers.weather('부산')['temperature'])
        self.assertEqual(providers.weather('전체')['status'],'select_region')

    def test_tour_decoded_key_singleton_empty_and_error(self):
        with patch('providers.request_json',return_value=tour_body(row(),1)) as request:
            records,total=providers.tour_request('areaBasedList2','abc%2Bdef%3D')
        self.assertEqual(len(records),1)
        self.assertEqual(total,1)
        self.assertEqual(request.call_args.kwargs['params']['serviceKey'],'abc+def=')
        with patch('providers.request_json',return_value={'response':{'header':{'resultCode':'0000'},'body':{'items':'','totalCount':0}}}):
            self.assertEqual(providers.tour_request('areaBasedList2','key'),([],0))
        with patch('providers.request_json',return_value={'response':{'header':{'resultCode':'30','resultMsg':'private-key'}}}):
            with self.assertRaises(providers.ProviderError) as raised:providers.tour_request('areaBasedList2','key')
            self.assertNotIn('private-key',str(raised.exception))

    def test_tour_discovers_current_region_code_and_filters(self):
        calls=[]
        def request(method,url,**kwargs):
            params=kwargs['params'];calls.append((url,params))
            if url.endswith('/ldongCode2'):return tour_body([{'code':'51','name':'강원특별자치도'}])
            return tour_body([row('32')],20)
        with patch('providers.settings',return_value=CONFIG),patch('providers.request_json',side_effect=request):
            result=providers.search_places('강원','stay','',2)
        self.assertEqual(result['status'],'live')
        self.assertTrue(result['has_more'])
        self.assertEqual(calls[1][1]['lDongRegnCd'],'51')
        self.assertEqual(calls[1][1]['contentTypeId'],'32')
        item=result['items'][0]
        self.assertEqual(item['category'],'stay')
        self.assertEqual(item['content_id'],'123')
        self.assertEqual(item['is_demo'],0)
        self.assertIsNone(item['checked_at'])
        self.assertEqual(item['provider_modified_at'],'20261029120000')
        self.assertNotIn(CONFIG['TOUR_API_KEY'],str(result))

    def test_keyword_search_one_call_and_local_category_filter(self):
        with patch('providers.settings',return_value=CONFIG),patch('providers.request_json',return_value=tour_body([row('12','1'),row('32','2'),row('39','3'),row('14','4')],40)) as request:
            result=providers.search_places('전체','food','한옥',1)
        self.assertEqual(request.call_count,1)
        self.assertTrue(request.call_args.args[1].endswith('/searchKeyword2'))
        self.assertNotIn('contentTypeId',request.call_args.kwargs['params'])
        self.assertEqual([p['category'] for p in result['items']],['food'])
        self.assertTrue(result['has_more'])

    def test_tour_partial_failure(self):
        def request(method,url,**kwargs):
            kind=kwargs['params'].get('contentTypeId')
            if kind=='39':raise providers.ProviderError('연결 실패')
            return tour_body([row(kind,kind)])
        with patch('providers.settings',return_value=CONFIG),patch('providers.request_json',side_effect=request):
            result=providers.search_places('전체','all','',1)
        self.assertEqual(result['status'],'partial')
        self.assertEqual(len(result['items']),2)

    def test_no_tour_key_no_demo_and_no_request(self):
        with patch('providers.settings',return_value={'TOUR_API_KEY':''}),patch('providers.request_json') as request:
            result=providers.search_places('전체','all','',1)
        self.assertEqual(result['status'],'needs_key');self.assertEqual(result['items'],[]);request.assert_not_called()

    def test_lodging_app_links_need_no_keys_or_external_request(self):
        with patch('providers.settings',side_effect=AssertionError('must not use credentials')),patch('providers.request_json') as request:
            result=providers.hotel_app_links('강원')
        request.assert_not_called()
        self.assertEqual(result['query'],'강릉 숙소')
        self.assertEqual(result['links'][0]['url'],'https://www.agoda.com/ko-kr/')
        self.assertEqual(result['status'],'external_app')
        self.assertNotIn('price',result)
        self.assertEqual(providers.hotel_app_links('전체','특정 숙소')['query'],'특정 숙소')

    def test_safe_links(self):
        self.assertIsNone(providers.safe_link('javascript:alert(1)',['booking.com']))
        self.assertIsNone(providers.safe_link('https://booking.com.evil.example/',['booking.com']))

    def test_http_error_does_not_expose_key(self):
        response=httpx.Response(401,request=httpx.Request('GET','https://example.com?appid=SECRET'),json={'error':'private'})
        with patch('providers.httpx.Client') as client:
            client.return_value.__enter__.return_value.request.return_value=response
            with self.assertRaises(providers.ProviderError) as raised:providers.request_json('GET','https://example.com')
        self.assertNotIn('SECRET',str(raised.exception));self.assertNotIn('private',str(raised.exception))


if __name__=='__main__':unittest.main()
