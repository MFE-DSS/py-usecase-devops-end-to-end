"""DRF serializers — JSON contract for the public API.

Decisions:
- explicit `fields = [...]` lists (never "__all__"): the JSON shape is
  a contract, not a side-effect of the ORM schema. New columns must be
  consciously exposed.
- read-only enrichments (fund_isin, benchmark_code) flatten the response
  so consumers don't navigate FKs.
- TrackingErrorRequestSerializer validates POST input separately —
  request and response shapes diverge.
"""
from rest_framework import serializers

from risk.models import CalculationRun, Fund, RiskMetric


class FundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fund
        fields = ["id", "isin", "name", "currency", "active"]
        read_only_fields = fields


class RiskMetricSerializer(serializers.ModelSerializer):
    fund_isin = serializers.CharField(source="fund.isin", read_only=True)
    benchmark_code = serializers.CharField(source="benchmark.code", read_only=True)
    calculation_version = serializers.CharField(
        source="calculation_run.calculation_version", read_only=True
    )

    class Meta:
        model = RiskMetric
        fields = [
            "id",
            "fund",
            "fund_isin",
            "benchmark",
            "benchmark_code",
            "metric_name",
            "metric_value",
            "window_months",
            "as_of_date",
            "observation_count",
            "data_quality_status",
            "calculation_run",
            "calculation_version",
            "methodology",
            "created_at",
        ]
        read_only_fields = fields


class CalculationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalculationRun
        fields = [
            "id",
            "calculation_version",
            "run_date",
            "status",
            "triggered_by",
            "notes",
        ]
        read_only_fields = fields


class TriggerTrackingErrorSerializer(serializers.Serializer):
    """Input contract for POST /api/v1/calculation-runs/.

    Validation only — no DB writes here.
    """
    fund_id = serializers.IntegerField(min_value=1)
    as_of_date = serializers.DateField()
    triggered_by = serializers.CharField(max_length=100, default="api")
