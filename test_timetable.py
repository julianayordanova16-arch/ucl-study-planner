import os
import requests
from dotenv import load_dotenv
from icalendar import Calendar

# Read the secret link from .env
load_dotenv()
url = os.getenv("TIMETABLE_ICS_URL")

# Download the calendar
response = requests.get(url, timeout=30)
response.raise_for_status()

# Keep a local copy for testing
with open("data/timetable.ics", "wb") as f:
    f.write(response.content)

# Read the events
cal = Calendar.from_ical(response.content)
events = sorted(cal.walk("VEVENT"), key=lambda e: e.get("DTSTART").dt)
print(f"Found {len(events)} events")

for event in events[:10]:
    print(event.get("DTSTART").dt, "|", event.get("SUMMARY"))
