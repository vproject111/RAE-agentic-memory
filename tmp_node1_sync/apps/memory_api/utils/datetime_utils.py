from datetime import datetime, timezone


def utc_now() -> datetime:
    """Get current UTC datetime with timezone awareness."""
    return datetime.now(timezone.utc)


# Backward-compatible alias if needed
utcnow = utc_now
