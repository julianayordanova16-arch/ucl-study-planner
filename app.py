"""UCL Study Planner: upload course material and get it scored."""
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from pypdf.errors import PdfReadError

from calendar_io import LONDON, get_modules, load_prefs, load_timetable
from export_ics import plan_to_ics
from free_time import free_slots
from scheduler import merge_blocks, plan_week
from scoring import score_item
from store import KINDS, add_item, list_items, update_item
from demo import DEMO_MODULES, demo_items, demo_timetable

UPLOAD_DIR = Path("data/uploads")
# Public demo: no real timetable on this machine, or forced with DEMO_MODE=1
DEMO = os.getenv("DEMO_MODE") == "1" or not Path("data/timetable.ics").exists()

st.set_page_config(page_title="UCL Study Planner", layout="wide")


@st.cache_data(ttl=3600)
def module_list() -> list[str]:
    """Module names from the timetable (remembered for an hour)."""
    if DEMO:
        return DEMO_MODULES
    today = date.today()
    """Module names from the timetable (remembered for an hour)."""
    today = date.today()
    timetable = load_timetable(today - timedelta(days=60), today + timedelta(days=60),
                               use_local=True)
    return get_modules(timetable)


st.title("UCL Study Planner")
st.caption("Drop in course material, get a difficulty score, and plan your week.")
if DEMO:
    st.info("**Demo mode:** made-up modules, timetable and scores. "
            "Uploading and AI scoring are switched off in the public demo.")

# ---------- 1. Upload ----------
st.header("1. Add course material")

with st.form("upload", clear_on_submit=True):
    files = st.file_uploader("Drag and drop PDFs here", type="pdf",
                             accept_multiple_files=True)
    col1, col2 = st.columns(2)
    module = col1.selectbox("Module", module_list())
    kind = col2.selectbox("Type", KINDS)

    has_deadline = st.checkbox("This has a deadline (otherwise: review within 7 days)")
    col3, col4 = st.columns(2)
    due_day = col3.date_input("Due date", value=date.today() + timedelta(days=7))
    due_time = col4.time_input("Due time", value=time(17, 0))

    submitted = st.form_submit_button("Add and score")

if submitted and DEMO:
    st.warning("Uploads are switched off in the demo. Run it locally to use your own files.")
elif submitted:
    if not files:
        st.warning("Choose at least one PDF first.")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    due = datetime.combine(due_day, due_time, tzinfo=LONDON) if has_deadline else None

    for file in files or []:
        path = UPLOAD_DIR / file.name
        path.write_bytes(file.getbuffer())

        try:
            item = add_item(path, module, kind, due)
        except PdfReadError:
            st.error(f"{file.name}: couldn't read this PDF. Is it damaged?")
            continue

        if item["difficulty"] is not None:
            st.info(f"{file.name} was already added (difficulty {item['difficulty']}/5).")
            continue

        with st.spinner(f"Scoring {file.name}…"):
            result = score_item(item)
        update_item(item["id"], **result)
        st.success(f"**{file.name}**: difficulty {result['difficulty']}/5, "
                   f"about {result['est_hours']}h. {result['reason']}")

# ---------- 2. Items ----------
st.header("2. Your items")
items = demo_items() if DEMO else list_items()

if not items:
    st.write("Nothing added yet.")
else:
    table = pd.DataFrame(items)[["module", "kind", "filename", "difficulty", "est_hours", "due", "reason"]]
    table["due"] = (pd.to_datetime(table["due"], utc=True)
                    .dt.tz_convert("Europe/London")
                    .dt.strftime("%a %d %b %H:%M"))
    table = table.sort_values("difficulty", ascending=False)
    st.dataframe(table, hide_index=True)

# ---------- 3. Plan ----------
st.header("3. Your study plan (next 7 days)")

if not DEMO:
    if st.sidebar.button("Refresh timetable from UCL"):
        with st.spinner("Downloading your latest timetable…"):
            load_timetable(date.today(), date.today() + timedelta(days=1), use_local=False)
        st.cache_data.clear()
        st.sidebar.success("Timetable updated")

if not items:
    st.write("Add some course material first.")
else:
    prefs = load_prefs("prefs.example.yaml" if DEMO else "prefs.yaml")
    today = date.today()
    timetable = demo_timetable(today) if DEMO else load_timetable(
        today, today + timedelta(days=7), use_local=True)
    slots = free_slots(today, timetable, prefs)
    plan, unplaced = plan_week(items, slots, prefs)

    col1, col2, col3 = st.columns(3)
    col1.metric("Study hours planned", len(plan))
    col2.metric("Free hours available", len(slots))
    col3.metric("Items that don't fit", len(unplaced))

    for u in unplaced:
        st.warning(f"**{u['task']}** ({u['file']}): {u['missing_hours']}h doesn't fit "
                   f"before it's due ({u['due']:%a %d %b %H:%M}). Consider dropping "
                   f"something, or raising your daily maximum in prefs.yaml.")

    if plan.empty:
        st.info("Nothing to plan right now.")
    else:
        merged = merge_blocks(plan)
        for day, group in merged.groupby(merged["start"].dt.date):
            st.subheader(f"{day:%A %d %b}")
            day_table = pd.DataFrame({
                "time": group["start"].dt.strftime("%H:%M") + "–" + group["end"].dt.strftime("%H:%M"),
                "study": group["task"],
                "file": group["file"],
                "difficulty": group["difficulty"],
            })
            st.dataframe(day_table, hide_index=True)

        st.download_button(
            "Download plan for your calendar (.ics)",
            data=plan_to_ics(plan),
            file_name="study_plan.ics",
            mime="text/calendar",
        )