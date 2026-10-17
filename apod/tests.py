from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from .models import APODOverride

FAKE_NASA = {
    "date": "2024-01-15",
    "title": "Original Title",
    "explanation": "text",
    "media_type": "image",
    "url": "https://example.com/x.jpg",
}


class CacheTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("apod.services.fetch_apod_from_nasa", return_value=FAKE_NASA)
    def test_miss_then_hit_calls_nasa_once(self, fetch):
        url = "/api/apod/low-level/?date=2024-01-15"
        r1 = self.client.get(url)
        r2 = self.client.get(url)
        self.assertEqual(r1["X-Cache"], "MISS")
        self.assertEqual(r2["X-Cache"], "HIT")
        self.assertEqual(fetch.call_count, 1)

    @patch("apod.services.fetch_apod_from_nasa", return_value=FAKE_NASA)
    def test_uncached_always_calls_nasa(self, fetch):
        url = "/api/apod/uncached/?date=2024-01-15"
        self.client.get(url)
        self.client.get(url)
        self.assertEqual(fetch.call_count, 2)

    @patch("apod.services.fetch_apod_from_nasa", return_value=FAKE_NASA)
    def test_changing_source_invalidates_cache(self, fetch):
        url = "/api/apod/low-level/?date=2024-01-15"
        self.assertEqual(self.client.get(url).json()["title"], "Original Title")
        self.assertEqual(self.client.get(url)["X-Cache"], "HIT")
        APODOverride.objects.create(date="2024-01-15", title="Edited")
        r = self.client.get(url)
        self.assertEqual(r["X-Cache"], "MISS")
        self.assertEqual(r.json()["title"], "Edited")

    @patch("apod.services.fetch_apod_from_nasa", return_value=FAKE_NASA)
    def test_deleting_override_invalidates_cache(self, fetch):
        obj = APODOverride.objects.create(date="2024-01-15", title="Edited")
        url = "/api/apod/low-level/?date=2024-01-15"
        self.client.get(url)
        obj.delete()
        r = self.client.get(url)
        self.assertEqual(r["X-Cache"], "MISS")
        self.assertEqual(r.json()["title"], "Original Title")

    @patch("apod.services.fetch_apod_from_nasa", return_value=FAKE_NASA)
    def test_manual_invalidate_endpoint(self, fetch):
        url = "/api/apod/low-level/?date=2024-01-15"
        self.client.get(url)
        self.client.post("/api/cache/invalidate/?date=2024-01-15")
        self.assertEqual(self.client.get(url)["X-Cache"], "MISS")

    @patch("apod.services.fetch_apod_from_nasa", return_value=FAKE_NASA)
    def test_page_cache_labels_miss_then_hit(self, fetch):
        url = "/api/apod/page-cached/?date=2024-01-15"
        self.assertEqual(self.client.get(url)["X-Cache"], "MISS")
        self.assertEqual(self.client.get(url)["X-Cache"], "HIT")
        self.assertEqual(fetch.call_count, 1)

    @patch("apod.services.fetch_apod_from_nasa", return_value=FAKE_NASA)
    def test_override_clears_page_cache_too(self, fetch):
        url = "/api/apod/page-cached/?date=2024-01-15"
        self.client.get(url)
        self.client.get(url)
        APODOverride.objects.create(date="2024-01-15", title="Edited")
        r = self.client.get(url)
        self.assertEqual(r["X-Cache"], "MISS")
        self.assertEqual(r.json()["title"], "Edited")

    def test_dashboard_loads(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "APOD Cache Lab")

    @override_settings(USE_MOCK_NASA=True, MOCK_NASA_LATENCY=0)
    def test_mock_mode_never_calls_requests(self):
        with patch("apod.services.requests.get") as http:
            r = self.client.get("/api/apod/low-level/?date=2024-01-15")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["title"], "Mock APOD for 2024-01-15")
        http.assert_not_called()

    def test_bad_date_rejected(self):
        r = self.client.get("/api/apod/low-level/?date=not-a-date")
        self.assertEqual(r.status_code, 400)

    @patch("apod.services.fetch_apod_from_nasa", return_value=FAKE_NASA)
    def test_stats_count_hits_and_misses(self, fetch):
        url = "/api/apod/low-level/?date=2024-01-15"
        self.client.get(url)
        self.client.get(url)
        self.client.get(url)
        stats = self.client.get("/api/cache/stats/").json()
        self.assertEqual(stats["hits"], 2)
        self.assertEqual(stats["misses"], 1)

    @patch("apod.services.fetch_apod_from_nasa", return_value=FAKE_NASA)
    def test_errors_are_not_cached(self, fetch):
        from .services import NasaError

        fetch.side_effect = NasaError("boom")
        url = "/api/apod/low-level/?date=2024-01-15"
        self.assertEqual(self.client.get(url).status_code, 502)
        fetch.side_effect = None
        fetch.return_value = FAKE_NASA
        self.assertEqual(self.client.get(url)["X-Cache"], "MISS")
