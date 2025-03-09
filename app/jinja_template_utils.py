import arrow


def humanize_timedelta(start_date_str: str) -> str:
    start_date = arrow.get(start_date_str)
    human_time = start_date.humanize()
    return human_time
