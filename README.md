# ExamPlanner-GeneticAlgo

A desktop study planner that uses a Genetic Algorithm to turn your exams,
priorities, and available time into an optimized study schedule — no
manual timetabling required.

Built as a learning/portfolio project: the optimizer, the local bridge,
and the frontend are all kept deliberately simple and easy to explain.

## What it does

1. You add your subjects — name, exam date, priority (1–5), required
   study hours.
2. You define your available study time — date range, daily hours,
   preferred time of day.
3. A Genetic Algorithm (`GA_Optimizer.py`) searches for a schedule that:
   - covers each subject's required hours,
   - favors higher-priority subjects,
   - studies subjects earlier when their exam is sooner,
   - never schedules a session after that subject's exam.
4. The result renders as a visual weekly schedule, plus insights
   explaining *why* the plan looks the way it does, and a chart of the
   GA's fitness improving across generations.

## Tech stack

- **Frontend** — plain HTML / CSS / JavaScript, no framework.
- **Bridge** — Flask (`run.py`), serving the frontend and one JSON
  endpoint (`/api/generate-plan`).
- **Optimizer** — pure Python (`GA_Optimizer.py`): chromosomes, roulette
  selection, single-point crossover, mutation, elitism.

Everything runs locally. No cloud, no accounts, no database.

## Get the app

**Just want to run it?** Download the latest `.exe` from
[Releases](../../releases) — no Python required.

**Want to run from source or make changes?**

```
pip install -r requirements.txt
python run.py
```

This opens `http://127.0.0.1:5000` in your browser automatically.

## Building your own .exe

```
pip install pyinstaller
python -m PyInstaller --onefile --add-data "frontend;frontend" --name ExamPlanner run.py
```

This creates `dist/ExamPlanner.exe`. It isn't tracked in this repo (see
`.gitignore`) — publish new builds as a [GitHub Release](../../releases)
rather than committing them.

## Project structure

```
ExamPlanner-GeneticAlgo/
├── run.py              Flask bridge: serves the frontend, calls the GA
├── GA_Optimizer.py      the genetic algorithm itself
├── requirements.txt
├── LICENSE
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── README.md
```

## need some work due to minor limitations


