"""Read the UCL timetable feed and turn it into tidy tables."""
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import recurring_ical_events
import requests
import yaml
from dotenv import load_dotenv
from icalendar import Calendar

LONDON = ZoneInfo("Europe/London")
LOCAL_COPY = Path("data/timetable.ics")

# Titles that aren't real modules
GENERIC_TITLES = {"", "Timetable Event"}


def clean_module_name(title: str) -> str | None:
    """'Quantum Physics Level 5 [Lecture]' -> 'Quantum Physics'."""
    name = re.sub(r"\s*\[.*?\]\s*$", "", title)   # drop ' [Lecture]'
    name = re.sub(r"\s+Level\s+\d+$", "", name)    # drop ' Level 5'
    name = name.strip()
    return None if name in GENERIC_TITLES else name


def session_type(title: str) -> str | None:
    """'Quantum Physics Level 5 [Lecture]' -> 'Lecture'."""
    match = re.search(r"\[(.*?)\]\s*$", title)
    return match.group(1) if match else None


def fetch_calendar(use_local: bool = False) -> Calendar:
    """Download the timetable feed, or read the saved copy."""
    if use_local and LOCAL_COPY.exists():
        return Calendar.from_ical(LOCAL_COPY.read_bytes())
    load_dotenv()
    url = os.getenv("TIMETABLE_ICS_URL")
    if not url:
        raise RuntimeError("TIMETABLE_ICS_URL is missing from .env")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    LOCAL_COPY.write_bytes(response.content)  # refresh the saved copy
    return Calendar.from_ical(response.content)


def to_london(value) -> datetime:
    """Turn any calendar time into a London-time datetime."""
    if not isinstance(value, datetime):  # all-day events give a plain date
        value = datetime.combine(value, datetime.min.time())
    if value.tzinfo is None:
        return value.replace(tzinfo=LONDON)
    return value.astimezone(LONDON)


def load_timetable(start: date, end: date, use_local: bool = False) -> pd.DataFrame:
    """Every timetabled event between start and end, sorted by start time."""
    cal = fetch_calendar(use_local)
    events = recurring_ical_events.of(cal).between(start, end)

    rows = []
    for event in events:
        title = str(event.get("SUMMARY", "")).strip()

        event_start = to_london(event.get("DTSTART").dt)
        if event.get("DTEND"):
            event_end = to_london(event.get("DTEND").dt)
        elif event.get("DURATION"):
            event_end = event_start + event.get("DURATION").dt
        else:
            event_end = event_start + timedelta(hours=1)

        rows.append({
            "module": clean_module_name(title),
            "type": session_type(title),
            "start": event_start,
            "end": event_end,
            "location": str(event.get("LOCATION", "")).strip(),
        })

    df = pd.DataFrame(rows, columns=["module", "type", "start", "end", "location"])
    return df.sort_values("start").reset_index(drop=True)


def get_modules(timetable: pd.DataFrame) -> list[str]:
    """Unique module names, used later for the upload dropdown."""
    return sorted(timetable["module"].dropna().unique())


def load_prefs(path: str = "prefs.yaml") -> dict:
    """Read your study preferences."""
    with open(path) as f:
        return yaml.safe_load(f)


if __name__ == "__main__":
    today = date.today()
    tt = load_timetable(today, today + timedelta(days=28), use_local=True)

    print(f"{len(tt)} events in the next 4 weeks\n")
    print(tt[["module", "type", "start", "end"]].head(15).to_string(index=False))
    print("\nModules:", get_modules(tt))
    print("Session types:", sorted(tt["type"].dropna().unique()))

    no_module = tt[tt["module"].isna()]
    if not no_module.empty:
        print(f"\n{len(no_module)} events with no module name")