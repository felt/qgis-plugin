"""
Recent Maps Model Test.
"""

import unittest
import os
from tempfile import TemporaryDirectory

from qgis.PyQt.QtCore import QDateTime
from qgis.core import (
    QgsProject
)

from .utilities import get_qgis_app
from ..core.recent_projects_model import RecentMapsModel

QGIS_APP = get_qgis_app()


class RecentMapsModelTest(unittest.TestCase):
    """Test recent maps model works."""

    def test_pretty_date(self):
        """
        Test generation of pretty date diffs
        """
        model = RecentMapsModel()
        now = QDateTime.currentDateTime()
        self.assertEqual(model.pretty_format_date(now), "just now")

        one_minute_ago = now.addSecs(-1 * 60)
        self.assertEqual(model.pretty_format_date(one_minute_ago), "1 minute ago")

        ten_minutes_ago = now.addSecs(-10 * 60)
        self.assertEqual(model.pretty_format_date(ten_minutes_ago), "10 minutes ago")

        one_hour_ago = now.addSecs(-1 * 60 * 60)
        self.assertEqual(model.pretty_format_date(one_hour_ago), "1 hour ago")
        
        three_hours_ago = now.addSecs(-3 * 60 * 60)
        self.assertEqual(model.pretty_format_date(three_hours_ago), "3 hours ago")

        yesterday = now.addDays(-1)
        self.assertEqual(model.pretty_format_date(yesterday), "yesterday")

        four_days_ago = now.addDays(-4)
        self.assertEqual(model.pretty_format_date(four_days_ago), "4 days ago")

        one_week_ago = now.addDays(-7)
        self.assertEqual(model.pretty_format_date(one_week_ago), "1 week ago")

        two_weeks_ago = now.addDays(-14)
        self.assertEqual(model.pretty_format_date(two_weeks_ago), "2 weeks ago")

        one_month_ago = now.addMonths(-1)
        self.assertEqual(model.pretty_format_date(one_month_ago), "1 month ago")

        three_months_ago = now.addMonths(-3)
        self.assertEqual(model.pretty_format_date(three_months_ago), "3 months ago")

        one_year_ago = now.addYears(-1)
        self.assertEqual(model.pretty_format_date(one_year_ago), "1 year ago")

        two_years_ago = now.addYears(-2)
        self.assertEqual(model.pretty_format_date(two_years_ago), "2 years ago")



if __name__ == "__main__":
    suite = unittest.makeSuite(RecentMapsModelTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
