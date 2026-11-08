# Project notes

## Day 1 – Fri 6 Nov
- Set up repo, venv, .gitignore
- Timetable feed works (128 events)

## Day 2 – Sun 8 Nov
- calendar_io.py: timetable -> clean table of modules + session types
- prefs.yaml: my study window, days off, commitments (kept private)

**Why is the timetable link in .env and not in the code?**
- The link works like a password. It has a private token in it, so anyone who has it can see your timetable. Your code goes on GitHub, where anyone can read it, but .env is listed in .gitignore, so it never leaves your laptop. Keeping secrets separate from code also means you can change the link (if it ever leaks) without touching the code, and someone else could run your project with their timetable just by making their own .env.


**What does use_local=True save me from?**
- It makes the code read the saved copy in data/timetable.ics instead of downloading from UCL every time. That saves you from:

waiting for a download on every test run,
your code breaking when you’re offline or UCL’s server is slow,
hammering UCL’s server while you’re testing the same thing 20 times.

The trade-off is that the local copy can be out of date, so you switch to use_local=False when you want the latest timetable.


**Why convert every time to Europe/London?**
- Times in calendars come in different forms. Some are in UTC (ending in Z), some have a time zone attached, and some have none. On top of that, the UK switches between BST (UTC+1) in summer and GMT (UTC+0) in winter; the clocks changed on 25 Oct. If you mix forms, a 9:00 lecture could show up as 8:00 or 10:00, or Python could refuse to compare the times at all. Converting everything to London time means every time is in one consistent form and matches your wall clock, so comparisons like “does this lecture overlap this free hour?” are always correct.


## Day 3 – Sun 8 Nov
- free_time.py: finds free study hours

**Why is the overlap rule `start < busy_end and end > busy_start`?**
- Two time periods overlap unless one finishes before the other begins. The rule checks both sides:

start < busy_end: the free slot starts before the busy thing ends
end > busy_start: the free slot ends after the busy thing starts

If both are true, they overlap. With your Monday padwork:

Slot 20:00–21:00 vs padwork 20:20–22:15
20:00 < 22:15 ✅ and 21:00 > 20:20 ✅ → overlap, so the slot is removed.
Slot 19:00–20:00: 19:00 < 22:15 ✅ but 20:00 > 20:20 ❌ → no overlap, so the slot is kept.

Using < rather than <= means a slot ending at exactly 18:00 doesn’t clash with something starting at 18:00. Back-to-back is allowed.

**Why skip slots before now?**
- You can’t study in the past. If you run the planner on Wednesday afternoon, Monday’s and Tuesday’s free hours have already gone. If they weren’t skipped, the scheduler would happily put study blocks there, and you’d get a plan that looks fine but has work scheduled on days that are already over.


**Why doesn't this file apply the 4-hours-a-day limit?**
- Because it’s a different question. free_time.py answers “when am I available?”, which is a fact about your week. The 4-hour limit is about “how much should I actually study?”, which is a planning decision that belongs to the scheduler (Day 7). Keeping them separate means each file does one job. You can test them separately and change one without breaking the other: for example, a lighter limit in exam week doesn’t change when you’re free. Programmers call this separation of concerns, and it’s a good phrase to use in interviews.


## Day 4 – Sun 8 Nov
- pdf_text.py: extracts text, flags scanned PDFs, survives broken files
- store.py: saves items to data/store.json

**Why rate the PDFs myself before using the AI?**

**Why does add_item check the filename first?**

**Why are difficulty and est_hours None for now?**