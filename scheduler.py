"""Turn free slots + scored items into a weekly study plan."""
import math
from datetime import date, datetime, timedelta

import pandas as pd

from calendar_io import load_prefs, load_timetable
from free_time import free_slots
from store import list_items

MAX_HOURS_PER_ITEM_PER_DAY = 2   # spread each item over several days
HARD = 4                         # difficulty at or above this counts as hard
KIND_ORDER = {"Lecture notes": 0, "Tutorial sheet": 1, "Quiz": 2}   # notes before problems

def build_tasks(items: list[dict]) -> list[dict]:
    """Scored items -> tasks: most urgent first, then notes before sheets, then hardest."""
    tasks = []
    for item in items:
        if item["difficulty"] is None or item["est_hours"] is None:
            continue  # not scored yet
        tasks.append({
            "id": item["id"],
            "name": f"{item['module']} – {item['kind']}",
            "file": item["filename"],
            "kind": item["kind"],
            "difficulty": item["difficulty"],
            "blocks": math.ceil(item["est_hours"]),   # 2.5h -> 3 one-hour blocks
            "due": datetime.fromisoformat(item["due"]),
        })
    tasks.sort(key=lambda t: (t["due"], KIND_ORDER.get(t["kind"], 9), -t["difficulty"]))
    return tasks


def plan_week(items: list[dict], slots: pd.DataFrame, prefs: dict):
    """Greedily fill free slots with study blocks. Returns (plan, unplaced)."""
    max_per_day = prefs.get("max_study_hours_per_day", 4)
    slots = slots.sort_values("start").reset_index(drop=True)

    taken = set()            # slot numbers already used
    hours_on_day = {}        # date -> hours planned that day
    item_hours_on_day = {}   # (item id, date) -> hours of that item that day
    plan, unplaced = [], []

    for task in build_tasks(items):
        placed = 0
        # Hard tasks: first pass uses focus slots only, second pass uses any slot
        passes = [True, False] if task["difficulty"] >= HARD else [False]

        for focus_only in passes:
            for i, slot in slots.iterrows():
                if placed == task["blocks"]:
                    break
                day = slot["start"].date()
                if (i in taken
                        or slot["end"] > task["due"]
                        or hours_on_day.get(day, 0) >= max_per_day
                        or item_hours_on_day.get((task["id"], day), 0) >= MAX_HOURS_PER_ITEM_PER_DAY
                        or (focus_only and not slot["focus"])):
                    continue
                taken.add(i)
                hours_on_day[day] = hours_on_day.get(day, 0) + 1
                item_hours_on_day[(task["id"], day)] = item_hours_on_day.get((task["id"], day), 0) + 1
                placed += 1
                plan.append({
                    "start": slot["start"], "end": slot["end"],
                    "task": task["name"], "file": task["file"],
                    "difficulty": task["difficulty"],
                })

        if placed < task["blocks"]:
            unplaced.append({
                "task": task["name"], "file": task["file"],
                "missing_hours": task["blocks"] - placed, "due": task["due"],
            })

    plan_df = pd.DataFrame(plan, columns=["start", "end", "task", "file", "difficulty"])
    return plan_df.sort_values("start").reset_index(drop=True), unplaced


if __name__ == "__main__":
    prefs = load_prefs()
    today = date.today()
    week_start = today - timedelta(days=today.weekday())   # this Monday
    week_end = week_start + timedelta(days=7)

    timetable = load_timetable(week_start, week_end, use_local=True)
    slots = free_slots(week_start, timetable, prefs)        # past hours are skipped
    plan, unplaced = plan_week(list_items(), slots, prefs)

    print(f"Plan for week of {week_start:%a %d %b}: {len(plan)} study hours "
          f"from {len(slots)} free hours\n")

    if plan.empty:
        print("Nothing planned. Are your items scored and not overdue?")
    else:
        for day, group in plan.groupby(plan["start"].dt.date):
            print(f"{day:%A %d %b}  ({len(group)}h)")
            for _, row in group.iterrows():
                print(f"  {row['start']:%H:%M}-{row['end']:%H:%M}  "
                      f"{row['task']}  (difficulty {row['difficulty']})")
            print()

    for u in unplaced:
        print(f"WARNING: {u['missing_hours']}h of '{u['task']}' doesn't fit "
              f"before it's due ({u['due']:%a %d %b %H:%M})")