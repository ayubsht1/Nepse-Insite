from urllib.parse import parse_qs, urlparse

from .base import *

database_url = os.getenv("DATABASE_URL", "").strip()
if not database_url:
    raise ValueError("DATABASE_URL is required for GitHub Actions data jobs.")

parsed_database_url = urlparse(database_url)
query = parse_qs(parsed_database_url.query)
if (
    parsed_database_url.scheme not in {"postgres", "postgresql"}
    or not parsed_database_url.hostname
    or parsed_database_url.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
    or query.get("sslmode") != ["require"]
):
    raise ValueError(
        "GitHub Actions data jobs require an external PostgreSQL DATABASE_URL "
        "with sslmode=require."
    )

if len(os.getenv("SECRET_KEY", "").strip()) < 50:
    raise ValueError(
        "SECRET_KEY must contain at least 50 characters for GitHub Actions data jobs."
    )

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}
