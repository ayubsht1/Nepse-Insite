from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CrawlRunDetailView, CrawlSourceViewSet, StartCrawlView

router = DefaultRouter()
router.register("crawl-sources", CrawlSourceViewSet, basename="crawl-source")

urlpatterns = [
    path("crawl-runs/", StartCrawlView.as_view(), name="crawl-run-list-create"),
    path("crawl-runs/<int:pk>/", CrawlRunDetailView.as_view(), name="crawl-run-detail"),
    path("", include(router.urls)),
]
