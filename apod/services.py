import time
from datetime import date

import requests
from django.conf import settings

from .models import APODOverride


class NasaError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def _mock_nasa(date_str=None):
    time.sleep(settings.MOCK_NASA_LATENCY)  # stand-in for network time
    day = date_str or date.today().isoformat()
    return {
        "date": day,
        "title": f"Mock APOD for {day}",
        "explanation": "Mock data (USE_MOCK_NASA=1). No request was sent to NASA.",
        "media_type": "image",
        "url": "https://apod.nasa.gov/apod/image/mock.jpg",
    }


def fetch_apod_from_nasa(date_str=None):
    """The slow part: one network call to NASA APOD."""
    if settings.USE_MOCK_NASA:
        return _mock_nasa(date_str)
    params = {"api_key": settings.NASA_API_KEY}
    if date_str:
        params["date"] = date_str
    try:
        resp = requests.get(settings.NASA_APOD_URL, params=params, timeout=15)
    except requests.RequestException as exc:
        raise NasaError(f"Could not reach NASA: {exc}")
    if resp.status_code == 429:
        raise NasaError("NASA rate limit hit, try again later", status=429)
    if resp.status_code != 200:
        raise NasaError(f"NASA returned {resp.status_code}: {resp.text[:200]}")
    return resp.json()


def build_payload(date_str=None):
    """NASA data merged with any local override for that date."""
    data = fetch_apod_from_nasa(date_str)
    override = APODOverride.objects.filter(date=data.get("date")).first()
    payload = {
        "date": data.get("date"),
        "title": data.get("title"),
        "explanation": data.get("explanation"),
        "media_type": data.get("media_type"),
        "url": data.get("url"),
        "overridden": False,
    }
    if override:
        payload["title"] = override.title
        if override.note:
            payload["note"] = override.note
        payload["overridden"] = True
    return payload
