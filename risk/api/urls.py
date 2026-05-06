"""API v1 routes — included by config/urls.py under /api/v1/."""
from rest_framework.routers import DefaultRouter

from risk.api.views import CalculationRunViewSet, FundViewSet

router = DefaultRouter()
router.register(r"funds", FundViewSet, basename="fund")
router.register(r"calculation-runs", CalculationRunViewSet, basename="calculation-run")

urlpatterns = router.urls
