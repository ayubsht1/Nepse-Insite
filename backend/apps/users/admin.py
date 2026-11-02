from django.contrib import admin

from .models import UserProfile, Watchlist

admin.site.register(UserProfile)
admin.site.register(Watchlist)
