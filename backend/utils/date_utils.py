import re
from datetime import date, datetime, timedelta
from typing import Optional, Union

# Compiled patterns for fast regex parsing if necessary
DATE_PATTERNS = [
    # YYYY-MM-DD or YYYY/MM/DD or YYYY.MM.DD
    (re.compile(r'^\d{4}[\.\-/]\d{2}[\.\-/]\d{2}$'), ('%Y-%m-%d', '%Y/%m/%d', '%Y.%m.%d')),
    # DD-MM-YYYY or DD/MM/YYYY or DD.MM.YYYY
    (re.compile(r'^\d{2}[\.\-/]\d{2}[\.\-/]\d{4}$'), ('%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y')),
    # D-M-YYYY or D/M/YYYY or D.M.YYYY similar variations
    (re.compile(r'^\d{1,2}[\.\-/]\d{1,2}[\.\-/]\d{4}$'), ('%d-%m-%Y', '%d/%m/%Y', '%d.%m.%Y')),
    # DD-MMM-YYYY or DD-MMM-YY (Tally style e.g., 1-Apr-2023 or 1-Apr-23)
    (re.compile(r'^\d{1,2}[-\s/\.][a-zA-Z]{3,}[-\s/\.]\d{2,4}$'), ('%d-%b-%Y', '%d-%b-%y', '%d %b %Y', '%d %b %y', '%d.%b.%Y')),
]

def parse_date(date_val: Union[str, datetime, date, int, float, None]) -> Optional[date]:
    """
    Parses a date from varying formats (string, datetime, date, excel serial number).
    Returns a datetime.date object or None if parsing fails.
    """
    if date_val is None:
        return None

    # If it is already a date or datetime
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, date):
        return date_val

    # Handle float/int (Excel serial date)
    if isinstance(date_val, (int, float)):
        # Excel date serial number starts from 1900-01-01
        # Excel bug: 1900 is treated as a leap year, so we subtract 2 days for dates after Feb 28, 1900
        try:
            excel_epoch = datetime(1899, 12, 30)
            return (excel_epoch + timedelta(days=float(date_val))).date()
        except Exception:
            return None

    # Handle string parsing
    if isinstance(date_val, str):
        cleaned = date_val.strip()
        if not cleaned:
            return None

        # Check if it looks like a timestamp (e.g. 2026-05-23 18:30:00 or similar)
        # Try full datetime formats first
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%d-%m-%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue

        # Try mapping with regex patterns
        for pattern, formats in DATE_PATTERNS:
            if pattern.match(cleaned):
                for fmt in formats:
                    try:
                        return datetime.strptime(cleaned, fmt).date()
                    except ValueError:
                        continue

        # Fallback to direct trial of common formats
        fallback_formats = [
            "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y",
            "%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%d %b %y",
            "%Y%m%d", "%d-%m-%y", "%d/%m/%y",
            "%d.%m.%Y", "%Y.%m.%d", "%d.%b.%Y", "%d.%m.%y"
        ]
        for fmt in fallback_formats:
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue

    return None
