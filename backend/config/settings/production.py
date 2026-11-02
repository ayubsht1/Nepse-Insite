from .base import *

DEBUG = False
if SECRET_KEY == "unsafe-development-key":
    raise ValueError("SECRET_KEY must be configured for production.")

SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
