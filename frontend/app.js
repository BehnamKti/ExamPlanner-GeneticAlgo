/* =========================================================
   STUDY OPTIMIZER — app.js
   Phase 4/5: wired to the local Flask bridge (run.py), which
   calls GA_Optimizer.py directly. No more fake data once the
   user hits Generate — see runGenerate() below.
   ========================================================= */

const API_BASE = ""; // same origin — Flask serves the frontend too

// ---------------------------------------------------------
// STATE
// starts with sample subjects + a placeholder schedule so the
// UI isn't empty before the user runs a real optimization.
// ---------------------------------------------------------

const state = {
  subjects: [
    { id: 1, name: "Mathematics", examDate: "2026-09-08", priority: 5, hoursNeeded: 12 },
    { id: 2, name: "Operating Systems", examDate: "2026-09-12", priority: 4, hoursNeeded: 10 },
    { id: 3, name: "Database Systems", examDate: "2026-09-14", priority: 3, hoursNeeded: 8 },
    { id: 4, name: "Computer Networks", examDate: "2026-09-18", priority: 3, hoursNeeded: 9 },
    { id: 5, name: "Linear Algebra", examDate: "2026-09-20", priority: 4, hoursNeeded: 8 },
    { id: 6, name: "Software Engineering", examDate: "2026-09-24", priority: 2, hoursNeeded: 6 },
  ],

  schedule: { days: [], times: [], sessions: {} }, // populated on first generate
  statistics: [],
  fitnessHistory: null,
  insights: ["Add your subjects, set your availability, then generate a plan."],

  bestFitness: null,
  availableHours: null,
  gaRunning: false,
  hasGenerated: false,
};

// ---------------------------------------------------------
// HELPERS
// ---------------------------------------------------------

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function daysUntil(dateStr) {
  const today = new Date(todayISO());
  const target = new Date(dateStr);
  return Math.ceil((target - today) / (1000 * 60 * 60 * 24));
}

function formatDate(dateStr) {
  const [y, m, d] = dateStr.split("-");
  return `${d} / ${m} / ${y}`;
}

const WEEKDAY_ABBR = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

// Parses "YYYY-MM-DD HH:MM" without going through a timezone-sensitive
// Date constructor, so the displayed schedule always matches what the
// backend actually computed.
function parseSlotStart(startStr) {
  const [datePart, timePart] = startStr.split(" ");
  const [y, m, d] = datePart.split("-").map(Number);
  const weekday = WEEKDAY_ABBR[new Date(Date.UTC(y, m - 1, d)).getUTCDay()];
  return {
    dayLabel: `${weekday} ${String(d).padStart(2, "0")}`,
    sortKey: `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`,
    time: timePart,
  };
}

function priorityBarHTML(priority, size = 5) {
  let html = "";
  for (let i = 1; i <= size; i++) {
    const filled = i <= priority;
    const critical = filled && priority === 5;
    html += `<span class="priority-bar__seg ${filled ? (critical ? "priority-bar__seg--critical" : "priority-bar__seg--filled") : ""}"></span>`;
  }
  return html;
}

// ---------------------------------------------------------
// TRANSFORM: GA schedule list -> grid the UI can render
// ---------------------------------------------------------

function scheduleFromApiResult(sessions) {
  const dayMeta = new Map(); // dayLabel -> sortKey
  const times = new Set();
  const cellMap = {};

  sessions.forEach(item => {
    const { dayLabel, sortKey, time } = parseSlotStart(item.start);
    dayMeta.set(dayLabel, sortKey);
    times.add(time);

    const key = `${dayLabel}-${time}`;
    cellMap[key] = {
      subject: item.subject_name,
      duration: `${item.duration}H`,
      priority: item.priority,
    };
  });

  const days = [...dayMeta.entries()]
    .sort((a, b) => a[1].localeCompare(b[1]))
    .map(([label]) => label);

  const times_sorted = [...times].sort();

  return { days, times: times_sorted, sessions: cellMap };
}

function insightsFromResult(result) {
  const insights = [];
  const allComplete = result.statistics.every(s => s.completion_percentage >= 100);

  insights.push(
    allComplete
      ? "All required study hours were allocated."
      : "Some subjects did not receive their full required hours within the available time."
  );

  const highestPriority = [...result.statistics].sort((a, b) => b.priority - a.priority)[0];
  if (highestPriority) {
    insights.push(`${highestPriority.subject} received the most weight as the highest-priority subject.`);
  }

  const earliestExam = [...result.statistics].sort((a, b) => a.exam_date.localeCompare(b.exam_date))[0];
  if (earliestExam) {
    insights.push(`${earliestExam.subject} was prioritized early, since its exam is soonest.`);
  }

  const lateSessions = result.schedule.filter(item => item.start.slice(0, 10) > item.exam_date);
  insights.push(
    lateSessions.length === 0
      ? "No sessions were scheduled after their subject's exam."
      : `${lateSessions.length} session(s) landed after their subject's exam — check availability range.`
  );

  return insights;
}

