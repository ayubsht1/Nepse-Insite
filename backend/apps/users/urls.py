from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CurrentUserView, WatchlistViewSet

router = DefaultRouter()
router.register("watchlists", WatchlistViewSet, basename="watchlist")

urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="current-user"),
    *router.urls,
]
