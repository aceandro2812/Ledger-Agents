from datetime import date, datetime
from typing import List, Set, Union

# Default Indian National Holidays and major fixed-date public holidays.
# Since festival dates vary year-to-year, this default set contains major national holidays
# and allows addition of dynamically configured holiday dates from the frontend.
DEFAULT_INDIAN_HOLIDAYS = {
    # Format: (month, day)
    (1, 26): "Republic Day",
    (5, 1): "May Day / Maharashtra Day",
    (8, 15): "Independence Day",
    (10, 2): "Gandhi Jayanti",
    (12, 25): "Christmas Day",
}

class HolidayChecker:
    def __init__(self, custom_holidays: List[str] = None):
        """
        Initialize the checker with an optional list of custom holiday dates.
        custom_holidays: list of date strings in YYYY-MM-DD or DD-MM-YYYY format
        """
        self.custom_holiday_dates: Set[date] = set()
        if custom_holidays:
            for h_str in custom_holidays:
                parsed_dt = self._parse_date_string(h_str)
                if parsed_dt:
                    self.custom_holiday_dates.add(parsed_dt.date())

    def _parse_date_string(self, d_str: str) -> Union[datetime, None]:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(d_str.strip(), fmt)
            except ValueError:
                continue
        return None

    def is_holiday_or_sunday(self, dt: Union[date, datetime]) -> bool:
        """
        Checks if the given date is a Sunday or a public holiday.
        """
        # If it's a datetime, extract date
        if isinstance(dt, datetime):
            dt = dt.date()
        
        # Check Sunday (weekday 6 in python: Monday=0, Sunday=6)
        if dt.weekday() == 6:
            return True

        # Check default fixed-date holidays
        if (dt.month, dt.day) in DEFAULT_INDIAN_HOLIDAYS:
            return True

        # Check custom/dynamic holidays configured by the user
        if dt in self.custom_holiday_dates:
            return True

        return False

    def get_holiday_reason(self, dt: Union[date, datetime]) -> str:
        """
        Returns the reason/name of the holiday if it is one, otherwise empty string.
        """
        if isinstance(dt, datetime):
            dt = dt.date()

        if dt.weekday() == 6:
            return "Sunday"

        if (dt.month, dt.day) in DEFAULT_INDIAN_HOLIDAYS:
            return DEFAULT_INDIAN_HOLIDAYS[(dt.month, dt.day)]

        if dt in self.custom_holiday_dates:
            return "Custom Public Holiday"

        return ""
