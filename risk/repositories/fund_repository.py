"""Fund + Benchmark mapping access. Encapsulates business queries that
go beyond simple `Fund.objects.get`."""
from datetime import date

from django.core.exceptions import ObjectDoesNotExist

from risk.models import Benchmark, Fund, FundBenchmarkMapping


class FundNotFound(Exception):
    pass


class BenchmarkMappingNotFound(Exception):
    pass


class FundRepository:
    def get_active(self, fund_id: int) -> Fund:
        try:
            return Fund.objects.get(pk=fund_id, active=True)
        except ObjectDoesNotExist as e:
            raise FundNotFound(f"Fund {fund_id} not found or inactive") from e

    def get_active_benchmark(self, fund: Fund, as_of: date) -> Benchmark:
        """Return the benchmark mapped to `fund` at the given date.

        Selects the mapping whose [valid_from, valid_to) interval contains
        `as_of` and whose is_active flag is True.
        """
        mapping = (
            FundBenchmarkMapping.objects
            .select_related("benchmark")
            .filter(fund=fund, is_active=True, valid_from__lte=as_of)
            .filter(models_q_valid_to_contains(as_of))
            .order_by("-valid_from")
            .first()
        )
        if mapping is None:
            raise BenchmarkMappingNotFound(
                f"No active benchmark mapping for fund {fund.pk} at {as_of}"
            )
        return mapping.benchmark


def models_q_valid_to_contains(as_of: date):
    """Helper: matches mappings whose valid_to is NULL (open-ended) or > as_of."""
    from django.db.models import Q
    return Q(valid_to__isnull=True) | Q(valid_to__gt=as_of)
