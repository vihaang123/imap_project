"""Vercel entry point: exposes the Django WSGI app as `app`."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()

# Serverless instances start with an empty database (SQLite lives in /tmp), or
# a fresh Postgres. Apply migrations once per cold start; it is a no-op when
# nothing is pending.
if os.getenv("VERCEL"):
    from django.core.management import call_command

    call_command("migrate", interactive=False, verbosity=0)

app = application
