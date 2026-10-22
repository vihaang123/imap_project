import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ON_VERCEL = bool(os.getenv("VERCEL"))
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver", ".vercel.app"]
ALLOWED_HOSTS += [h for h in os.getenv("EXTRA_ALLOWED_HOSTS", "").split(",") if h]
CSRF_TRUSTED_ORIGINS = ["https://*.vercel.app"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apod.apps.ApodConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# DATABASE_URL (Postgres, e.g. Neon) is used when set. Otherwise SQLite: a file
# in the project locally, or in /tmp on Vercel (the only writable place, and it
# is per-instance and temporary).
if os.getenv("DATABASE_URL"):
    import dj_database_url

    DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=60)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": "/tmp/db.sqlite3" if ON_VERCEL else BASE_DIR / "db.sqlite3",
        }
    }

# Redis cache (django-redis). Locally: `docker compose up -d`. On Vercel: set
# REDIS_URL to a hosted Redis (e.g. Upstash, rediss://...). If it is missing on
# Vercel we fall back to a per-instance in-memory cache so the site still loads,
# but hits are then not shared between serverless instances.
REDIS_URL = os.getenv("REDIS_URL") or (None if ON_VERCEL else "redis://127.0.0.1:6379/1")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            "KEY_PREFIX": "apodproj",
        }
    }
    CACHE_LABEL = "Redis"
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    CACHE_LABEL = "in-memory (no REDIS_URL)"

NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
NASA_APOD_URL = "https://api.nasa.gov/planetary/apod"
APOD_CACHE_TTL = int(os.getenv("APOD_CACHE_TTL", "300"))  # seconds

# Optional offline mode: fake NASA responses with simulated latency, so you can
# develop and practise the demo without a key or burning rate limit.
# Leave USE_MOCK_NASA=0 for the real benchmark numbers you submit.
USE_MOCK_NASA = os.getenv("USE_MOCK_NASA", "0") == "1"
MOCK_NASA_LATENCY = float(os.getenv("MOCK_NASA_LATENCY", "0.8"))  # seconds

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
WHITENOISE_USE_FINDERS = True  # serve admin CSS without a collectstatic step
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-us"
