"""Data freshness checking utilities.

Implements differentiated freshness checking:
- Price data (current_price, market_cap): Fresh if today/yesterday, warn if older
- Fundamental data (EPS, BVPS, revenue): Tolerant up to 6 months
"""
from datetime import datetime, timedelta, date
from typing import Tuple, Optional


def is_trading_day(check_date) -> bool:
    """Check if a date is a trading day (weekday).
    
    A-shares trade on weekdays (Monday-Friday).
    """
    if isinstance(check_date, datetime):
        check_date = check_date.date()
    return check_date.weekday() < 5  # 0=Monday, 4=Friday


def get_last_trading_day(reference_date=None):
    """Get the last trading day from reference date.
    
    Args:
        reference_date: Reference date (default: now)
        
    Returns:
        Last trading day (skips weekends)
    """
    if reference_date is None:
        reference_date = datetime.now()
    elif isinstance(reference_date, date):
        reference_date = datetime.combine(reference_date, datetime.now().time())
    
    # Go back day by day until we find a trading day
    check_date = reference_date
    for _ in range(7):  # Check up to 7 days back
        if is_trading_day(check_date):
            return check_date
        check_date -= timedelta(days=1)
    
    return reference_date  # Fallback


def check_price_data_freshness(
    data_timestamp: str,
    market: str = "A-share",
    reference_time: datetime = None,
) -> Tuple[str, int, str]:
    """Check price data freshness.
    
    Price data should be fresh (today or yesterday).
    
    Args:
        data_timestamp: ISO format timestamp string
        market: Market type ("A-share" or "US")
        reference_time: Reference time for comparison (default: now)
        
    Returns:
        Tuple of (status, days_old, message)
    """
    if reference_time is None:
        reference_time = datetime.now()
    
    try:
        fetch_time = datetime.fromisoformat(data_timestamp)
    except (ValueError, TypeError):
        return ("unknown", 0, "Invalid timestamp format")
    
    age = reference_time - fetch_time
    days_old = age.days
    
    if market == "A-share":
        last_trading_day = get_last_trading_day(reference_time)
        
        # Fresh: Today or last trading day
        if fetch_time.date() == reference_time.date():
            return ("fresh", 0, "✅ 价格数据新鲜 (今天)")
        
        if fetch_time.date() == last_trading_day.date():
            return ("fresh", 0, "✅ 价格数据新鲜 (上一交易日)")
        
        # Acceptable: Yesterday
        yesterday = reference_time - timedelta(days=1)
        if fetch_time.date() == yesterday.date():
            return ("acceptable", 1, "✓ 价格数据较新 (昨天)")
        
        # Stale: 2-3 days old
        if days_old <= 3:
            return ("stale", days_old, f"⚠️ 价格数据较旧 ({days_old}天前)")
        
        # Old: More than 3 days
        return ("old", days_old, f"❌ 价格数据过旧 ({days_old}天前)")
    
    else:  # US stocks
        if fetch_time.date() == reference_time.date():
            return ("fresh", 0, "✅ 价格数据新鲜 (今天)")
        
        yesterday = reference_time - timedelta(days=1)
        if fetch_time.date() == yesterday.date():
            return ("acceptable", 1, "✓ 价格数据较新 (昨天)")
        
        if days_old <= 3:
            return ("stale", days_old, f"⚠️ 价格数据较旧 ({days_old}天前)")
        
        return ("old", days_old, f"❌ 价格数据过旧 ({days_old}天前)")


def check_fundamental_data_freshness(
    report_date,  # date object or string
    reference_date: date = None,
) -> Tuple[str, int, str]:
    """Check fundamental data freshness.
    
    Fundamental data (quarterly financial statements) is tolerant up to 6 months.
    
    Args:
        report_date: Financial report date (date object or YYYYMMDD string)
        reference_date: Reference date for comparison (default: today)
        
    Returns:
        Tuple of (status, months_old, message)
    """
    if reference_date is None:
        reference_date = datetime.now().date()
    
    # Parse report date
    if isinstance(report_date, str):
        if len(report_date) == 8 and report_date.isdigit():
            try:
                report_date = datetime.strptime(report_date, "%Y%m%d").date()
            except:
                return ("unknown", 0, "Invalid report date format")
        else:
            return ("unknown", 0, "Invalid report date format")
    elif not isinstance(report_date, date):
        return ("unknown", 0, "Invalid report date type")
    
    # Calculate age in months
    days_old = (reference_date - report_date).days
    months_old = days_old / 30  # Approximate
    
    # Fresh: Within 3 months (latest quarterly report)
    if months_old <= 3:
        return ("fresh", int(months_old), f"✅ 基本面数据新鲜 ({int(months_old)}个月前)")
    
    # Acceptable: 3-6 months (could be last quarterly report)
    if months_old <= 6:
        return ("acceptable", int(months_old), f"✓ 基本面数据可接受 ({int(months_old)}个月前)")
    
    # Stale: 6-9 months
    if months_old <= 9:
        return ("stale", int(months_old), f"⚠️ 基本面数据较旧 ({int(months_old)}个月前)")
    
    # Old: More than 9 months
    return ("old", int(months_old), f"❌ 基本面数据过旧 ({int(months_old)}个月前)")


def format_price_freshness_warning(status: str, days_old: int, ticker: str) -> str:
    """Format a warning message for old price data."""
    if status == "old":
        return (
            f"\n{'='*70}\n"
            f"⚠️  价格数据新鲜度警告\n"
            f"{'='*70}\n"
            f"股票: {ticker}\n"
            f"数据时间: {days_old} 天前\n"
            f"状态: 价格数据过旧\n"
            f"\n"
            f"建议:\n"
            f"  1. 检查网络连接是否正常\n"
            f"  2. 尝试重新获取数据\n"
            f"  3. 如果问题持续，可能是数据源问题\n"
            f"{'='*70}\n"
        )
    elif status == "stale":
        return f"\n⚠️  价格数据提示: {ticker} 价格数据为 {days_old} 天前，建议检查数据源\n"
    return ""


def format_fundamental_freshness_warning(status: str, months_old: int, ticker: str) -> str:
    """Format a warning message for old fundamental data."""
    if status == "old":
        return (
            f"\n{'='*70}\n"
            f"⚠️  基本面数据新鲜度警告\n"
            f"{'='*70}\n"
            f"股票: {ticker}\n"
            f"财报日期: {months_old} 个月前\n"
            f"状态: 基本面数据过旧\n"
            f"\n"
            f"说明:\n"
            f"  季度财报数据滞后超过9个月，可能已不反映最新情况。\n"
            f"  建议查看最新财报公告或等待新财报发布。\n"
            f"{'='*70}\n"
        )
    elif status == "stale":
        return f"\n⚠️  基本面数据提示: {ticker} 财报数据为 {months_old} 个月前，建议查看最新财报\n"
    return ""


# Backward compatibility - deprecated
check_data_freshness = check_price_data_freshness
format_freshness_warning = format_price_freshness_warning
