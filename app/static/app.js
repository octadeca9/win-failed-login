"use strict";

const state = {
  events: [],
  filtered: [],
  tasks: [],
  sort: { key: "record_id", dir: 1 },
};

async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
}

/* ---------- Log viewer ---------- */

function uniqueSorted(key) {
  return [...new Set(state.events.map((e) => e[key]).filter((v) => v && v !== "-"))].sort();
}

function populateFilters() {
  const userSel = document.getElementById("filter-user");
  const ipSel = document.getElementById("filter-ip");
  for (const u of uniqueSorted("target_user")) userSel.add(new Option(u, u));
  for (const ip of uniqueSorted("source_ip")) ipSel.add(new Option(ip, ip));
}

function applyFilters() {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const eid = document.getElementById("filter-eventid").value;
  const user = document.getElementById("filter-user").value;
  const ip = document.getElementById("filter-ip").value;

  state.filtered = state.events.filter((e) => {
    if (eid && String(e.event_id) !== eid) return false;
    if (user && e.target_user !== user) return false;
    if (ip && e.source_ip !== ip) return false;
    if (q) {
      const hay = `${e.record_id} ${e.timestamp} ${e.event_id} ${e.target_user} ${e.source_ip} ${e.computer} ${e.logon_type} ${e.status} ${e.sub_status}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  const { key, dir } = state.sort;
  state.filtered.sort((a, b) => {
    const av = a[key], bv = b[key];
    if (av < bv) return -1 * dir;
    if (av > bv) return 1 * dir;
    return 0;
  });

  renderTable();
}

function renderTable() {
  const body = document.getElementById("events-body");
  body.innerHTML = "";
  for (const e of state.filtered) {
    const tr = document.createElement("tr");
    const isFail = e.event_id === 4625;
    tr.innerHTML = `
      <td class="mono">${e.record_id}</td>
      <td class="mono">${e.timestamp}</td>
      <td><span class="badge ${isFail ? "fail" : "ok"}">${e.event_id}</span></td>
      <td>${e.target_user}</td>
      <td class="mono">${e.source_ip}</td>
      <td class="mono">${e.logon_type}</td>
      <td class="mono">${e.status}</td>`;
    body.appendChild(tr);
  }
  document.getElementById("event-count").textContent =
    `${state.filtered.length} / ${state.events.length} events`;
}

function wireViewer() {
  document.getElementById("search").addEventListener("input", applyFilters);
  for (const id of ["filter-eventid", "filter-user", "filter-ip"]) {
    document.getElementById(id).addEventListener("change", applyFilters);
  }
  document.querySelectorAll("th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      state.sort.dir = state.sort.key === key ? -state.sort.dir : 1;
      state.sort.key = key;
      applyFilters();
    });
  });
}

/* ---------- Tasks ---------- */

function taskInputs(t) {
  if (t.input === "timestamp_window") {
    return `
      <input data-field="first" placeholder="First (2026-...Z)" />
      <input data-field="last" placeholder="Last (2026-...Z)" />`;
  }
  if (t.input === "choice_with_evidence") {
    const opts = t.choices.map((c) => `<option value="${c}">${c}</option>`).join("");
    return `
      <select data-field="choice">${opts}</select>
      <input data-field="evidence" placeholder="${t.evidence_hint || "evidence"}" />`;
  }
  if (t.input === "choice_with_priority") {
    const opts = t.choices.map((c) => `<option value="${c}">${c}</option>`).join("");
    const prio = t.priorities.map((p) => `<option value="${p}">${p}</option>`).join("");
    return `
      <select data-field="choice">${opts}</select>
      <select data-field="priority">${prio}</select>`;
  }
  return `<input data-field="value" placeholder="${t.answer_hint || "answer"}" />`;
}

function renderTasks() {
  const list = document.getElementById("task-list");
  list.innerHTML = "";
  for (const t of state.tasks) {
    const card = document.createElement("div");
    card.className = "task";
    card.id = `task-${t.id}`;
    card.innerHTML = `
      <div class="task-top">
        <h3>${t.id}. ${t.title}</h3>
        <span class="pts">${t.points} pts</span>
      </div>
      <p class="instr">${t.instructions}</p>
      <div class="inputs">
        ${taskInputs(t)}
        <button class="btn primary" data-submit="${t.id}">Submit</button>
      </div>
      <div class="feedback" id="fb-${t.id}"></div>`;
    list.appendChild(card);
  }
  list.querySelectorAll("button[data-submit]").forEach((btn) => {
    btn.addEventListener("click", () => submitTask(btn.dataset.submit));
  });
}

function buildAnswer(card, t) {
  const read = (f) => {
    const el = card.querySelector(`[data-field="${f}"]`);
    return el ? el.value.trim() : "";
  };
  if (t.input === "timestamp_window") return { first: read("first"), last: read("last") };
  if (t.input === "choice_with_evidence") return { choice: read("choice"), evidence: read("evidence") };
  if (t.input === "choice_with_priority") return { choice: read("choice"), priority: read("priority") };
  return read("value");
}

async function submitTask(taskId) {
  const t = state.tasks.find((x) => x.id === taskId);
  const card = document.getElementById(`task-${taskId}`);
  const fb = document.getElementById(`fb-${taskId}`);
  const answer = buildAnswer(card, t);

  const { ok, status, data } = await api(`/api/tasks/${taskId}/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answer }),
  });

  if (!ok) {
    fb.className = "feedback bad";
    fb.textContent = data.detail || `Error (${status}).`;
    return;
  }

  if (data.correct) {
    fb.className = "feedback ok";
    fb.textContent = `✔ ${data.message}`;
    card.classList.add("solved");
    card.querySelectorAll("input,select,button").forEach((el) => (el.disabled = true));
  } else {
    fb.className = "feedback bad";
    const rem = data.attempts_remaining;
    fb.textContent = `✗ ${data.message}` + (rem != null ? ` (${rem} attempts left)` : "");
  }
  updateScore(data);
}

