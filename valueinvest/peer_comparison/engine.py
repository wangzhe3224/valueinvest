"""Peer Comparison Engine - compares a stock against industry peers."""

from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from valueinvest.stock import Stock

from .base import (
    MetricComparison,
    MetricDirection,
    ComparisonRating,
    PeerComparisonResult,
    _score_to_rating,
)

# Metrics to compare: (peer_attr, display_name, direction, default_weight)
METRIC_DEFINITIONS = [
    ("pe_ratio", "PE Ratio", MetricDirection.LOWER_BETTER, 0.20),
    ("pb_ratio", "PB Ratio", MetricDirection.LOWER_BETTER, 0.15),
    ("roe", "ROE (%)", MetricDirection.HIGHER_BETTER, 0.20),
    ("market_cap", "Market Cap", MetricDirection.HIGHER_BETTER, 0.10),
    ("net_margin", "Net Margin (%)", MetricDirection.HIGHER_BETTER, 0.15),
    ("operating_margin", "Operating Margin (%)", MetricDirection.HIGHER_BETTER, 0.10),
    ("revenue_growth", "Revenue Growth (%)", MetricDirection.HIGHER_BETTER, 0.10),
]

MIN_PEERS = 3


class PeerComparisonEngine:
    """Compares a stock's financial metrics against industry peers.

    Usage:
        engine = PeerComparisonEngine()
        result = engine.analyze(stock)

        # Or with manual peers (e.g., US stocks):
        engine = PeerComparisonEngine(peers=manual_peer_list)
        result = engine.analyze(stock)
    """

    def __init__(
        self,
        peers: Optional[List] = None,
        metric_weights: Optional[Dict[str, float]] = None,
        min_peers: int = MIN_PEERS,
    ):
        self._peers = peers
        self._metric_weights = metric_weights
        self._min_peers = min_peers

    def analyze(self, stock: "Stock") -> PeerComparisonResult:
        """Run peer comparison analysis.

        Args:
            stock: Stock instance with financial data.

        Returns:
            PeerComparisonResult with metric comparisons and composite score.
        """
        peers = self._get_peers(stock)
        industry_name = stock.industry or "Unknown"
        market = "cn" if stock.ticker.isdigit() else "us"

        if len(peers) < self._min_peers:
            return self._insufficient_data_result(
                stock.ticker, industry_name, market, len(peers)
            )

        rank, percentile = self._compute_rank(stock, peers)
        metric_comparisons = self._compute_metric_comparisons(stock, peers)
        composite = self._compute_composite(metric_comparisons)
        strengths, weaknesses, warnings, analysis = self._build_evidence(
            stock, metric_comparisons, composite, peers
        )

        return PeerComparisonResult(
            ticker=stock.ticker,
            industry_name=industry_name,
            market=market,
            composite_score=composite,
            rating=_score_to_rating(composite),
            metric_comparisons=metric_comparisons,
            peer_count=len(peers),
            rank_in_peers=rank,
            percentile_rank=percentile,
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=warnings,
            analysis=analysis,
        )

    def _get_peers(self, stock: "Stock") -> list:
        """Get peer list: manual if provided, otherwise from IndustryRegistry."""
        if self._peers is not None:
            return self._peers

        try:
            from valueinvest.industry.registry import IndustryRegistry

            fetcher = IndustryRegistry.get_fetcher(stock.ticker)
            result = fetcher.fetch_industry_data(
                stock.ticker, include_peers_count=50
            )
            return [p for p in result.peers if p.ticker != stock.ticker]
        except Exception:
            return []

    def _compute_rank(self, stock: "Stock", peers: list) -> tuple:
        """Compute market-cap rank and percentile among peers."""
        target_mc = stock.market_cap
        all_caps = [target_mc] + [p.market_cap for p in peers if p.market_cap > 0]
        all_caps.sort(reverse=True)
        try:
            rank = all_caps.index(target_mc) + 1
        except ValueError:
            rank = len(all_caps)
        percentile = (1 - (rank - 1) / max(len(all_caps) - 1, 1)) * 100
        return rank, percentile

    def _compute_metric_comparisons(
        self, stock: "Stock", peers: list
    ) -> List[MetricComparison]:
        """Compute per-metric comparison against peers."""
        target_values = {
            "pe_ratio": stock.pe_ratio,
            "pb_ratio": stock.pb_ratio,
            "roe": stock.roe,
            "market_cap": stock.market_cap,
            "net_margin": self._derive_net_margin(stock),
            "operating_margin": stock.operating_margin,
            "revenue_growth": stock.revenue_growth,
        }

        comparisons = []
        for metric_key, metric_name, direction, _ in METRIC_DEFINITIONS:
            peer_values = self._get_peer_values(peers, metric_key)
            target_val = target_values.get(metric_key, 0.0)

            if len(peer_values) < 2:
                comparisons.append(
                    MetricComparison(
                        metric_name=metric_name,
                        metric_key=metric_key,
                        target_value=target_val,
                        peer_avg=0.0,
                        peer_median=0.0,
                        peer_count=0,
                        percentile=0.0,
                        direction=direction,
                        is_available=False,
                    )
                )
                continue

            avg = sum(peer_values) / len(peer_values)
            median = self._median(peer_values)
            pct = self._percentile(target_val, peer_values, direction)

            comparisons.append(
                MetricComparison(
                    metric_name=metric_name,
                    metric_key=metric_key,
                    target_value=target_val,
                    peer_avg=avg,
                    peer_median=median,
                    peer_count=len(peer_values),
                    percentile=pct,
                    direction=direction,
                    is_available=True,
                )
            )

        return comparisons

    def _get_peer_values(self, peers: list, metric_key: str) -> list:
        """Extract valid metric values from peers."""
        values = []
        for p in peers:
            val = getattr(p, metric_key, 0.0)
            if val == 0.0 and metric_key == "net_margin":
                val = p.effective_net_margin
            # Include zero for ROE (could be legitimately 0)
            if val != 0.0 or metric_key == "roe":
                values.append(val)
        return values

    @staticmethod
    def _derive_net_margin(stock: "Stock") -> float:
        """Derive net margin from stock fields."""
        if stock.revenue > 0 and stock.net_income != 0:
            return (stock.net_income / stock.revenue) * 100
        return 0.0

    @staticmethod
    def _percentile(
        value: float, peer_values: list, direction: MetricDirection
    ) -> float:
        """Calculate percentile rank of value within peer_values.

        For HIGHER_BETTER: higher value = higher percentile.
        For LOWER_BETTER: lower value = higher percentile (inverted).
        """
        if not peer_values:
            return 0.0

        n = len(peer_values)
        count_below = sum(1 for v in peer_values if v < value)
        count_equal = sum(1 for v in peer_values if v == value)
        raw = (count_below + 0.5 * count_equal) / n * 100

        if direction == MetricDirection.LOWER_BETTER:
            raw = 100 - raw

        return max(0.0, min(100.0, raw))

    @staticmethod
    def _median(values: list) -> float:
        """Calculate median of a list of floats."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
        return sorted_vals[mid]

    def _compute_composite(self, metric_comparisons: list) -> float:
        """Compute weighted composite score from metric comparisons."""
        weights = {
            metric_key: default_weight
            for metric_key, _, _, default_weight in METRIC_DEFINITIONS
        }
        if self._metric_weights:
            weights.update(self._metric_weights)

        total_weight = 0.0
        weighted_sum = 0.0

        for mc in metric_comparisons:
            if mc.is_available and mc.percentile > 0:
                w = weights.get(mc.metric_key, 0.0)
                weighted_sum += mc.percentile * w
                total_weight += w

        if total_weight == 0:
            return 0.0

        return max(0.0, min(100.0, weighted_sum / total_weight))

    def _build_evidence(
        self, stock, metric_comparisons, composite, peers
    ) -> tuple:
        """Build strengths, weaknesses, warnings, and analysis lists."""
        strengths = []
        weaknesses = []
        warnings = []
        analysis = []

        for mc in metric_comparisons:
            if not mc.is_available:
                warnings.append(f"{mc.metric_name}: insufficient peer data")
                continue
            if mc.percentile >= 75:
                strengths.append(
                    f"{mc.metric_name} at {mc.percentile:.0f}th percentile "
                    f"({mc.target_value:.1f} vs avg {mc.peer_avg:.1f})"
                )
            elif mc.percentile <= 25:
                weaknesses.append(
                    f"{mc.metric_name} at {mc.percentile:.0f}th percentile "
                    f"({mc.target_value:.1f} vs avg {mc.peer_avg:.1f})"
                )

        rating = _score_to_rating(composite)
        analysis.append(
            f"{stock.ticker} ({stock.name}): Peer comparison rating = "
            f"{rating.value.upper()} ({composite:.0f}/100)"
        )
        analysis.append(
            f"Compared against {len(peers)} peers in "
            f"{stock.industry or 'same industry'}"
        )

        if composite >= 60:
            analysis.append(
                "Overall financial metrics are above industry peers, "
                "suggesting competitive strength"
            )
        elif composite >= 40:
            analysis.append(
                "Financial metrics are broadly in line with industry peers"
            )
        else:
            analysis.append(
                "Financial metrics lag behind industry peers, "
                "warrants further investigation"
            )

        val_metrics = [
            m
            for m in metric_comparisons
            if m.metric_key in ("pe_ratio", "pb_ratio") and m.is_available
        ]
        if val_metrics:
            avg_val_pct = sum(m.percentile for m in val_metrics) / len(val_metrics)
            if avg_val_pct >= 70:
                analysis.append("Stock appears expensive relative to peers")
            elif avg_val_pct <= 30:
                analysis.append("Stock appears cheap relative to peers")

        return strengths, weaknesses, warnings, analysis

    def _insufficient_data_result(
        self, ticker, industry_name, market, peer_count
    ) -> PeerComparisonResult:
        """Return a result indicating insufficient peer data."""
        warning = (
            f"Only {peer_count} peers found (minimum {self._min_peers} required)"
            if peer_count > 0
            else "No peer data available"
        )
        return PeerComparisonResult(
            ticker=ticker,
            industry_name=industry_name,
            market=market,
            composite_score=0.0,
            rating=ComparisonRating.AVERAGE,
            peer_count=peer_count,
            warnings=[warning],
            analysis=[f"{ticker}: Cannot perform peer comparison - {warning}"],
        )
