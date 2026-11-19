import os
from urllib.parse import urlparse

from .base import *

required_environment = (
    "SECRET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "ALLOWED_HOSTS",
    "PUBLIC_APP_URL",
    "CORS_ALLOWED_ORIGINS",
    "CSRF_TRUSTED_ORIGINS",
    "CRAWLER_USER_AGENT",
)
missing_environment = [
    name for name in required_environment if not os.getenv(name, "").strip()
]
if missing_environment:
    raise ValueError(
        "Missing required production environment variables: "
        + ", ".join(missing_environment)
    )

DEBUG = os.getenv("DEBUG", "False").lower() in {"true", "1", "yes"}
if DEBUG:
    raise ValueError("DEBUG must be false in production.")
if (
    len(SECRET_KEY) < 50
    or SECRET_KEY == "unsafe-development-key-not-for-production-32bytes"
):
    raise ValueError(
        "Set SECRET_KEY to a unique random value of at least 50 characters."
    )
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ValueError("Set ALLOWED_HOSTS to explicit deployment hostnames.")
if not os.getenv("DATABASE_URL"):
    raise ValueError("DATABASE_URL must be set to the Supabase PostgreSQL connection URI.")
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ValueError("Production requires PostgreSQL; SQLite is not supported.")
if not DATABASES["default"]["NAME"] or not DATABASES["default"]["HOST"]:
    raise ValueError("DATABASE_URL must include a PostgreSQL database and host.")
if DATABASES["default"]["HOST"].lower() in {"localhost", "127.0.0.1", "::1"}:
    raise ValueError("Production DATABASE_URL must reference the external database.")
if not DATABASES["default"]["USER"] or not DATABASES["default"]["PASSWORD"]:
    raise ValueError(
        "Production DATABASE_URL must include a database username and password."
    )
if DATABASES["default"].get("OPTIONS", {}).get("sslmode") != "require":
    raise ValueError("Production DATABASE_URL must include sslmode=require.")

for redis_setting in ("REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"):
    try:
        redis_url = urlparse(os.environ[redis_setting])
        redis_host = redis_url.hostname
    except ValueError:
        raise ValueError(
            f"{redis_setting} must be a valid redis:// or rediss:// URL."
        ) from None
    if redis_url.scheme not in {"redis", "rediss"} or not redis_host:
        raise ValueError(
            f"{redis_setting} must be a valid redis:// or rediss:// URL."
        )
    if redis_host.lower() in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError(
            f"{redis_setting} must reference the external Redis service."
        )

if not CORS_ALLOWED_ORIGINS:
    raise ValueError("Set CORS_ALLOWED_ORIGINS for the public application origin.")
if not CSRF_TRUSTED_ORIGINS:
    raise ValueError("Set CSRF_TRUSTED_ORIGINS for the public application origin.")

SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "True").lower() in {
    "true",
    "1",
    "yes",
}
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", "False"
).lower() in {"true", "1", "yes"}
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "False").lower() in {
    "true",
    "1",
    "yes",
}
SECURE_REFERRER_POLICY = "same-origin"
