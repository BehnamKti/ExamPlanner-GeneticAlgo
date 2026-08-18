# Study Optimizer — Student Exam Planner

## Run it

```
pip install -r requirements.txt
python run.py
```

Then open http://127.0.0.1:5000 in a browser.

## How it fits together

```
frontend/ (HTML + CSS + JS)
        ↓  fetch("/api/generate-plan")
run.py (Flask bridge)
        ↓  builds study slots from your availability form
GA_Optimizer.py (ExamPlannerGA)
        ↓  returns schedule, statistics, fitness history
run.py
        ↓  JSON response
frontend renders schedule, insights, fitness chart
```

`run.py` also serves the frontend itself, so there's only one process
to run — no separate dev server.

## Current limitations (by design, for now)

- The progress bar/fitness chart during "Generate" replays the GA's real
  per-generation history *after* the optimizer finishes, rather than
  streaming it live. True live progress needs a background thread or
  WebSocket and is intentionally deferred (see Phase 6 in the project brief).
- Availability only supports one contiguous hour block per day, inside a
  single "preferred period" window (morning/afternoon/evening). Multiple
  blocks per day, days off, and weekend handling are future constraints.
