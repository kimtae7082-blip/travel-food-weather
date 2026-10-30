import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
import main
from unittest.mock import patch


class TravelTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous = main.DATABASE
        main.DATABASE = Path(self.directory.name) / "test.db"
        self.context = TestClient(main.app)
        self.client = self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)
        main.DATABASE = self.previous
        self.directory.cleanup()

    def test_home_and_regions(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("여행 한곳", response.text)
        self.assertEqual(len(self.client.get("/api/regions").json()["regions"]), 17)
        for path in ["/.env", "/.env.example", "/settings.local.json", "/static/../.env"]:
            self.assertEqual(self.client.get(path).status_code,404)

    def test_family_and_solo_filter(self):
        for audience in ["family", "solo"]:
            data = self.client.get("/api/places", params={"region":"강원", "audience":audience,"mode":"demo"}).json()
            self.assertEqual(data["total"], 3)
            self.assertTrue(all(p["region"] == "강원" for p in data["items"]))
            self.assertTrue(all(p["audience"] in [audience, "both"] for p in data["items"]))

    def test_search_category_empty_and_sql_input(self):
        data = self.client.get("/api/places", params={"category":"scenery", "q":"경포","mode":"demo"}).json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["name"], "경포호")
        for term in ["없는검색어", "' OR 1=1 --", "%"]:
            self.assertEqual(self.client.get("/api/places",params={"q":term,"mode":"demo"}).json()["total"],0)

    def test_invalid_and_honest_status(self):
        self.assertEqual(self.client.get("/api/places?category=wrong").status_code,422)
        self.assertEqual(self.client.get("/api/places?audience=wrong").status_code,422)
        with patch("providers.request_json", side_effect=main.providers.ProviderError("연결 실패")):
            main.providers._weather_cache.clear()
            weather = self.client.get("/api/weather?region=부산").json()
        self.assertEqual(weather["status"], "unavailable")
        self.assertIsNone(weather["temperature"])
        self.assertIsNone(weather["issued_at"])
        for item in self.client.get("/api/places?mode=demo").json()["items"]:
            self.assertEqual(item["is_demo"],1)
            self.assertIsNone(item["checked_at"])

    def test_live_missing_key_does_not_fall_back_to_demo(self):
        with patch("providers.settings", return_value={"KAKAO_REST_API_KEY":""}):
            data = self.client.get("/api/places").json()
        self.assertEqual(data["status"], "needs_key")
        self.assertEqual(data["items"], [])
        self.assertEqual(data["mode"], "live")

    def test_hotel_input_validation(self):
        for query in ["checkin=2020-01-01&checkout=2020-01-02", "checkin=bad&checkout=bad",
                      "checkin=2027-01-01&checkout=2027-01-01"]:
            self.assertEqual(self.client.get("/api/hotel-prices?"+query).status_code,422)
        from datetime import datetime, timedelta, timezone
        tomorrow = datetime.now(timezone(timedelta(hours=9))).date()+timedelta(days=1)
        params={"checkin":tomorrow.isoformat(),"checkout":(tomorrow+timedelta(days=1)).isoformat(),"children":"18"}
        self.assertEqual(self.client.get("/api/hotel-prices",params=params).status_code,422)


if __name__ == "__main__":
    unittest.main()
