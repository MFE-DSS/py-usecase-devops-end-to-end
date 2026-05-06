"""ORM models for the Risk Metrics Service.

Layer: infrastructure. These classes describe persistence only;
business calculations live in `risk/domain/` (pure functions) and
orchestration lives in `risk/services/`.

Design choices:
- Decimal (not Float) for monetary/return values: auditability, no
  binary drift on aggregates.
- on_delete=PROTECT on RiskMetric FKs: a fund/benchmark with metrics
  cannot be silently deleted (historical integrity).
- UniqueConstraint instead of unique_together (modern Django form).
- methodology stored as JSON snapshot of parameters used for the
  calculation; lets us reproduce/audit any past number.
"""
from django.db import models


class Fund(models.Model):
    name = models.CharField(max_length=200)
    isin = models.CharField(max_length=12, unique=True, db_index=True)
    currency = models.CharField(max_length=3)  # ISO 4217
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["active"])]

    def __str__(self) -> str:
        return f"{self.isin} {self.name}"


class Benchmark(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    currency = models.CharField(max_length=3)

    def __str__(self) -> str:
        return self.code


class FundBenchmarkMapping(models.Model):
    """Bitemporal-ish mapping. A fund's benchmark of reference can change
    over time; the mapping valid at a given as_of_date is the one whose
    [valid_from, valid_to) interval contains as_of_date with is_active=True.
    """
    fund = models.ForeignKey(Fund, on_delete=models.PROTECT, related_name="benchmark_mappings")
    benchmark = models.ForeignKey(Benchmark, on_delete=models.PROTECT)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["fund", "valid_from"],
                name="uniq_fund_valid_from",
            ),
        ]
        indexes = [models.Index(fields=["fund", "is_active"])]


class FundReturn(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="returns")
    date = models.DateField()  # month-end
    monthly_return = models.DecimalField(max_digits=12, decimal_places=8)
    source = models.CharField(max_length=50, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["fund", "date"], name="uniq_fund_date"),
        ]
        indexes = [models.Index(fields=["fund", "date"])]


class BenchmarkReturn(models.Model):
    benchmark = models.ForeignKey(Benchmark, on_delete=models.CASCADE, related_name="returns")
    date = models.DateField()
    monthly_return = models.DecimalField(max_digits=12, decimal_places=8)
    source = models.CharField(max_length=50, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["benchmark", "date"], name="uniq_bench_date"),
        ]
        indexes = [models.Index(fields=["benchmark", "date"])]


class CalculationRun(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING"
        SUCCESS = "SUCCESS"
        FAILED = "FAILED"

    calculation_version = models.CharField(max_length=20)  # e.g. "te.v1.0"
    run_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    triggered_by = models.CharField(max_length=100)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"Run#{self.pk} {self.calculation_version} {self.status}"


class RiskMetric(models.Model):
    class DataQuality(models.TextChoices):
        OK = "OK"
        DEGRADED = "DEGRADED"
        INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

    fund = models.ForeignKey(Fund, on_delete=models.PROTECT, related_name="metrics")
    benchmark = models.ForeignKey(Benchmark, on_delete=models.PROTECT)
    calculation_run = models.ForeignKey(
        CalculationRun, on_delete=models.PROTECT, related_name="metrics"
    )
    metric_name = models.CharField(max_length=50)  # "tracking_error_12m"
    metric_value = models.DecimalField(max_digits=12, decimal_places=8, null=True, blank=True)
    window_months = models.PositiveSmallIntegerField()
    as_of_date = models.DateField()
    data_quality_status = models.CharField(max_length=30, choices=DataQuality.choices)
    observation_count = models.PositiveSmallIntegerField()
    methodology = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["fund", "metric_name", "as_of_date", "calculation_run"],
                name="uniq_metric_per_run",
            ),
        ]
        indexes = [
            models.Index(fields=["fund", "metric_name", "as_of_date"]),
        ]


class DataQualityIssue(models.Model):
    class Severity(models.TextChoices):
        LOW = "LOW"
        MEDIUM = "MEDIUM"
        HIGH = "HIGH"

    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="quality_issues")
    issue_type = models.CharField(max_length=50)  # MISSING_RETURN, STALE_NAV, OUTLIER
    severity = models.CharField(max_length=20, choices=Severity.choices)
    description = models.TextField()
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["fund", "resolved_at"])]
