from django.urls import path

from .views import (
    FloorsheetImportView,
    FloorsheetListView,
    MarketAnalysisOverviewView,
    PriceImportView,
    StockPriceListView,
)

urlpatterns = [
    path("analysis/", MarketAnalysisOverviewView.as_view(), name="market-analysis"),
    path("prices/", StockPriceListView.as_view(), name="stock-price-list"),
    path("floorsheet/", FloorsheetListView.as_view(), name="floorsheet-list"),
    path(
        "admin/prices/import/",
        PriceImportView.as_view(),
        name="stock-price-import",
    ),
    path(
        "admin/floorsheet/import/",
        FloorsheetImportView.as_view(),
        name="floorsheet-import",
    ),
]
