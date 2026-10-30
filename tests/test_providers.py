"""외부 응답을 대체한 검사입니다. 실서비스 인증 검증과는 구분합니다."""
import unittest
from datetime import date
from unittest.mock import patch
import httpx
import providers
import os
import tempfile
from pathlib import Path

CONFIG={"KAKAO_REST_API_KEY":"test-only-secret", "BOOKING_API_TOKEN":"test-booking", "BOOKING_AFFILIATE_ID":"1", "BOOKING_ENV":"sandbox"}


class ProviderTests(unittest.TestCase):
    def setUp(self):
        providers._weather_cache.clear()

    def test_env_file_bom_quotes_and_no_expansion(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,".env").write_text('KAKAO_REST_API_KEY="fake-${UNCHANGED}-key"\nBOOKING_ENV=sandbox\n',encoding="utf-8-sig")
            with patch.object(providers,"ROOT",Path(folder)),patch.dict(os.environ,{},clear=True):
                result=providers.settings()
                self.assertEqual(result["KAKAO_REST_API_KEY"],"fake-${UNCHANGED}-key")
                self.assertNotIn("KAKAO_REST_API_KEY",os.environ)

    def test_env_reload_removal_and_system_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder,".env")
            with patch.object(providers,"ROOT",Path(folder)),patch.dict(os.environ,{},clear=True):
                path.write_text("KAKAO_REST_API_KEY=first\n",encoding="utf-8")
                self.assertEqual(providers.settings()["KAKAO_REST_API_KEY"],"first")
                path.write_text("KAKAO_REST_API_KEY=second\n",encoding="utf-8")
                self.assertEqual(providers.settings()["KAKAO_REST_API_KEY"],"second")
                with patch.dict(os.environ,{"KAKAO_REST_API_KEY":"system"}):
                    self.assertEqual(providers.settings()["KAKAO_REST_API_KEY"],"system")
                path.write_text("KAKAO_REST_API_KEY=\n",encoding="utf-8")
                self.assertEqual(providers.settings()["KAKAO_REST_API_KEY"],"")

    def test_missing_env_defaults_without_json_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,"settings.local.json").write_text('{"KAKAO_REST_API_KEY":"obsolete"}',encoding="utf-8")
            with patch.object(providers,"ROOT",Path(folder)),patch.dict(os.environ,{},clear=True):
                config=providers.settings()
        self.assertEqual(config["KAKAO_REST_API_KEY"],"")

    def test_public_status_never_contains_keys(self):
        with patch("providers.settings",return_value=CONFIG):
            result=providers.connection_status()
        self.assertEqual(result["places"],"configured")
        self.assertNotIn(CONFIG["KAKAO_REST_API_KEY"],str(result))
        self.assertNotIn(CONFIG["BOOKING_API_TOKEN"],str(result))

    def test_weather_zero_and_timestamp_and_cache(self):
        with patch("providers.request_json",return_value={"current":{"temperature_2m":0,"weather_code":0,"time":"2026-10-29T18:00"}}) as call:
            first=providers.weather("강원")
            second=providers.weather("강원")
        self.assertEqual(first["temperature"],0)
        self.assertEqual(first["city"],"강릉")
        self.assertEqual(first["valid_at"],"2026-10-29T18:00")
        self.assertIsNone(first["issued_at"])
        self.assertEqual(first,second)
        self.assertEqual(call.call_count,1)

    def test_weather_failure_and_all_region(self):
        with patch("providers.request_json",side_effect=providers.ProviderError("연결 실패")):
            failed=providers.weather("서울")
        self.assertEqual(failed["status"],"unavailable")
        self.assertIsNone(failed["temperature"])
        self.assertEqual(providers.weather("전체")["status"],"select_region")

    def test_kakao_source_not_operating_verification(self):
        response={"documents":[{"id":"123","place_name":"응답 테스트 식당","category_name":"음식점","address_name":"강원 강릉시", "place_url":"http://place.map.kakao.com/123","phone":""}],"meta":{"is_end":False}}
        with patch("providers.settings",return_value=CONFIG),patch("providers.request_json",return_value=response) as call:
            result=providers.search_places("강원","food","순두부",2)
        item=result["items"][0]
        self.assertEqual(result["status"],"live")
        self.assertEqual(item["is_demo"],0)
        self.assertIsNone(item["checked_at"])
        self.assertTrue(item["source_url"].startswith("https://place.map.kakao.com"))
        self.assertTrue(result["has_more"])
        self.assertEqual(call.call_args.kwargs["params"]["category_group_code"],"FD6")
        self.assertEqual(call.call_args.kwargs["params"]["page"],2)
        self.assertNotIn(CONFIG["KAKAO_REST_API_KEY"],str(result))

    def test_kakao_partial_outage(self):
        def request(method,url,**kwargs):
            if kwargs["params"]["category_group_code"]=="FD6":raise providers.ProviderError("연결 실패")
            return {"documents":[{"id":"1","place_name":"테스트","address_name":"서울"}],"meta":{"is_end":True}}
        with patch("providers.settings",return_value=CONFIG),patch("providers.request_json",side_effect=request):
            result=providers.search_places("서울","all","",1)
        self.assertEqual(result["status"],"partial")
        self.assertEqual(len(result["items"]),2)

    def test_hotel_sandbox_total_children_and_sanitized_link(self):
        calls=[]
        def request(method,url,**kwargs):
            calls.append((url,kwargs))
            if url.endswith('/search'):
                return {"data":[{"id":100,"currency":{"booker":"KRW"},"price":{"total":{"booker_currency":250000}},"url":"https://www.booking.com/hotel/kr/test.html"},
                                {"id":101,"currency":{"booker":"KRW"},"price":{"display":{"booker_currency":1}}}]}
            return {"data":[{"id":100,"name":{"ko":"모의 응답 숙소"},"accommodation_status":"open"}]}
        with patch("providers.settings",return_value=CONFIG),patch("providers.request_json",side_effect=request):
            result=providers.hotel_prices("강원",date(2027,1,1),date(2027,1,3),2,[5,10])
        self.assertEqual(result["status"],"sandbox")
        self.assertEqual(len(result["items"]),1)
        self.assertEqual(result["items"][0]["total"],"250000")
        self.assertEqual(result["items"][0]["name"],"모의 응답 숙소")
        payload=calls[0][1]["json"]
        self.assertEqual(payload["guests"]["allocation"][0]["children"],[5,10])
        self.assertEqual(payload["guests"]["number_of_rooms"],1)
        self.assertEqual(payload["coordinates"]["radius"],10)
        self.assertNotIn(CONFIG["BOOKING_API_TOKEN"],str(result))

    def test_booking_missing_keys_and_failed_service(self):
        with patch("providers.settings",return_value={**CONFIG,"BOOKING_API_TOKEN":""}):
            result=providers.hotel_prices("전체",date(2027,1,1),date(2027,1,2),1,[])
        self.assertEqual(result["status"],"needs_partner_access")
        with patch("providers.settings",return_value=CONFIG),patch("providers.request_json",side_effect=providers.ProviderError("연결 실패")):
            result=providers.hotel_prices("전체",date(2027,1,1),date(2027,1,2),1,[])
        self.assertEqual(result["status"],"unavailable")

    def test_safe_urls(self):
        self.assertIsNone(providers.safe_link("javascript:alert(1)",["booking.com"]))
        self.assertIsNone(providers.safe_link("https://booking.com.evil.example/",["booking.com"]))

    def test_http_errors_do_not_expose_auth_or_response(self):
        response=httpx.Response(401,request=httpx.Request("GET","https://example.com"),json={"error":"private"})
        with patch("providers.httpx.Client") as client:
            client.return_value.__enter__.return_value.request.return_value=response
            with self.assertRaises(providers.ProviderError) as raised:
                providers.request_json("GET","https://example.com",headers={"Authorization":"SECRET"})
        self.assertNotIn("SECRET",str(raised.exception))
        self.assertNotIn("private",str(raised.exception))


if __name__=='__main__':unittest.main()