/* ---------- Score / session ---------- */

function updateScore(s) {
  if (!s.progress) return;
  document.getElementById("progress").textContent = `${s.progress.completed}/${s.progress.total}`;
  document.getElementById("score").textContent = `${s.score}/${s.max_score}`;
}

async function refreshSession() {
  const { data } = await api("/api/session");
  updateScore(data);
  for (const [tid, ts] of Object.entries(data.tasks || {})) {
    if (ts.solved) {
      const card = document.getElementById(`task-${tid}`);
      if (card) {
        card.classList.add("solved");
        card.querySelectorAll("input,select,button").forEach((el) => (el.disabled = true));
        document.getElementById(`fb-${tid}`).textContent = "✔ Solved";
        document.getElementById(`fb-${tid}`).className = "feedback ok";
      }
    }
  }
}

function wireReset() {
  const btn = document.getElementById("reset-btn");
  if (!btn) return; // viewer-only mode has no reset button
  btn.addEventListener("click", async () => {
    if (!confirm("Reset all task progress for this session?")) return;
    await api("/api/session/reset", { method: "POST" });
    location.reload();
  });
}

/* ---------- Boot ---------- */

async function boot() {
  const [meta, events] = await Promise.all([api("/api/meta"), api("/api/events")]);
  state.tasks = meta.data.tasks || [];
  state.events = events.data.events || [];
  document.getElementById("dataset-notice").textContent =
    `${events.data.notice} (dataset ${events.data.dataset_version})`;
  populateFilters();
  wireViewer();
  applyFilters();

  // Viewer-only mode: render just the log dashboard, skip all task/scoring UI.
  if (meta.data.tasks_enabled === false) return;

  wireReset();
  renderTasks();
  await refreshSession();
}

boot();
