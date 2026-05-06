"""HTTP layer. ViewSets translate requests into service calls and back.

NO business logic here. The View is a thin adapter:
  request -> validate -> delegate to service -> serialize -> respond.
"""
from datetime import date

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from risk.api.serializers import (
    CalculationRunSerializer,
    FundSerializer,
    RiskMetricSerializer,
    TriggerTrackingErrorSerializer,
)
from risk.models import CalculationRun, Fund, RiskMetric
from risk.repositories.fund_repository import (
    BenchmarkMappingNotFound,
    FundNotFound,
)
from risk.repositories.metric_repository import MetricRepository
from risk.services.calculation_service import (
    METRIC_NAME,
    TrackingErrorCalculationService,
    TrackingErrorCommand,
)


class FundViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve funds. Read-only by design at this stage."""
    queryset = Fund.objects.all().order_by("isin")
    serializer_class = FundSerializer
    filterset_fields = ["active", "currency"]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="as_of",
                description="Reference date (YYYY-MM-DD) for the metric lookup.",
                required=True,
                type=str,
            ),
        ],
        responses={200: RiskMetricSerializer, 404: None},
    )
    @action(detail=True, methods=["get"], url_path="tracking-error")
    def tracking_error(self, request, pk=None, version=None):
        """Return the latest tracking_error_12m metric stored for this fund at as_of.

        This endpoint is read-only: it does NOT recalculate silently.
        Trigger a fresh run via POST /api/v1/calculation-runs/.
        """
        fund = self.get_object()
        as_of_str = request.query_params.get("as_of")
        if not as_of_str:
            return Response(
                {"detail": "Query parameter 'as_of' is required (YYYY-MM-DD).",
                 "code": "AS_OF_REQUIRED"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            as_of = date.fromisoformat(as_of_str)
        except ValueError:
            return Response(
                {"detail": "Invalid 'as_of' date format. Use YYYY-MM-DD.",
                 "code": "AS_OF_INVALID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        metric = MetricRepository().latest_for_fund(fund, METRIC_NAME, as_of)
        if metric is None:
            raise NotFound(
                detail=f"No {METRIC_NAME} metric for fund {fund.pk} at {as_of}.",
            )
        return Response(RiskMetricSerializer(metric).data)


class CalculationRunViewSet(viewsets.GenericViewSet):
    """Trigger and inspect calculation runs."""
    queryset = CalculationRun.objects.all().order_by("-run_date")
    serializer_class = CalculationRunSerializer

    @extend_schema(
        request=TriggerTrackingErrorSerializer,
        responses={202: RiskMetricSerializer, 400: None, 404: None},
    )
    def create(self, request, version=None):
        """POST /api/v1/calculation-runs/ — trigger a tracking-error calculation."""
        cmd_serializer = TriggerTrackingErrorSerializer(data=request.data)
        cmd_serializer.is_valid(raise_exception=True)
        data = cmd_serializer.validated_data

        svc = TrackingErrorCalculationService()
        try:
            metric = svc.run(TrackingErrorCommand(
                fund_id=data["fund_id"],
                as_of_date=data["as_of_date"],
                triggered_by=data["triggered_by"],
            ))
        except FundNotFound as e:
            return Response(
                {"detail": str(e), "code": "FUND_NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except BenchmarkMappingNotFound as e:
            return Response(
                {"detail": str(e), "code": "BENCHMARK_MAPPING_NOT_FOUND"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(
            RiskMetricSerializer(metric).data,
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(responses={200: RiskMetricSerializer(many=True)})
    @action(detail=True, methods=["get"], url_path="metrics")
    def metrics(self, request, pk=None, version=None):
        """List all metrics produced by a given calculation run."""
        run = self.get_object()
        qs = (
            RiskMetric.objects
            .filter(calculation_run=run)
            .select_related("fund", "benchmark", "calculation_run")
            .order_by("fund_id")
        )
        return Response(RiskMetricSerializer(qs, many=True).data)
