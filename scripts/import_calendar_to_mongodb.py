import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from src.schemas.student_context import CalendarEventInfo

import os
import re
from datetime import datetime, date, time

import requests
from icalendar import Calendar
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv
from pydantic import ValidationError

load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

ICAL_URL = os.getenv("ICAL_URL")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "aiapp_dilivi")
MONGODB_COLLECTION_NAME = os.getenv("MONGODB_COLLECTION_NAME", "calendar_events")
STUDENT_ID = os.getenv("STUDENT_ID", "default_student_id")  # Default student ID if not set

if not ICAL_URL:
    raise ValueError("ICAL_URL is not set in the environment variables. Please set it in the .env file.")

if not STUDENT_ID:
    raise ValueError("STUDENT_ID is not set in the environment variables. Please set it in the .env file.")

def to_datetime(value) -> datetime:
    """
    Convert a value to a datetime object.
    If the value is already a datetime, return it as is.
    If the value is a date, convert it to a datetime at midnight.
    If the value is a time, combine it with today's date.
    """
    if isinstance(value, datetime):
        return value
    elif isinstance(value, date):
        return datetime.combine(value, time.min)
    elif isinstance(value, time):
        return datetime.combine(date.today(), value)
    else:
        raise ValueError(f"Unsupported type for datetime conversion: {type(value)}")

def get_text(component, field_name: str) -> str:
    """
    Extract text from a calendar component field.
    If the field is missing, return an empty string.
    """
    value = component.get(field_name)
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return str(value)

def get_categories(component) -> list[str]:
    """
    Extract categories from a calendar component.
    If the categories field is missing, return an empty list.
    """
    categories = component.get("categories")

    if categories is None:
        return []
    if isinstance(categories, (list, tuple)):
        return [str(item).strip() for item in categories]

    cats = getattr(categories, "cats", None)
    if cats is not None:
        return [str(item).strip() for item in cats]
    return [str(categories)]

def redact_exam_password(text: str) -> str:
    """
    Redact exam passwords from the given text.
    Replaces any occurrence of 'Exam Password: <password>' with 'Exam Password: [REDACTED]'.
    """
    return re.sub(r"(Exam Password:\s*)(\S+)", r"\1[REDACTED]", text, flags=re.IGNORECASE)

def fetch_calendar_events() -> list[dict]:
    """
    Fetch calendar events from the iCal URL and return them as a list of dictionaries.
    Each dictionary represents a calendar event with relevant fields.
    """
    response = requests.get(ICAL_URL, timeout=30, allow_redirects=True)
    response.raise_for_status()  # Raise an error for bad responses
    content_type = response.headers.get('Content-Type', '')

    if not content_type.startswith('text/calendar'):
        raise ValueError("Unexpected content type")

    calendar = Calendar.from_ical(response.content)
    events = []

    for component in calendar.walk("VEVENT"):
        try:
            start = component.get("dtstart").dt
            end = component.get("dtend").dt

            if start is None or end is None:
                print(f"Skipping event due to missing start or end time: {component.get('summary')}")
                continue

            event_info = CalendarEventInfo(
                event_id=get_text(component, "uid"),
                title=get_text(component, "summary"),
                start_time=to_datetime(start),
                end_time=to_datetime(end),
                location=get_text(component, "location"),
                description=redact_exam_password(get_text(component, "description")),
                source="moodle_ical"
            )

            event_doc = event_info.model_dump()

            event_doc["student_id"] = STUDENT_ID  # Add student_id to the event document
            event_doc["categories"] = get_categories(component)  # Add categories to the event document
            event_doc["last_updated"] = datetime.utcnow()  # Add a timestamp for when the event was created
            events.append(event_doc)

        except ValidationError as ve:
            print(f"Validation error for event {get_text(component, 'summary')}: {ve}")
        except Exception as e:
            print(f"Error processing event {get_text(component, 'summary')}: {e}")
    return events

# Save events to MongoDB
def save_events_to_mongodb(events: list[dict]) -> None:
    """
    Save the list of calendar events to MongoDB.
    If an event with the same event_id already exists, it will be updated.
    """
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    collection = db[MONGODB_COLLECTION_NAME]

    # Create a unique index on event_id to prevent duplicates
    collection.create_index([("event_id", ASCENDING)], unique=True)

    for event in events:
        try:
            collection.update_one(
                {"event_id": event["event_id"]},
                {"$set": event},
                upsert=True
            )
        except Exception as e:
            print(f"Error saving event {event['event_id']} to MongoDB: {e}")

    client.close()

# Verify that data can be retrieved from MongoDB
def verify_mongodb_data() -> None:
    """
    Verify that data can be retrieved from MongoDB.
    Prints the number of events stored in the collection.
    """
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]
    collection = db[MONGODB_COLLECTION_NAME]

    event_count = collection.count_documents({})
    print(f"Number of events in MongoDB: {event_count}")

    client.close()

# Main execution
if __name__ == "__main__":
    try:
        events = fetch_calendar_events()
        print(f"Fetched {len(events)} events from the calendar.")   
        save_events_to_mongodb(events)
        if events:
            print("Events saved to MongoDB.")
            verify_mongodb_data()
        else:
            print("No events to save.")
    except Exception as e:
        print(f"An error occurred: {e}")