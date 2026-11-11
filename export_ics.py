"""Turn a study plan into an .ics file that calendar apps can import."""
import uuid
from datetime import datetime, timezone

import pandas as pd
from icalendar import Calendar, Event

from scheduler import merge_blocks


def plan_to_ics(plan: pd.DataFrame) -> bytes:
    """One calendar event per study block."""
    cal = Calendar()
    cal.add("prodid", "-//UCL Study Planner//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "Study plan")

    for _, row in merge_blocks(plan).iterrows():
        event = Event()
        event.add("uid", f"{uuid.uuid4()}@ucl-study-planner")
        event.add("dtstamp", datetime.now(timezone.utc))
        # Stored in UTC so every calendar app reads the times the same way
        event.add("dtstart", row["start"].tz_convert("UTC").to_pydatetime())
        event.add("dtend", row["end"].tz_convert("UTC").to_pydatetime())
        event.add("summary", f"Study: {row['task']}")
        event.add("description", f"{row['file']} (difficulty {row['difficulty']}/5)")
        cal.add_component(event)

    return cal.to_ical()