
from .._http import HttpClient


class AnalyticsResource:
    """Methods for the ``/v1/analytics`` endpoints."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def get_summary(self, period: str = "30d") -> dict:
        """Aggregate delivery and engagement metrics for a period.

        Returns totals for sent, delivered, opened, clicked, bounced and
        complained, plus the derived rates and the average delivery latency.

        Args:
            period: ``7d``, ``30d``, ``90d``, ``180d`` or ``1y``. Defaults to ``30d``.
                ``180d`` and ``1y`` are rejected with a test-mode key.
        """
        return self._http._request(
            "GET", "/v1/analytics/summary", params={"period": period}
        )

    def get_timeseries(self, period: str = "30d") -> dict:
        """The same metrics as :meth:`get_summary`, bucketed by day.

        Useful for charting a trend rather than a single number.

        Args:
            period: ``7d``, ``30d``, ``90d``, ``180d`` or ``1y``. Defaults to ``30d``.
                ``180d`` and ``1y`` are rejected with a test-mode key.
        """
        return self._http._request(
            "GET", "/v1/analytics/timeseries", params={"period": period}
        )
