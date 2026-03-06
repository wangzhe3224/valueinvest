"""
Event Detection Module

Detects significant financial events from news:
- Earnings surprises (beat/miss vs consensus)
- Guidance changes (upgrades/downgrades)
- M&A announcements
- Management changes
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import re


@dataclass
class EarningsSurprise:
    """Detected earnings surprise event."""

    ticker: str
    quarter: str
    fiscal_year: int

    actual_eps: float
    consensus_eps: float
    surprise_pct: float  # (Actual - Consensus) / |Consensus| * 100

    beat_or_miss: str  # "beat" or "miss"
    magnitude: str  # "small" (<5%), "moderate" (5-10%), "large" (>10%)

    news_date: datetime
    stock_reaction_pct: Optional[float] = None  # Price change following announcement


class EarningsSurpriseDetector:
    """
    Detects earnings surprises from news headlines and analyst data.

    Looks for patterns like:
    - "beat by X%"
    - "missed estimates by Y%"
    - "earnings surprise"
    - "above/below consensus"
    """

    # Keywords indicating earnings surprises
    BEAT_KEYWORDS = [
        r"beat.*estimate",
        r"beat.*consensus",
        r"above.*expectation",
        r"surpassed.*forecast",
        r"topped.*estimate",
        r"exceeded.*consensus",
        r"better than expected",
        r"stronger than expected",
        r"earnings beat",
        r"profit beat",
    ]

    MISS_KEYWORDS = [
        r"miss.*estimate",
        r"miss.*consensus",
        r"below.*expectation",
        r"fell short",
        r"disappointed.*forecast",
        r"earnings miss",
        r"profit miss",
        r"weaker than expected",
        r"worse than expected",
    ]

    # Numbers extraction patterns
    NUMBER_PATTERN = r"\$?([\d,]+\.?\d*)%?"
    EPS_PATTERN = r"\$?([\d.]+)\s*(per share|eps)"
    PERCENT_PATTERN = r"([\d.]+)%"

    def detect_from_headline(self, headline: str) -> Optional[Dict[str, Any]]:
        """
        Detect earnings surprise from a news headline.

        Returns dict with:
        - type: "beat" or "miss"
        - magnitude_pct: percentage surprise
        - confidence: "high", "medium", "low"
        """
        headline_lower = headline.lower()

        # Check for beat
        for pattern in self.BEAT_KEYWORDS:
            if re.search(pattern, headline_lower):
                # Try to extract percentage
                percent_match = re.search(self.PERCENT_PATTERN, headline)
                if percent_match:
                    magnitude = float(percent_match.group(1))
                    return {
                        "type": "beat",
                        "magnitude_pct": magnitude,
                        "confidence": "high",
                    }
                else:
                    return {
                        "type": "beat",
                        "magnitude_pct": None,
                        "confidence": "medium",
                    }

        # Check for miss
        for pattern in self.MISS_KEYWORDS:
            if re.search(pattern, headline_lower):
                percent_match = re.search(self.PERCENT_PATTERN, headline)
                if percent_match:
                    magnitude = float(percent_match.group(1))
                    return {
                        "type": "miss",
                        "magnitude_pct": magnitude,
                        "confidence": "high",
                    }
                else:
                    return {
                        "type": "miss",
                        "magnitude_pct": None,
                        "confidence": "medium",
                    }

        return None

    def detect_from_guidance(
        self,
        guidance_data: Dict[str, Any],
        actual_eps: Optional[float] = None,
    ) -> Optional[EarningsSurprise]:
        """
        Detect earnings surprise from analyst guidance data.

        Args:
            guidance_data: Dict with analyst_eps_mean, company_eps_low/high
            actual_eps: Actual EPS if available

        Returns:
            EarningsSurprise if detected, None otherwise
        """
        consensus_eps = guidance_data.get("analyst_eps_mean")

        if not consensus_eps or consensus_eps <= 0:
            return None

        # If actual EPS provided
        if actual_eps and actual_eps > 0:
            surprise_pct = ((actual_eps - consensus_eps) / abs(consensus_eps)) * 100

            if surprise_pct > 0:
                beat_or_miss = "beat"
            else:
                beat_or_miss = "miss"

            # Classify magnitude
            abs_surprise = abs(surprise_pct)
            if abs_surprise < 5:
                magnitude = "small"
            elif abs_surprise < 10:
                magnitude = "moderate"
            else:
                magnitude = "large"

            return EarningsSurprise(
                ticker="",  # Will be filled by caller
                quarter=guidance_data.get("quarter", ""),
                fiscal_year=guidance_data.get("fiscal_year", 0),
                actual_eps=actual_eps,
                consensus_eps=consensus_eps,
                surprise_pct=round(surprise_pct, 2),
                beat_or_miss=beat_or_miss,
                magnitude=magnitude,
                news_date=datetime.now(),
            )

        return None

    def analyze_news_batch(
        self,
        news_items: List[Dict[str, Any]],
        guidance_data: Optional[Dict[str, Any]] = None,
    ) -> List[EarningsSurprise]:
        """
        Analyze a batch of news for earnings surprises.

        Args:
            news_items: List of news dicts with 'title', 'date' keys
            guidance_data: Optional analyst guidance data

        Returns:
            List of detected EarningsSurprise objects
        """
        surprises = []

        for news in news_items:
            headline = news.get("title", "")
            news_date = news.get("date", datetime.now())

            # Try to detect from headline
            detection = self.detect_from_headline(headline)

            if detection:
                # Extract quarter/year if possible
                quarter_match = re.search(r"Q(\d)", headline)
                quarter = f"Q{quarter_match.group(1)}" if quarter_match else ""

                year_match = re.search(r"20\d{2}", headline)
                fiscal_year = int(year_match.group()) if year_match else datetime.now().year

                surprise = EarningsSurprise(
                    ticker="",  # Will be filled by caller
                    quarter=quarter,
                    fiscal_year=fiscal_year,
                    actual_eps=0.0,  # Unknown from headline
                    consensus_eps=0.0,
                    surprise_pct=detection.get("magnitude_pct", 0.0) or 0.0,
                    beat_or_miss=detection["type"],
                    magnitude="moderate",  # Default
                    news_date=news_date if isinstance(news_date, datetime) else datetime.now(),
                )
                surprises.append(surprise)

        # If guidance data available, try to detect from that
        if guidance_data:
            surprise = self.detect_from_guidance(guidance_data)
            if surprise:
                surprises.append(surprise)

        return surprises


class GuidanceChangeDetector:
    """
    Detects guidance changes (upgrades/downgrades) from news.
    """

    UPGRADE_KEYWORDS = [
        r"raised.*guidance",
        r"increased.*forecast",
        r"upped.*outlook",
        r"higher.*guidance",
        r"boost.*forecast",
        r"raised.*outlook",
    ]

    DOWNGRADE_KEYWORDS = [
        r"lowered.*guidance",
        r"cut.*forecast",
        r"reduced.*outlook",
        r"downgraded",
        r"slashed.*guidance",
        r"weaker.*forecast",
    ]

    def detect_from_headline(self, headline: str) -> Optional[Dict[str, str]]:
        """Detect guidance change from headline."""
        headline_lower = headline.lower()

        for pattern in self.UPGRADE_KEYWORDS:
            if re.search(pattern, headline_lower):
                return {"type": "upgrade", "confidence": "high"}

        for pattern in self.DOWNGRADE_KEYWORDS:
            if re.search(pattern, headline_lower):
                return {"type": "downgrade", "confidence": "high"}

        return None

    def analyze_news_batch(self, news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze news batch for guidance changes."""
        changes = []

        for news in news_items:
            headline = news.get("title", "")
            detection = self.detect_from_headline(headline)

            if detection:
                changes.append(
                    {
                        "type": detection["type"],
                        "confidence": detection["confidence"],
                        "date": news.get("date", datetime.now()),
                        "headline": headline,
                    }
                )

        return changes
