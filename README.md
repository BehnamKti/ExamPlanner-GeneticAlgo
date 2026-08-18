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

## cureently in works due to some limitations
