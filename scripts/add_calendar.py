import os
import requests
from dotenv import load_dotenv

from icalendar import Calendar

load_dotenv()

calendar_url = os.getenv("ICAL_URL")

if not calendar_url:
    print("ICAL_URL is not set in the environment variables.PLease set it in the .env file.")

response = requests.get(calendar_url, timeout=30, allow_redirects=True)
  # Set a timeout and allow redirects
print(f"Response Status Code: {response.status_code}")  # Print the status code for debugging
print("Final URL after redirects:", response.url)  # Print the final URL after redirects
  # Print the response content for debugging
print("Content Type:", response.headers.get('Content-Type'))  # Print the content type for debugging
print("Response preview:")
print(response.text)  # Print the first 500 characters of the response text for debugging

response.raise_for_status()  # Raise an error for bad responses

calendar = Calendar.from_ical(response.content)

for component in calendar.walk("VEVENT"):
    
    summary = component.get("summary", "No Title")
    start_time = component.get("dtstart").dt
    end_time = component.get("dtend").dt

    print(f"Event: {summary}, Start: {start_time}, End: {end_time}")
    print(f"Title: {summary}, Start Time: {start_time}, End Time: {end_time}")
    