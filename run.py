"""
Local bridge between the frontend (HTML/CSS/JS) and GA_Optimizer.py.

Run with:

    python run.py

Then open:

    http://127.0.0.1:5000

This process is entirely local — no cloud, no auth, no external database.
Flask is used only as a thin static-file + JSON-endpoint server.
"""

from datetime import datetime, timedelta

from flask import Flask, jsonify, request, send_from_directory

from GA_Optimizer import ExamPlannerGA

app = Flask(__name__, static_folder="frontend", static_url_path="")

# Hour windows for each "preferred study period" option in the UI.
# (start_hour, end_hour) — end_hour is exclusive.
PERIOD_WINDOWS = {
    "morning": (7, 12),
    "afternoon": (12, 18),
    "evening": (18, 23),
}


# ---------------------------------------------------------------
# STATIC FRONTEND
# ---------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# ---------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------

def build_study_slots(start_date, end_date, daily_hours, preferred_period):
    """
    Turn the simple availability form (start date, end date, daily hours,
    preferred period) into the list of {"start", "end"} slots the GA expects.

    Kept intentionally simple: one block of `daily_hours` consecutive
    one-hour slots per day, inside the chosen period's window. Splitting
    this into multiple blocks per day, weekends-off, etc. is future work
    (see "Future constraints" in the project brief) and isn't needed yet.
    """

    period_start, period_end = PERIOD_WINDOWS.get(
        preferred_period, PERIOD_WINDOWS["afternoon"]
    )
    window_size = period_end - period_start

    hours_per_day = max(1, min(daily_hours, window_size))

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    if end < start:
        raise ValueError("End date must be on or after the start date.")

    slots = []
    current_day = start

    while current_day <= end:
        for hour_offset in range(hours_per_day):
            slot_start = current_day.replace(
                hour=period_start + hour_offset, minute=0, second=0, microsecond=0
            )
            slot_end = slot_start + timedelta(hours=1)
            slots.append(
                {
                    "start": slot_start.strftime("%Y-%m-%d %H:%M"),
                    "end": slot_end.strftime("%Y-%m-%d %H:%M"),
                }
            )
        current_day += timedelta(days=1)

    return slots


def error_response(message, status=400):
    return jsonify({"error": message}), status


# ---------------------------------------------------------------
# API
# ---------------------------------------------------------------

@app.route("/api/generate-plan", methods=["POST"])
def generate_plan():
    payload = request.get_json(silent=True)

    if not payload:
        return error_response("Request body must be JSON.")

    subjects = payload.get("subjects")
    availability = payload.get("availability", {})
    ga_settings = payload.get("gaSettings", {})

    if not subjects:
        return error_response("At least one subject is required.")

    required_availability_fields = ["startDate", "endDate", "dailyHours", "preferredPeriod"]
    missing = [f for f in required_availability_fields if f not in availability]
    if missing:
        return error_response(f"Missing availability field(s): {', '.join(missing)}.")

    # Translate frontend subject shape -> GA subject shape.
    ga_subjects = [
        {
            "name": s["name"],
            "priority": s["priority"],
            "hours_needed": s["hoursNeeded"],
            "exam_date": s["examDate"],
        }
        for s in subjects
    ]

    try:
        study_slots = build_study_slots(
            availability["startDate"],
            availability["endDate"],
            int(availability["dailyHours"]),
            availability["preferredPeriod"],
        )
    except ValueError as exc:
        return error_response(str(exc))

    if not study_slots:
        return error_response("The selected date range produced no study slots.")

    try:
        planner = ExamPlannerGA(
            subjects=ga_subjects,
            study_slots=study_slots,
            population_size=int(ga_settings.get("populationSize", 40)),
            generations=int(ga_settings.get("generations", 100)),
            mutation_rate=float(ga_settings.get("mutationRate", 0.10)),
            elitism_count=int(ga_settings.get("elitismCount", 2)),
        )
        result = planner.optimize()
    except ValueError as exc:
        return error_response(str(exc))

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