// ---------------------------------------------------------
// RENDER: OVERVIEW
// ---------------------------------------------------------

function renderOverview() {
  const totalHours = state.subjects.reduce((sum, s) => sum + s.hoursNeeded, 0);
  const nextExam = state.subjects.length
    ? Math.min(...state.subjects.map(s => daysUntil(s.examDate)))
    : "—";

  document.getElementById("statExams").textContent = state.subjects.length;
  document.getElementById("statHours").textContent = totalHours;
  document.getElementById("statAvailable").textContent = state.availableHours ?? "—";
  document.getElementById("statFitness").textContent =
    state.bestFitness !== null ? state.bestFitness.toFixed(1) : "—";
  document.getElementById("statNextExam").textContent = nextExam;
}

// ---------------------------------------------------------
// RENDER: SUBJECTS
// ---------------------------------------------------------

function renderSubjects() {
  const grid = document.getElementById("subjectGrid");
  grid.innerHTML = state.subjects.map((s, i) => `
    <div class="subject-card" data-id="${s.id}">
      <div class="subject-card__actions">
        <button class="icon-btn" data-action="edit" data-id="${s.id}">E</button>
        <button class="icon-btn" data-action="delete" data-id="${s.id}">X</button>
      </div>
      <div class="subject-card__index">${String(i + 1).padStart(2, "0")}</div>
      <div class="subject-card__name">${s.name}</div>
      <div class="subject-card__row">
        <span class="subject-card__row-label">EXAM</span>
        <span class="subject-card__row-value subject-card__row-value--red">${formatDate(s.examDate)}</span>
      </div>
      <div class="subject-card__row">
        <span class="subject-card__row-label">REQUIRED</span>
        <span class="subject-card__row-value">${s.hoursNeeded} H</span>
      </div>
      <div class="subject-card__row">
        <span class="subject-card__row-label">PRIORITY</span>
        <span class="priority-bar">${priorityBarHTML(s.priority)}</span>
      </div>
    </div>
  `).join("");
}

// ---------------------------------------------------------
// RENDER: TIMELINE
// ---------------------------------------------------------

function renderTimeline() {
  const track = document.getElementById("timeline_track");

  if (!state.subjects.length) {
    track.innerHTML = `<div class="timeline__name">No subjects yet — add one above.</div>`;
    return;
  }

  const sorted = [...state.subjects].sort((a, b) => daysUntil(a.examDate) - daysUntil(b.examDate));
  const maxDays = Math.max(1, ...sorted.map(s => daysUntil(s.examDate)));

  track.innerHTML = sorted.map(s => {
    const days = daysUntil(s.examDate);
    const urgent = days <= 14;
    const height = 20 + (1 - Math.min(days, maxDays) / maxDays) * 80;
    return `
      <div class="timeline__item">
        <div class="timeline__days">${days}D</div>
        <div class="timeline__bar ${urgent ? "timeline__bar--urgent" : ""}" style="height:${height}px"></div>
        <div class="timeline__name">${s.name}</div>
        <div class="timeline__date">${formatDate(s.examDate)}</div>
      </div>
    `;
  }).join("");
}

// ---------------------------------------------------------
// RENDER: SCHEDULE
// ---------------------------------------------------------

function renderSchedule() {
  const grid = document.getElementById("scheduleGrid");
  const { days, times, sessions } = state.schedule;

  if (!days.length) {
    grid.style.gridTemplateColumns = "1fr";
    grid.innerHTML = `<div class="schedule-cell schedule-cell--empty">No plan generated yet. Set your availability and click "Generate Optimal Plan".</div>`;
    return;
  }

  grid.style.gridTemplateColumns = `80px repeat(${days.length}, 1fr)`;

  let html = `<div class="schedule-cell schedule-cell--head"></div>`;
  days.forEach(d => {
    html += `<div class="schedule-cell schedule-cell--head">${d}</div>`;
  });

  times.forEach(t => {
    html += `<div class="schedule-cell schedule-cell--time">${t}</div>`;
    days.forEach(d => {
      const session = sessions[`${d}-${t}`];
      if (session) {
        html += `
          <div class="schedule-cell schedule-cell--session" title="Priority ${session.priority}">
            <div class="session__subject">${session.subject}${session.priority === 5 ? ' <span class="session__priority-mark">!</span>' : ""}</div>
            <div class="session__duration">${session.duration}</div>
          </div>`;
      } else {
        html += `<div class="schedule-cell schedule-cell--empty">—</div>`;
      }
    });
  });

  grid.innerHTML = html;
}

