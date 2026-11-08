"""Save and load your course items."""
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from calendar_io import LONDON
from pdf_text import extract_text

STORE_PATH = Path("data/store.json")
DEFAULT_DAYS_TO_REVIEW = 7
KINDS = ["Lecture notes", "Tutorial sheet", "Quiz"]


def load_items() -> list[dict]:
    """Every saved item (empty list if nothing saved yet)."""
    if not STORE_PATH.exists():
        return []
    return json.loads(STORE_PATH.read_text())


def save_items(items: list[dict]) -> None:
    """Write all items to data/store.json."""
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(json.dumps(items, indent=2))


def add_item(pdf_path, module: str, kind: str, due: datetime | None = None) -> dict:
    """Add a PDF to the store. If it's already there, return the existing item."""
    pdf_path = Path(pdf_path)
    items = load_items()
    for item in items:
        if item["filename"] == pdf_path.name:
            return item

    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")

    now = datetime.now(LONDON)
    info = extract_text(pdf_path)
    item = {
        "id": uuid.uuid4().hex[:8],
        "filename": pdf_path.name,
        "path": str(pdf_path),
        "module": module,
        "kind": kind,
        "uploaded_at": now.isoformat(timespec="minutes"),
        "due": (due or now + timedelta(days=DEFAULT_DAYS_TO_REVIEW)).isoformat(timespec="minutes"),
        "pages": info["pages"],
        "chars": info["chars"],
        "scanned": info["scanned"],
        # Filled in on Day 5 by the LLM
        "difficulty": None,
        "est_hours": None,
        "topics": [],
        "reason": None,
    }
    items.append(item)
    save_items(items)
    return item


def update_item(item_id: str, **changes) -> dict:
    """Change some fields of one item, e.g. update_item('ab12cd34', difficulty=4)."""
    items = load_items()
    for item in items:
        if item["id"] == item_id:
            item.update(changes)
            save_items(items)
            return item
    raise KeyError(f"No item with id {item_id}")


def list_items() -> list[dict]:
    """All items, soonest due first."""
    return sorted(load_items(), key=lambda item: item["due"])


if __name__ == "__main__":
    # (file path, module name, type, due date or None for "7 days from now")
    TEST_ITEMS = [
        ("data/PHAS0022-2026-27-Section4-part2.pdf", "Quantum Physics", "Lecture notes", None),
        ("data/PHAS0022-PSweek4-2026.pdf", "Quantum Physics", "Tutorial sheet", None),
        ("data/PHAS0025_Chapter_3.pdf", "Mathematical Methods III", "Lecture notes", None),
        ("data/Prob_Legendre_2026-27_q.pdf", "Mathematical Methods III", "Tutorial sheet", None),
    ]

    for path, module, kind, due in TEST_ITEMS:
        add_item(path, module, kind, due)

    for item in list_items():
        flag = "SCANNED" if item["scanned"] else ""
        print(f"{item['id']}  {item['module']:<26} {item['kind']:<15} "
              f"due {item['due'][:10]}  {item['pages']:>3}p  {flag}")