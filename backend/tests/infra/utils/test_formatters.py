import pytest

from infra.utils.formatters import format_bytes, format_time


def test_format_bytes_formats_units() -> None:
    assert format_bytes(0) == "0.00 B"
    assert format_bytes(1024) == "1.00 KB"
    assert format_bytes(1024 * 1024) == "1.00 MB"


def test_format_bytes_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        format_bytes(-1)


def test_format_time_formats_days_hours_minutes_seconds() -> None:
    assert format_time(90061.5) == "01d 01h 01m 01.50s"
