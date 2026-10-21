"""YouTube daily quota boundaries in Pacific civil time."""
import datetime as dt
from zoneinfo import ZoneInfo


def next_reset(now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    pacific = ZoneInfo('America/Los_Angeles')
    tomorrow = now.astimezone(pacific).date() + dt.timedelta(days=1)
    return dt.datetime.combine(tomorrow, dt.time(), pacific).astimezone(dt.timezone.utc)
