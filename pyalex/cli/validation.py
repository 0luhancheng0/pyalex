"""
Input validation utilities for PyAlex CLI.

This module provides validation functions for CLI inputs including:
- Range filters
- Date ranges
- IDs
- Filter values
"""

import re


def _parse_single_value(value: str) -> str | None:
    """Parse a single numeric value.

    Args:
        value: String to parse as integer

    Returns:
        Original string if valid integer, None otherwise
    """
    try:
        int(value)
        return value
    except ValueError:
        return None


def _parse_range_value(lower_str: str, upper_str: str) -> str | None:
    """Parse a range value with lower and upper bounds.

    Args:
        lower_str: Lower bound string (can be empty for open range)
        upper_str: Upper bound string (can be empty for open range)

    Returns:
        Formatted range string or None if invalid

    Examples:
        _parse_range_value("", "500") -> "<500"
        _parse_range_value("100", "") -> ">100"
        _parse_range_value("100", "500") -> "100-500"
    """
    # Handle upper bound only (-500)
    if not lower_str and upper_str:
        try:
            int(upper_str)
            return f"<{upper_str}"
        except ValueError:
            return None

    # Handle lower bound only (100-)
    if lower_str and not upper_str:
        try:
            int(lower_str)
            return f">{lower_str}"
        except ValueError:
            return None

    # Handle full range (100-500)
    if lower_str and upper_str:
        try:
            lower = int(lower_str)
            upper = int(upper_str)
            return f"{lower}-{upper}" if lower <= upper else None
        except ValueError:
            return None

    return None


def parse_range_filter(value: str) -> str | None:
    """
    Parse range filter format (e.g., "100-500", "100-", "-500", ">100", "<500").

    Args:
        value: The range filter string

    Returns:
        Parsed range string or None if invalid

    Examples:
        "100-500" -> "100-500"
        "100-" -> ">100"
        "-500" -> "<500"
        ">100" -> ">100"
        "<500" -> "<500"
        "100" -> "100"
    """
    if not value:
        return None

    value = value.strip()

    # Early return for explicit operators
    if value.startswith((">", "<")):
        return value

    # Early return for range format
    if "-" in value:
        parts = value.split("-", 1)
        return _parse_range_value(parts[0], parts[1])

    # Single value case
    return _parse_single_value(value)


def validate_year_range(value: str) -> tuple[bool, str | None]:
    """
    Validate a year or year range.

    Args:
        value: Year string (e.g., "2023" or "2020-2023")

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not value:
        return False, "Year value is required"

    value = value.strip()

    # Single year
    if "-" not in value:
        try:
            year = int(value)
            if 1800 <= year <= 2100:
                return True, None
            return False, f"Year {year} out of reasonable range (1800-2100)"
        except ValueError:
            return False, f"Invalid year format: {value}"

    # Year range
    parts = value.split("-", 1)
    if len(parts) != 2:
        return False, f"Invalid year range format: {value}"

    try:
        start_year = int(parts[0]) if parts[0] else None
        end_year = int(parts[1]) if parts[1] else None

        if start_year and not (1800 <= start_year <= 2100):
            return False, f"Start year {start_year} out of range"

        if end_year and not (1800 <= end_year <= 2100):
            return False, f"End year {end_year} out of range"

        if start_year and end_year and start_year > end_year:
            return False, f"Start year {start_year} is after end year {end_year}"

        return True, None
    except ValueError:
        return False, f"Invalid year range format: {value}"


def validate_date_format(value: str) -> tuple[bool, str | None]:
    """
    Validate a date or date range in YYYY-MM-DD format.

    Args:
        value: Date string

    Returns:
        Tuple of (is_valid, error_message)
    """
    date_pattern = r"^\d{4}-\d{2}-\d{2}$"

    if not value:
        return False, "Date value is required"

    value = value.strip()

    # Single date
    if ":" not in value:
        if re.match(date_pattern, value):
            return True, None
        return False, f"Invalid date format: {value} (expected YYYY-MM-DD)"

    # Date range
    parts = value.split(":", 1)
    if len(parts) != 2:
        return False, f"Invalid date range format: {value}"

    for part in parts:
        if part and not re.match(date_pattern, part):
            return False, f"Invalid date in range: {part} (expected YYYY-MM-DD)"

    return True, None


def clean_openalex_id(id_value: str, url_prefix: str = "https://openalex.org/") -> str:
    """
    Clean and normalize an OpenAlex ID.

    Args:
        id_value: Raw ID value (could be URL or ID)
        url_prefix: OpenAlex URL prefix to remove

    Returns:
        Cleaned ID string

    Examples:
        "https://openalex.org/W123" -> "W123"
        "W123" -> "W123"
        "  W123  " -> "W123"
    """
    if not id_value:
        return ""

    id_value = id_value.strip()

    # Remove URL prefix if present
    if id_value.startswith(url_prefix):
        id_value = id_value[len(url_prefix) :]
    elif id_value.startswith("http://openalex.org/"):
        id_value = id_value.replace("http://openalex.org/", "")
    elif id_value.startswith("https://openalex.org/"):
        id_value = id_value.replace("https://openalex.org/", "")

    return id_value.strip()


def validate_openalex_id(id_value: str) -> tuple[bool, str | None]:
    """
    Validate an OpenAlex ID format.

    Args:
        id_value: ID to validate

    Returns:
        Tuple of (is_valid, error_message)

    OpenAlex IDs follow the format: [TYPE][NUMERIC], e.g., W123456789, A987654321
    Valid types: W (Work), A (Author), S (Source), I (Institution), C (Concept),
                 F (Funder), P (Publisher), T (Topic), etc.
    """
    if not id_value:
        return False, "ID value is required"

    id_value = clean_openalex_id(id_value)

    # Check format: Letter followed by digits
    if not re.match(r"^[A-Z]\d+$", id_value):
        return (
            False,
            f"Invalid OpenAlex ID format: {id_value} (expected format: [TYPE][NUMERIC], e.g., W123456789)",
        )

    return True, None


def parse_id_list(id_string: str, separator: str = ",") -> list[str]:
    """
    Parse a delimited string of IDs into a list.

    Args:
        id_string: String containing IDs
        separator: Delimiter character

    Returns:
        List of cleaned IDs
    """
    if not id_string:
        return []

    ids = [clean_openalex_id(id_val.strip()) for id_val in id_string.split(separator)]
    return [id_val for id_val in ids if id_val]


def validate_positive_int(value: int, name: str = "value") -> tuple[bool, str | None]:
    """
    Validate that a value is a positive integer.

    Args:
        value: Value to validate
        name: Name of the value for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if value is None:
        return False, f"{name} is required"

    if not isinstance(value, int):
        return False, f"{name} must be an integer"

    if value <= 0:
        return False, f"{name} must be positive"

    return True, None


def validate_limit(limit: int | None) -> tuple[bool, str | None]:
    """
    Validate a result limit value.

    Args:
        limit: Limit value to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if limit is None:
        return True, None

    return validate_positive_int(limit, "limit")
