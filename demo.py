"""Made-up data so the public demo works without anyone's real timetable."""
from datetime import date, datetime, time, timedelta

import pandas as pd

from calendar_io import LONDON

DEMO_MODULES = ["Classical Mechanics", "Thermal Physics", "Linear Algebra", "Electronics Lab"]

# (weekday 0=Mon, start hour, length in hours, module, session type)
WEEKLY_SESSIONS = [
    (0, 10, 2, "Classical Mechanics", "Lecture"),
    (1, 9, 1, "Linear Algebra", "Lecture"),
    (1, 14, 3, "Electronics Lab", "Lab"),
    (2, 11, 2, "Thermal Physics", "Lecture"),
    (3, 10, 1, "Linear Algebra", "Problem class"),
    (4, 9, 2, "Classical Mechanics", "Lecture"),
]


def _at(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=LONDON)


def demo_timetable(start: date, days: int = 7) -> pd.DataFrame:
    """A fake weekly timetable, in the same shape as load_timetable()."""
    rows = []
    for offset in range(days):
        day = start + timedelta(days=offset)
        for weekday, hour, length, module, kind in WEEKLY_SESSIONS:
            if day.weekday() == weekday:
                rows.append({"module": module, "type": kind,
                             "start": _at(day, hour), "end": _at(day, hour + length),
                             "location": "Demo building"})
    df = pd.DataFrame(rows, columns=["module", "type", "start", "end", "location"])
    return df.sort_values("start").reset_index(drop=True)


def demo_items() -> list[dict]:
    """Fake, already-scored items. Due dates move with today so the demo never goes stale."""
    today = date.today()

    def item(n, module, kind, difficulty, hours, due_in_days, reason, topics):
        return {
            "id": f"demo{n}", "filename": f"demo_{n}.pdf", "path": "",
            "module": module, "kind": kind, "uploaded_at": "",
            "due": _at(today + timedelta(days=due_in_days), 17).isoformat(timespec="minutes"),
            "pages": 0, "chars": 0, "scanned": False,
            "difficulty": difficulty, "est_hours": hours, "topics": topics, "reason": reason,
        }

    return [
        item(1, "Classical Mechanics", "Lecture notes", 4, 3.0, 4,
             "Lagrangian mechanics introduces several new derivations.", ["Lagrangian", "Euler-Lagrange"]),
        item(2, "Classical Mechanics", "Tutorial sheet", 4, 3.5, 6,
             "Multi-step problems applying the Euler-Lagrange equation.", ["Constraints", "Generalised coordinates"]),
        item(3, "Thermal Physics", "Lecture notes", 3, 2.0, 5,
             "Standard introduction to entropy using familiar maths.", ["Entropy", "Second law"]),
        item(4, "Linear Algebra", "Tutorial sheet", 2, 1.5, 3,
             "Short practice on eigenvalues with familiar methods.", ["Eigenvalues"]),
        item(5, "Linear Algebra", "Quiz", 2, 0.5, 2,
             "Short multiple-choice quiz on last week's material.", ["Diagonalisation"]),
        item(6, "Thermal Physics", "Tutorial sheet", 5, 4.0, 7,
             "Long sheet with unfamiliar statistical mechanics derivations.", ["Partition function", "Boltzmann"]),
    ]