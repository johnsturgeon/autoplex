from datetime import datetime, UTC
import humanize


def humanize_timedelta(
    start_date_str: str, end_date: datetime = datetime.now(UTC)
) -> str:
    start_date: datetime = datetime.fromtimestamp(int(start_date_str), UTC)
    return humanize.naturaltime(end_date - start_date)
