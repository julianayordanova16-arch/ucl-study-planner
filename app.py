"""UCL Study Planner: upload course material and get it scored."""
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from pypdf.errors import PdfReadError

from calendar_io import LONDON, get_modules, load_timetable
from scoring import score_item
from store import KINDS, add_item, list_items, update_item

UPLOAD_DIR = Path("data/uploads")

st.set_page_config(page_title="UCL Study Planner", layout="wide")


@st.cache_data(ttl=3600)
def module_list() -> list[str]:
    """Module names from the timetable (remembered for an hour)."""
    today = date.today()
    timetable = load_timetable(today - timedelta(days=60), today + timedelta(days=60),
                               use_local=True)
    return get_modules(timetable)


st.title("UCL Study Planner")
st.caption("Drop in course material, get a difficulty score, and plan your week.")

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

if submitted:
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
items = list_items()

if not items:
    st.write("Nothing added yet.")
else:
    table = pd.DataFrame(items)[["module", "kind", "filename", "difficulty", "est_hours", "due"]]
    table["due"] = (pd.to_datetime(table["due"], utc=True)
                    .dt.tz_convert("Europe/London")
                    .dt.strftime("%a %d %b %H:%M"))
    table = table.sort_values("difficulty", ascending=False)
    st.dataframe(table, hide_index=True)