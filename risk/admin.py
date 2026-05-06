from django.contrib import admin

from risk.models import (
    Benchmark,
    BenchmarkReturn,
    CalculationRun,
    DataQualityIssue,
    Fund,
    FundBenchmarkMapping,
    FundReturn,
    RiskMetric,
)


@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    list_display = ("isin", "name", "currency", "active")
    list_filter = ("active", "currency")
    search_fields = ("isin", "name")


@admin.register(Benchmark)
class BenchmarkAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "currency")


@admin.register(FundBenchmarkMapping)
class FundBenchmarkMappingAdmin(admin.ModelAdmin):
    list_display = ("fund", "benchmark", "valid_from", "valid_to", "is_active")
    list_filter = ("is_active",)


@admin.register(FundReturn)
class FundReturnAdmin(admin.ModelAdmin):
    list_display = ("fund", "date", "monthly_return", "source")
    list_filter = ("fund",)
    date_hierarchy = "date"


@admin.register(BenchmarkReturn)
class BenchmarkReturnAdmin(admin.ModelAdmin):
    list_display = ("benchmark", "date", "monthly_return", "source")
    list_filter = ("benchmark",)
    date_hierarchy = "date"


@admin.register(CalculationRun)
class CalculationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "calculation_version", "status", "run_date", "triggered_by")
    list_filter = ("status", "calculation_version")


@admin.register(RiskMetric)
class RiskMetricAdmin(admin.ModelAdmin):
    list_display = (
        "fund",
        "metric_name",
        "as_of_date",
        "metric_value",
        "data_quality_status",
        "calculation_run",
    )
    list_filter = ("metric_name", "data_quality_status")
    date_hierarchy = "as_of_date"


@admin.register(DataQualityIssue)
class DataQualityIssueAdmin(admin.ModelAdmin):
    list_display = ("fund", "issue_type", "severity", "detected_at", "resolved_at")
    list_filter = ("severity", "issue_type")
