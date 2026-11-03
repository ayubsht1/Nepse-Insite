import os
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv(
    "SECRET_KEY", "unsafe-development-key-not-for-production-32bytes"
)
DEBUG = False
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
    "channels",
    "apps.users",
    "apps.companies",
    "apps.market_data",
    "apps.news",
    "apps.analytics",
    "apps.crawlers",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
ASGI_APPLICATION = "config.asgi.application"

database_url_value = os.getenv("DATABASE_URL")
if not database_url_value:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    database_url = urlparse(database_url_value)

if database_url_value and database_url.scheme in {"postgres", "postgresql"}:
    database_query = parse_qs(database_url.query)
    database_options = {}
    if "sslmode" in database_query:
        database_options["sslmode"] = database_query["sslmode"][0]
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(database_url.path.lstrip("/")),
            "USER": unquote(database_url.username or ""),
            "PASSWORD": unquote(database_url.password or ""),
            "HOST": database_url.hostname or "localhost",
            "PORT": database_url.port or 5432,
            "CONN_MAX_AGE": 60,
            "OPTIONS": database_options,
        }
    }
elif database_url_value and database_url.scheme == "sqlite":
    sqlite_name = unquote(database_url.path)
    if os.name == "nt" and len(sqlite_name) > 2 and sqlite_name[2] == ":":
        sqlite_name = sqlite_name[1:]
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": sqlite_name,
        }
    }
elif database_url_value:
    raise ValueError(f"Unsupported DATABASE_URL scheme: {database_url.scheme}")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
CORS_ALLOWED_ORIGINS = [FRONTEND_URL]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [FRONTEND_URL]

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "NEPSE Insight API",
    "DESCRIPTION": "API documentation for NEPSE Insight.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.getenv(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379/2"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "celery.beat:PersistentScheduler"
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "crawl-enabled-news-sources-every-four-hours": {
        "task": "apps.crawlers.tasks.crawl_enabled_sources",
        "schedule": crontab(minute=0, hour="*/4"),
    },
    "collect-nepsealpha-market-data-during-market-hours": {
        "task": "apps.market_data.tasks.collect_nepsealpha_market_data",
        "schedule": crontab(
            minute="*/15", hour="11-15", day_of_week="sun-thu"
        ),
    },
    "collect-sharesansar-market-data-during-market-hours": {
        "task": "apps.market_data.tasks.collect_sharesansar_market_data",
        "schedule": crontab(
            minute="*/15", hour="11-15", day_of_week="sun-thu"
        ),
    },
    "collect-merolagani-market-data-during-market-hours": {
        "task": "apps.market_data.tasks.collect_merolagani_market_data",
        "schedule": crontab(
            minute="*/15", hour="11-15", day_of_week="sun-thu"
        ),
    },
    "collect-merolagani-floorsheet-during-market-hours": {
        "task": "apps.market_data.tasks.collect_merolagani_floorsheet_data",
        "schedule": crontab(
            minute="*/15", hour="11-15", day_of_week="sun-thu"
        ),
    },
    "collect-sharesansar-historical-index-data-after-market": {
        "task": "apps.market_data.tasks.collect_sharesansar_index_history_data",
        "schedule": crontab(minute=15, hour=15, day_of_week="sun-thu"),
    },
    "collect-sharesansar-company-history-after-market": {
        "task": "apps.market_data.tasks.collect_sharesansar_company_history_data",
        "schedule": crontab(minute=45, hour=15, day_of_week="sun-thu"),
    },
}
CRAWLER_USER_AGENT = os.getenv(
    "CRAWLER_USER_AGENT", "NEPSEInsightBot/1.0 (+contact: configure CRAWLER_USER_AGENT)"
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name}: {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        }
    },
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "config": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
