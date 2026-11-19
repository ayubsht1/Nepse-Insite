from .base import *

DEBUG = False
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
if not DATABASES["default"]["USER"] or not DATABASES["default"]["PASSWORD"]:
    raise ValueError(
        "Production DATABASE_URL must include a database username and password."
    )
if DATABASES["default"].get("OPTIONS", {}).get("sslmode") != "require":
    raise ValueError("Production DATABASE_URL must include sslmode=require.")

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
