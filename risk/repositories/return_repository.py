"""Returns access. Returns pandas Series indexed by month-end date,
ready to feed `risk.domain.metrics`."""
from datetime import date

import pandas as pd
from dateutil.relativedelta import relativedelta

from risk.models import Benchmark, BenchmarkReturn, Fund, FundReturn


def _qs_to_series(qs, name: str) -> pd.Series:
    rows = list(qs.values("date", "monthly_return").order_by("date"))
    if not rows:
        return pd.Series(dtype=float, name=name, index=pd.DatetimeIndex([], name="date"))
    df = pd.DataFrame(rows)
    return pd.Series(
        df["monthly_return"].astype(float).values,
        index=pd.DatetimeIndex(df["date"]),
        name=name,
    )


class ReturnRepository:
    def get_fund_returns(self, fund: Fund, as_of: date, months: int) -> pd.Series:
        start = as_of - relativedelta(months=months)
        qs = FundReturn.objects.filter(fund=fund, date__lte=as_of, date__gte=start)
        return _qs_to_series(qs, name="fund")

    def get_benchmark_returns(self, benchmark: Benchmark, as_of: date, months: int) -> pd.Series:
        start = as_of - relativedelta(months=months)
        qs = BenchmarkReturn.objects.filter(benchmark=benchmark, date__lte=as_of, date__gte=start)
        return _qs_to_series(qs, name="benchmark")
