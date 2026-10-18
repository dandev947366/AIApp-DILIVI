import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.calendar_models import (
    Base,
    StudentModel,
    CourseModel,
    CalendarEventModel,
)
from src.services.moodle_sync_service import parse_ical_events, sync_calendar_to_db

MOCK_ICAL = b"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-1@example.com
SUMMARY:DB Essay
DESCRIPTION:Write 10 pages.
DTSTART:20261020T140000Z
CATEGORIES:Course: CS101
END:VEVENT
BEGIN:VEVENT
UID:test-2@example.com
SUMMARY:Python Quiz
DTSTART:20261025T080000Z
CATEGORIES:Course: CS204
END:VEVENT
END:VCALENDAR"""


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    yield db
    db.close()


class TestSync:
    @patch("src.services.moodle_sync_service.fetch_ical")
    def test_inserts_events(self, mock_fetch, test_db):
        mock_fetch.return_value = MOCK_ICAL
        stats = sync_calendar_to_db("http://fake", 66944, "Test", test_db)
        assert stats["events_added"] == 2
        assert stats["courses_added"] == 2

    @patch("src.services.moodle_sync_service.fetch_ical")
    def test_no_duplicates_on_second_sync(self, mock_fetch, test_db):
        mock_fetch.return_value = MOCK_ICAL
        sync_calendar_to_db("http://fake", 66944, "Test", test_db)
        stats = sync_calendar_to_db("http://fake", 66944, "Test", test_db)
        assert stats["events_added"] == 0
        assert stats["events_updated"] == 2