// ---------------------------------------------------------
// RENDER: INSIGHTS
// ---------------------------------------------------------

function renderInsights() {
  const list = document.getElementById("insightList");
  list.innerHTML = state.insights.map(text => `
    <li><span class="insight-mark">✓</span><span>${text}</span></li>
  `).join("");
}

// ---------------------------------------------------------
// RENDER: FITNESS CHART (real generation-by-generation history)
// ---------------------------------------------------------

function renderFitnessChart() {
  const chart = document.getElementById("fitnessChart");

  if (!state.fitnessHistory) {
    chart.innerHTML = "";
    return;
  }

  const { best, average, worst } = state.fitnessHistory;
  const allValues = [...best, ...average, ...worst];
  const max = Math.max(...allValues, 1);
  const min = Math.min(...allValues, 0);
  const range = max - min || 1;

  const toPct = v => ((v - min) / range) * 100;

  chart.innerHTML = best.map((_, i) => `
    <div class="fitness-bar-group">
      <div class="fitness-bar fitness-bar--worst" style="height:${toPct(worst[i])}%; position:absolute;"></div>
      <div class="fitness-bar fitness-bar--avg" style="height:${toPct(average[i])}%; position:absolute;"></div>
      <div class="fitness-bar fitness-bar--best" style="height:${toPct(best[i])}%; position:absolute;"></div>
    </div>
  `).join("");
}

// ---------------------------------------------------------
// GENERATE PLAN — calls the real GA through the Flask bridge
// ---------------------------------------------------------

function readAvailability() {
  return {
    startDate: document.getElementById("rangeStart").value,
    endDate: document.getElementById("rangeEnd").value,
    dailyHours: Number(document.getElementById("dailyHours").value),
    preferredPeriod: document.getElementById("preferredPeriod").value,
  };
}

function readGaSettings() {
  return {
    populationSize: Number(document.getElementById("gaPopulation").value),
    generations: Number(document.getElementById("gaGenerations").value),
    mutationRate: Number(document.getElementById("gaMutation").value),
    elitismCount: Number(document.getElementById("gaElitism").value),
  };
}

function setProgressState(text) {
  document.getElementById("progressState").textContent = text;
}

