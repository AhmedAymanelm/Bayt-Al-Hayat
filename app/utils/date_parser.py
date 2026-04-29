from datetime import date
import re


_MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


from typing import Union

def parse_date_input(value: Union[str, date]) -> date:
    """Parse a date input and support formats with English month abbreviations."""
    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        raise ValueError("Invalid date value")

    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Date value cannot be empty")

    # Primary format: YYYY-MM-DD
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        pass

    # Supported examples: 1998-Jan-15, 1998/Jan/15, 1998 Jan 15
    year_first_match = re.fullmatch(r"(\d{4})[-/\s]([A-Za-z]{3})[-/\s](\d{1,2})", cleaned)
    if year_first_match:
        year_str, month_str, day_str = year_first_match.groups()
        month = _MONTH_MAP.get(month_str.lower())
        if month is None:
            raise ValueError("Month must be an English abbreviation like Jan")
        return date(int(year_str), month, int(day_str))

    # Supported examples: 15-Jan-1998, 15/Jan/1998, 15 Jan 1998
    day_first_match = re.fullmatch(r"(\d{1,2})[-/\s]([A-Za-z]{3})[-/\s](\d{4})", cleaned)
    if day_first_match:
        day_str, month_str, year_str = day_first_match.groups()
        month = _MONTH_MAP.get(month_str.lower())
        if month is None:
            raise ValueError("Month must be an English abbreviation like Jan")
        return date(int(year_str), month, int(day_str))

    # Supported examples: Jan-15-1998, Jan/15/1998, Jan 15 1998
    month_first_match = re.fullmatch(r"([A-Za-z]{3})[-/\s](\d{1,2})[-/\s](\d{4})", cleaned)
    if month_first_match:
        month_str, day_str, year_str = month_first_match.groups()
        month = _MONTH_MAP.get(month_str.lower())
        if month is None:
            raise ValueError("Month must be an English abbreviation like Jan")
        return date(int(year_str), month, int(day_str))

    raise ValueError("Date must be YYYY-MM-DD or include month like Jan")


def normalize_date_input(value: Union[str, date]) -> str:
    """Normalize an input date to ISO format YYYY-MM-DD."""
    return parse_date_input(value).isoformat()
