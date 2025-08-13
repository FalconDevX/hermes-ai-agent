import unittest
from main import TZ, parse_iso_local, convert_date_to_local , move_date_to_future
import datetime as dt

class TestParseIsoLocal(unittest.TestCase):
    # Test all-day date sets start of day with Warsaw TZ
    def test_all_day_date_sets_start_of_day_with_warsaw_tz(self):
        d = parse_iso_local("2025-08-14")
        self.assertEqual(d.hour, 0)
        self.assertEqual(d.minute, 0)
        self.assertEqual(d.second, 0)
        self.assertEqual(d.tzinfo, TZ)

    #Test data set with UTC timezone
    def test_uts_date_format(self):
        d = parse_iso_local("2025-08-14T10:00:00Z")
        self.assertIsNotNone(d.tzinfo)
        self.assertEqual(d.astimezone(TZ).utcoffset(), dt.timedelta(hours=2))

class TestConvertDateToLocal(unittest.TestCase):
    # Test conversion of date with Warsaw timezone to local ISO format
    def test_convert_date_to_local(self):
        d = dt.datetime(2025, 8, 14, 10, 0, 0, tzinfo=TZ)
        self.assertEqual(convert_date_to_local(d), "2025-08-14T10:00:00")
    # Checking if future date is unchanged
    def test_future_date_unchanged(self):
        now = dt.datetime(2025, 8, 20, 10, 0, tzinfo=TZ)
        start = now + dt.timedelta(days=1)
        result = move_date_to_future(start, now)
        self.assertEqual(result, start) 
    #Test moving today time from past to tomorrow
    def test_today_but_time_passed_moves_to_tomorrow(self):
        now = dt.datetime(2025, 8, 20, 15, 0, tzinfo=TZ)
        start = dt.datetime(2025, 8, 20, 10, 0, tzinfo=TZ)
        result = move_date_to_future(start, now)
        self.assertEqual(result, dt.datetime(2025, 8, 21, 10, 0, tzinfo=TZ))
    #Test moving date in past to same day next year
    def test_date_in_past_moves_to_same_day_next_year(self):
        now = dt.datetime(2025, 8, 20, 10, 0, tzinfo=TZ)
        start = dt.datetime(2024, 5, 10, 12, 0, tzinfo=TZ)
        result = move_date_to_future(start, now)
        self.assertEqual(result, dt.datetime(2026, 5, 10, 12, 0, tzinfo=TZ))
    # Test moving date from leap year to non-leap year - should return None
    def test_no_avaible_date_after_move(self):
        now = dt.datetime(2025, 8, 20, 10, 0, tzinfo=TZ)
        start = dt.datetime(2020, 2, 29, 9, 0, tzinfo=TZ)
        result = move_date_to_future(start, now)
        self.assertIsNone(result)
if __name__ == '__main__':
    unittest.main()