async function runGenerate() {
  if (state.gaRunning) return;

  const availability = readAvailability();
  if (!availability.startDate || !availability.endDate) {
    alert("Set a start and end date under Available Study Time first.");
    return;
  }
  if (!state.subjects.length) {
    alert("Add at least one subject first.");
    return;
  }

  state.gaRunning = true;

  const btn = document.getElementById("generateBtn");
  const display = document.getElementById("progressDisplay");
  const fill = document.getElementById("progressFill");
  const meta = document.getElementById("progressMeta");
  const badge = document.getElementById("statusBadge");

  btn.disabled = true;
  display.hidden = false;
  badge.innerHTML = `<span class="dot dot--running"></span> RUNNING`;
  setProgressState("INITIALIZING");
  fill.style.width = "0%";
  meta.textContent = "CONTACTING LOCAL OPTIMIZER…";

  try {
    setProgressState("OPTIMIZING");

    const response = await fetch(`${API_BASE}/api/generate-plan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        subjects: state.subjects,
        availability,
        gaSettings: readGaSettings(),
      }),
    });

    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "The optimizer returned an error.");
    }

    setProgressState("EVALUATING");

    // We only get the final result back from this synchronous call, but it
    // includes the real per-generation history — so replay that history on
    // the progress bar and fitness chart instead of showing a fake ramp.
    // True live per-generation updates are future work (see Phase 6).
    await replayHistory(result.history, fill, meta);

    state.bestFitness = result.best_fitness;
    state.schedule = scheduleFromApiResult(result.schedule);
    state.statistics = result.statistics;
    state.insights = insightsFromResult(result);
    state.fitnessHistory = result.history;
    state.availableHours = result.schedule.reduce((sum, s) => sum + s.duration, 0);
    state.hasGenerated = true;

    setProgressState("✓ OPTIMAL PLAN FOUND");
    badge.innerHTML = `<span class="dot dot--done"></span> DONE`;

    renderOverview();
    renderSchedule();
    renderInsights();
    renderFitnessChart();
  } catch (err) {
    setProgressState("✕ OPTIMIZATION FAILED");
    meta.textContent = err.message;
    badge.innerHTML = `<span class="dot dot--idle"></span> ERROR`;
  } finally {
    btn.disabled = false;
    state.gaRunning = false;
  }
}

function replayHistory(history, fill, meta) {
  return new Promise(resolve => {
    const total = history.best.length;
    let gen = 0;
    const interval = setInterval(() => {
      gen += Math.max(1, Math.ceil(total / 60));
      if (gen >= total) gen = total;
      fill.style.width = `${(gen / total) * 100}%`;
      meta.textContent = `GENERATION ${String(gen).padStart(3, "0")} / ${total}`;
      if (gen >= total) {
        clearInterval(interval);
        resolve();
      }
    }, 20);
  });
}

// ---------------------------------------------------------
// MODAL — add / edit subject
// ---------------------------------------------------------

let editingId = null;

function openModal(subject = null) {
  editingId = subject ? subject.id : null;
  document.getElementById("modalTitle").textContent = subject ? "EDIT SUBJECT" : "ADD SUBJECT";
  document.getElementById("formName").value = subject ? subject.name : "";
  document.getElementById("formDate").value = subject ? subject.examDate : "";
  document.getElementById("formHours").value = subject ? subject.hoursNeeded : 10;
  document.getElementById("formPriority").value = subject ? subject.priority : 3;
  updatePriorityPreview();
  document.getElementById("subjectModal").hidden = false;
}

function closeModal() {
  document.getElementById("subjectModal").hidden = true;
}

function updatePriorityPreview() {
  const val = Number(document.getElementById("formPriority").value);
  document.getElementById("formPriorityPreview").innerHTML = priorityBarHTML(val);
}

function saveSubjectFromForm() {
  const name = document.getElementById("formName").value.trim();
  const examDate = document.getElementById("formDate").value;
  const hoursNeeded = Number(document.getElementById("formHours").value);
  const priority = Number(document.getElementById("formPriority").value);

  if (!name || !examDate || !hoursNeeded) {
    alert("Name, exam date, and required hours are all needed.");
    return;
  }

  if (editingId) {
    const s = state.subjects.find(s => s.id === editingId);
    Object.assign(s, { name, examDate, hoursNeeded, priority });
  } else {
    const id = Math.max(0, ...state.subjects.map(s => s.id)) + 1;
    state.subjects.push({ id, name, examDate, hoursNeeded, priority });
  }

  closeModal();
  renderSubjects();
  renderTimeline();
  renderOverview();
}

// ---------------------------------------------------------
// EVENT WIRING
// ---------------------------------------------------------

document.getElementById("addSubjectBtn").addEventListener("click", () => openModal());
document.getElementById("modalClose").addEventListener("click", closeModal);
document.getElementById("formCancel").addEventListener("click", closeModal);
document.getElementById("formSave").addEventListener("click", saveSubjectFromForm);
document.getElementById("formPriority").addEventListener("input", updatePriorityPreview);

document.getElementById("subjectGrid").addEventListener("click", (e) => {
  const btn = e.target.closest(".icon-btn");
  if (!btn) return;
  const id = Number(btn.dataset.id);
  const subject = state.subjects.find(s => s.id === id);

  if (btn.dataset.action === "edit") {
    openModal(subject);
  } else if (btn.dataset.action === "delete") {
    state.subjects = state.subjects.filter(s => s.id !== id);
    renderSubjects();
    renderTimeline();
    renderOverview();
  }
});

document.getElementById("advToggle").addEventListener("click", () => {
  const panel = document.getElementById("advPanel");
  panel.hidden = !panel.hidden;
  document.getElementById("advToggle").textContent = panel.hidden ? "SHOW ▾" : "HIDE ▴";
});

document.getElementById("generateBtn").addEventListener("click", runGenerate);

// ---------------------------------------------------------
// INIT
// ---------------------------------------------------------

function setDefaultAvailability() {
  const latestExam = state.subjects.reduce(
    (max, s) => (s.examDate > max ? s.examDate : max),
    state.subjects[0]?.examDate ?? todayISO()
  );
  document.getElementById("rangeStart").value = todayISO();
  document.getElementById("rangeEnd").value = latestExam;
}

function init() {
  setDefaultAvailability();
  renderOverview();
  renderSubjects();
  renderTimeline();
  renderSchedule();
  renderInsights();
  renderFitnessChart();
}

init();
