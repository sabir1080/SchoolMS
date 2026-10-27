import os

os.environ.setdefault("DEBUG", "1")

from .settings import *  # noqa: E402,F401,F403
from .settings import BASE_DIR, REST_FRAMEWORK  # noqa: E402

import dj_database_url  # noqa: E402

# Tests never touch DATABASE_URL (that may be the production database).
# Use TEST_DATABASE_URL to run them against a throwaway PostgreSQL instead of SQLite.
DATABASES = {
    "default": dj_database_url.parse(os.environ.get("TEST_DATABASE_URL", f"sqlite:///{BASE_DIR / 'test.sqlite3'}"))
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"login": "1000/min", "lookup": "1000/min", "register": "1000/min"},
}
