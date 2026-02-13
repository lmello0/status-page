def format_bytes(bytes_size: int | float) -> str:
    if bytes_size < 0:
        raise ValueError("Bytes size must be non-negative")

    units = ["B", "KB", "MB", "GB", "TB"]

    for unit in units:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"

        bytes_size /= 1024.0

    return f"{bytes_size:.2f} PB"


def format_time(elapsed_seconds: float) -> str:
    DAY_SECONDS = 86_400
    HOUR_SECONDS = 3_600
    MINUTE_SECONDS = 60

    days, remainder = divmod(elapsed_seconds, DAY_SECONDS)
    hours, remainder = divmod(remainder, HOUR_SECONDS)
    minutes, seconds = divmod(remainder, MINUTE_SECONDS)

    return f"{int(days):02d}d {int(hours):02d}h {int(minutes):02d}m {seconds:05.2f}s"
