"""Work out when you're free to study."""
from datetime import date, datetime, time, timedelta

import pandas as pd

from calendar_io import LONDON, load_prefs, load_timetable

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday",
             "Friday", "Saturday", "Sunday"]


def at(day: date, hhmm: str) -> datetime:
    """A London-time datetime for a day and a time like '18:30'."""
    hours, minutes = map(int, hhmm.split(":"))
    return datetime.combine(day, time(hours, minutes), tzinfo=LONDON)


def commitment_times(day: date, commitment: dict) -> tuple[datetime, datetime]:
    """Start and end of a commitment on a given day.
    An end at or before the start (like '00:00') means it runs past midnight."""
    start = at(day, commitment["start"])
    end = at(day, commitment["end"])
    if end <= start:
        end += timedelta(days=1)
    return start, end


def busy_periods(day: date, timetable: pd.DataFrame, prefs: dict) -> list:
    """Everything that blocks study time on one day: lectures + commitments."""
    day_start = datetime.combine(day, time(0), tzinfo=LONDON)
    day_end = day_start + timedelta(days=1)

    todays = timetable[(timetable["start"] < day_end) & (timetable["end"] > day_start)]
    periods = list(zip(todays["start"], todays["end"]))

    for commitment in prefs.get("commitments", []):
        if commitment["day"] == DAY_NAMES[day.weekday()]:
            periods.append(commitment_times(day, commitment))
    return periods


def overlaps(start, end, periods) -> bool:
    """True if [start, end) overlaps any busy period."""
    return any(start < busy_end and end > busy_start
               for busy_start, busy_end in periods)


def free_slots(week_start: date, timetable: pd.DataFrame, prefs: dict,
               slot_minutes: int = 60) -> pd.DataFrame:
    """Every free study slot in the 7 days from week_start."""
    window = prefs["study_window"]
    focus = prefs.get("best_focus_hours")
    days_off = set(prefs.get("days_off", []))
    step = timedelta(minutes=slot_minutes)
    now = datetime.now(LONDON)

    rows = []
    for offset in range(7):
        day = week_start + timedelta(days=offset)
        day_name = DAY_NAMES[day.weekday()]
        if day_name in days_off:
            continue

        busy = busy_periods(day, timetable, prefs)
        slot_start = at(day, window["start"])
        window_end = at(day, window["end"])

        while slot_start + step <= window_end:
            slot_end = slot_start + step
            if slot_start >= now and not overlaps(slot_start, slot_end, busy):
                in_focus = bool(focus) and (
                    at(day, focus["start"]) <= slot_start
                    and slot_end <= at(day, focus["end"])
                )
                rows.append({"day": day_name, "start": slot_start,
                             "end": slot_end, "focus": in_focus})
            slot_start = slot_end

    return pd.DataFrame(rows, columns=["day", "start", "end", "focus"])


if __name__ == "__main__":
    prefs = load_prefs()
    today = date.today()
    next_monday = today + timedelta(days=7 - today.weekday())

    # Check two weeks: next week might be reading week
    for week_start in [next_monday, next_monday + timedelta(days=7)]:
        week_end = week_start + timedelta(days=7)
        timetable = load_timetable(week_start, week_end, use_local=True)
        slots = free_slots(week_start, timetable, prefs)

        print(f"\nWeek of {week_start:%a %d %b}: {len(timetable)} lectures, "
              f"{len(slots)} free hours ({int(slots['focus'].sum())} in focus time)")
        for day_name, group in slots.groupby("day", sort=False):
            times = ", ".join(f"{s:%H:%M}" for s in group["start"])
            print(f"  {day_name:<10} {len(group):>2}h  {times}")