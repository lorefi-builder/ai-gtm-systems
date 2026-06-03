/* Project Assessment Agent — demo frontend logic.
 *
 * Single configurable API base URL (swap here to point at a deployed backend).
 * All state is kept in JS memory — no localStorage/sessionStorage. The three
 * channel tabs render the slack_message payloads the backend returns verbatim;
 * the dashboard reads GET /dashboard-data live. */

const API_BASE = "http://127.0.0.1:8000"; // <-- swap to retarget the backend
const DEMO_USER = "U_DEMO";

// ---------------------------------------------------------------- state (memory only)
const state = {
  tab: "spec",
  spec: [],     // spec-channel messages
  review: [],   // review-channel items
  deal: [],     // deal-tracking messages
  dashboard: null,
  charts: {},   // live Chart.js instances (destroyed on refresh)
  // Global dashboard filters (empty string = not applied; blank date_to -> backend "today").
  // date_from defaults to a fixed floor that spans the full seed history (earliest
  // specs ~Dec 2025) so the funnel opens on all 500 specs with no manual change.
  // Fixed date (not 6M-from-today) keeps it deterministic + clock-independent.
  // `preset` is UI-only (which date preset is highlighted; "" = custom/none) and
  // is NOT sent to the backend by buildDashQuery. use_case/segment/region are
  // multi-select arrays ([] = no filter on that dimension = all).
  filters: { date_from: "2025-12-01", date_to: "", cadence: "monthly", use_case: [], segment: [], region: [], preset: "" },
  openMs: null,   // key of the currently-open multi-select panel (UI-only)
};
let _id = 0;
const nextId = () => `m${++_id}`;

// ---------------------------------------------------------------- tiny helpers
const $ = (sel) => document.querySelector(sel);
const el = (id) => document.getElementById(id);

function escapeHtml(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Escape for use inside a double-quoted HTML attribute. The backend's button
// `value` is JSON like {"spec_id":"..."} — its double quotes MUST be escaped or
// the attribute terminates early and the payload (incl. spec_id) is lost.
function escapeAttr(s) {
  return escapeHtml(s).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

const EMOJI = {
  ":warning:": "⚠️", ":white_check_mark:": "✅", ":x:": "❌",
  ":link:": "🔗", ":raised_hand:": "✋",
};

// Convert Slack mrkdwn (already produced by the backend) into safe HTML.
function mrkdwn(text) {
  let t = escapeHtml(text);
  t = t.replace(/`([^`]+)`/g, "<code>$1</code>");
  t = t.replace(/\*([^*\n]+)\*/g, "<strong>$1</strong>");
  // conservative italics: _word_ bounded by space/start/punctuation
  t = t.replace(/(^|[\s(])_([^_\n]+)_(?=$|[\s).,;:])/g, "$1<em>$2</em>");
  for (const [k, v] of Object.entries(EMOJI)) t = t.split(k).join(v);
  t = t.replace(/\n/g, "<br/>");
  return t;
}

function nowTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function fmtMoney(n) {
  n = Number(n) || 0;
  if (n >= 1e6) return "$" + (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return "$" + (n / 1e3).toFixed(0) + "k";
  return "$" + n.toFixed(0);
}

// ---------------------------------------------------------------- API layer
async function api(path, body) {
  // STATIC REPLAY: when static-data.js is present (deployed, no backend), return
  // baked payloads instead of hitting the network. When the flag is falsy (local
  // dev), this is a no-op and the live path below runs exactly as before.
  if (window.STATIC_REPLAY) return staticApi(path, body);
  const opts = body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : { method: "GET" };
  let res;
  try {
    res = await fetch(API_BASE + path, opts);
  } catch (e) {
    // Network/CORS failure -> friendly banner, never a blank screen.
    showError(
      `Can't reach the API at ${API_BASE}. Is the backend running ` +
      `(uvicorn app:app) and is CORS enabled? See frontend/README.md.`
    );
    throw e;
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    // The backend returns clean {error, type} bodies for 4xx/5xx.
    throw new Error(data.error || `Request failed (${res.status})`);
  }
  return data;
}

// Static-replay backend: resolve the baked payload for `path`, mirroring api()'s
// resolved value (the parsed JSON body). Matches /spec, /review, /approve exactly
// and /dashboard-data by base path (query string stripped). Unbaked paths reject
// loudly so a missing capture fails visibly rather than silently.
function staticApi(path, body) {
  const responses = window.STATIC_RESPONSES || {};
  const base = String(path).split("?")[0];   // strips ?date_from=...&cadence=... from /dashboard-data
  const payload = responses[base];
  if (payload === undefined) {
    return Promise.reject(new Error(
      `Static replay: no baked response for "${path}". This demo only replays the ` +
      `captured happy path (/spec, /review, /approve) + /dashboard-data.`
    ));
  }
  // POST /spec gets the full pre-roll delay so the loading animation reads; the
  // rest resolve near-immediately for snappy buttons.
  const delay = base === "/spec" ? (Number(window.STATIC_DELAY_MS) || 1400) : 200;
  return new Promise((resolve) => setTimeout(() => resolve(payload), delay));
}

function showError(msg) {
  el("err-text").textContent = msg;
  el("err-banner").classList.add("show");
}

// Wrap any server-calling action so a click visibly registers and a second click
// can't fire a duplicate request. The re-entrancy guard runs SYNCHRONOUSLY — in
// the same tick as the click, before any await — which is the actual double-fire
// fix; the spinner is only the visual. Restores in `finally`, guarding against
// the button having been re-rendered/removed by the action.
async function runBusy(buttonEl, asyncFn, busyLabel = "Running…") {
  // 1) Re-entrancy guard FIRST, synchronously, before any await.
  if (!buttonEl || buttonEl.disabled || buttonEl.dataset.busy === "1") return;
  buttonEl.dataset.busy = "1";
  buttonEl.disabled = true;
  const originalHtml = buttonEl.innerHTML;
  buttonEl.classList.add("is-busy");
  buttonEl.innerHTML = `<span class="spinner" aria-hidden="true"></span>${escapeHtml(busyLabel)}`;
  try {
    await asyncFn();
  } catch (e) {
    // Surface minimally, don't swallow (covers a 529 too — retry isn't in yet).
    showError(e && e.message ? e.message : String(e));
  } finally {
    // Only restore if the button is still in the DOM — many of these actions
    // re-render or remove their bubble, in which case there's nothing to restore.
    if (buttonEl.isConnected) {
      buttonEl.disabled = false;
      buttonEl.dataset.busy = "0";
      buttonEl.classList.remove("is-busy");
      buttonEl.innerHTML = originalHtml;
    }
  }
}

// ---------------------------------------------------------------- Slack bubble renderer
// Renders one slack_message payload (channel header omitted — the pane is the
// channel). opts: { badge, below, footer, hideButtons, disableButtons }.
function bubble(payload, opts = {}) {
  const sections = (payload.blocks || [])
    .filter((b) => b.type === "section" && b.text)
    .map((b) => `<div class="msg-section">${mrkdwn(b.text.text)}</div>`)
    .join("");

  const text = sections || mrkdwn(payload.text || "");
  const buttons = opts.hideButtons ? "" : buttonsHtml(payload, opts.disableButtons);

  return `
    <div class="msg">
      <div class="msg-avatar">PA</div>
      <div class="msg-body">
        <div class="msg-head">
          <span class="msg-author">Project Assessment Agent</span>
          <span class="app-tag">APP</span>
          <span class="msg-time">${nowTime()}</span>
        </div>
        <div class="msg-text">${text}</div>
        ${opts.badge || ""}
        ${opts.below || ""}
        ${buttons ? `<div class="msg-actions">${buttons}</div>` : ""}
        ${opts.footer || ""}
      </div>
    </div>`;
}

function buttonsHtml(payload, disabled) {
  const actions = (payload.blocks || []).filter((b) => b.type === "actions");
  // Static replay only baked the happy path (no /reject, /regenerate), so hide
  // those buttons — a viewer can't trigger an unbaked call. Live mode: the flag
  // is falsy → suppress stays null → nothing is skipped (rendering unchanged).
  const suppress = window.STATIC_REPLAY
    ? new Set(["reject_spec", "regenerate_open", "regenerate_submit"])
    : null;
  const out = [];
  for (const a of actions) {
    for (const btn of a.elements || []) {
      if (suppress && suppress.has(btn.action_id)) continue;
      const cls = btn.style === "primary" ? "sl-btn sl-btn-primary"
                : btn.style === "danger" ? "sl-btn sl-btn-danger"
                : "sl-btn";
      out.push(
        `<button class="${cls}" ${disabled ? "disabled" : ""} ` +
        `data-action="${escapeAttr(btn.action_id)}" ` +
        `data-value="${escapeAttr(btn.value || "{}")}">${escapeHtml(btn.text.text)}</button>`
      );
    }
  }
  return out.join("");
}

// ---------------------------------------------------------------- tab switching
function setTab(tab) {
  state.tab = tab;
  document.querySelectorAll(".chan-item").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === tab));
  document.querySelectorAll(".pane").forEach((p) => p.classList.remove("active"));
  el("pane-" + tab).classList.add("active");

  const meta = {
    spec: ["#", "spec-channel", "Run <code>/spec</code> on a discovery transcript"],
    review: ["#", "spec-review", "Approvers review drafted specs"],
    deal: ["#", "deal-tracking", "Approved specs post their new opportunities here"],
    dashboard: ["📊", "Dashboard", ""],
    di: ["🛰", "Demand Intelligence", ""],
  }[tab];
  el("bar-hash").textContent = meta[0];
  el("bar-title").textContent = meta[1];
  el("bar-desc").innerHTML = meta[2];
  // Hide the subtitle slot entirely when empty so its left border/padding doesn't linger.
  el("bar-desc").style.display = meta[2] ? "" : "none";

  if (tab === "dashboard" && !state.dashboard) loadDashboard();
  // DI reuses the cached /dashboard-data response (no second endpoint). If it
  // isn't loaded yet, loadDashboard() renders the DI pane on completion (it
  // checks state.tab); otherwise render straight from the cache.
  if (tab === "di") {
    if (!state.dashboard) loadDashboard();
    else renderDI();
  }
}

function bumpBadge(which) {
  const map = { review: "badge-review", deal: "badge-deal" };
  const count = state[which].length;
  const b = el(map[which]);
  if (count > 0) { b.style.display = ""; b.textContent = count; }
}

// ---------------------------------------------------------------- TAB 1: spec channel
function renderSpec() {
  const list = el("spec-list");
  if (!state.spec.length) {
    list.innerHTML = `<div class="empty-state">No messages yet — pick a transcript below and run <b>/spec</b> to begin.</div>`;
    return;
  }
  list.innerHTML = state.spec.map((m) => {
    if (m.kind === "loading") {
      return `<div class="msg"><div class="msg-avatar">PA</div><div class="msg-body">
        <div class="msg-head"><span class="msg-author">Project Assessment Agent</span><span class="app-tag">APP</span></div>
        <div class="loading-text"><span id="${m.id}-txt">${m.text}</span><span class="dots"></span></div></div></div>`;
    }
    if (m.kind === "error") {
      return `<div class="msg"><div class="msg-avatar" style="background:var(--red)">!</div><div class="msg-body">
        <div class="msg-head"><span class="msg-author">Project Assessment Agent</span></div>
        <div class="msg-text" style="color:var(--red)">${escapeHtml(m.text)}</div></div></div>`;
    }
    // kind === "slack"
    if (m.deleted) {
      return `<div class="msg deleted-msg"><div class="msg-avatar">PA</div><div class="msg-body">
        <div class="msg-head"><span class="msg-author">Project Assessment Agent</span><span class="app-tag">APP</span></div>
        <div class="msg-text"><span class="deleted-tag">deleted</span>This spec was soft-deleted — the row + audit trail are retained in the warehouse.</div></div></div>`;
    }
    const lineage = m.lineageFrom
      ? `<div class="lineage-tag">↻ regenerated from <code>${escapeHtml(short(m.lineageFrom))}</code></div>`
      : "";
    const badge = m.reviewReason
      ? `<div class="review-badge">⚠️ Needs human review <span class="rb-reason">— ${escapeHtml(m.reviewReason)}</span></div>`
      : "";
    const below = m.draftSpec
      ? `<details class="draft"><summary>View draft spec ▼</summary><div class="md">${marked.parse(m.draftSpec)}</div></details>`
      : "";
    let footer = m.sentToReview
      ? `<div class="status-footer ok">✅ Sent to #spec-review</div>` : "";
    // Delete is a secondary housekeeping action; only on a draft not yet sent to
    // review (mirrors the backend guard: deletable from draft|rejected only).
    if (m.specId && !m.sentToReview) footer += deleteControl(m);
    return bubble(m.payload, { badge: lineage + badge, below, footer, disableButtons: m.sentToReview });
  }).join("");
  list.scrollTop = list.scrollHeight;
}

// Short id for lineage/labels.
function short(id) { return String(id || "").slice(0, 8); }

// Subtle delete affordance + inline confirm for a draft spec bubble.
function deleteControl(m) {
  if (m.deleting) {
    return `<div class="confirm-box">Delete this spec? This can't be undone from here.
      <div class="rb-actions">
        <button class="sl-btn sl-btn-danger" data-action="confirm_delete" data-value='{"spec_id":"${m.specId}","mid":"${m.id}"}'>Delete</button>
        <button class="sl-btn" data-action="cancel_delete" data-value='{"mid":"${m.id}"}'>Cancel</button>
      </div></div>`;
  }
  const err = m.deleteError ? `<span class="tool-err">${escapeHtml(m.deleteError)}</span>` : "";
  return `<div class="tools"><button class="link-btn" data-action="delete_spec" data-value='{"mid":"${m.id}"}'>🗑 Delete</button>${err}</div>`;
}

async function runSpec() {
  const sel = el("transcript-select");
  const t = window.TRANSCRIPTS[sel.value];
  if (!t) return;

  // The #run-spec button's busy/disabled state is owned by runBusy (see init).
  const loader = { id: nextId(), kind: "loading", text: "Agent 1 extracting signals" };
  state.spec.push(loader);
  renderSpec();

  // Staged progress text so the multi-second wait feels intentional.
  const stages = [
    "Agent 1 extracting signals",
    "Checking the warehouse for duplicate specs",
    "Classifying (capability matrix + escalation detectors)",
    "Estimating resources from historical analogs",
    "Drafting the spec (RAG-grounded)",
  ];
  let si = 0;
  const timer = setInterval(() => {
    si = Math.min(si + 1, stages.length - 1);
    const node = el(`${loader.id}-txt`);
    if (node) node.textContent = stages[si];
  }, 2200);

  try {
    const resp = await api("/spec", { transcript_text: t.text, requested_by: DEMO_USER });
    clearInterval(timer);
    state.spec = state.spec.filter((m) => m.id !== loader.id);
    handleSpecResponse(resp);
  } catch (e) {
    clearInterval(timer);
    state.spec = state.spec.filter((m) => m.id !== loader.id);
    state.spec.push({ id: nextId(), kind: "error", text: e.message });
    renderSpec();
  }
}

// Handles both /spec and /spec/resume responses (they share result shapes).
function handleSpecResponse(resp) {
  if (resp.status === "draft_created") {
    state.spec.push({
      id: nextId(), kind: "slack", payload: resp.slack_message,
      draftSpec: resp.draft_spec || "",
      reviewReason: resp.needs_human_review ? resp.review_reason : null,
      specId: resp.spec_id, sentToReview: false,
      lineageFrom: resp.regenerated_from || null,  // set on /regenerate results
    });
  } else if (resp.status === "paused_duplicate") {
    state.spec.push({ id: nextId(), kind: "slack", payload: resp.slack_message });
  } else if (resp.status === "linked_duplicate" || resp.status === "escalated") {
    state.spec.push({ id: nextId(), kind: "slack", payload: resp.slack_message });
  } else {
    state.spec.push({ id: nextId(), kind: "slack", payload: resp.slack_message || { text: JSON.stringify(resp) } });
  }
  renderSpec();
}

// ---------------------------------------------------------------- TAB 2: review channel
function renderReview() {
  const list = el("review-list");
  if (!state.review.length) {
    list.innerHTML = `<div class="empty-state">No specs in review yet — approve one from the spec channel by clicking <b>Send to review</b>.</div>`;
    return;
  }
  list.innerHTML = state.review.map((item) => {
    if (item.status === "approved") {
      const footer = `<div class="status-footer ok">✅ Approved — opportunity <code>${escapeHtml(item.opportunityId || "")}</code> created · posted to #deal-tracking</div>`;
      return bubble(item.payload, { hideButtons: true, footer });
    }
    if (item.status === "rejected") {
      // Close the loop: rejection reason + the Regenerate path right here.
      const regen = item.regenerating ? regenComposer(item) : regenButton(item);
      const note = item.regeneratedTo
        ? `<div class="status-footer ok">↻ Regenerated → new draft <code>${escapeHtml(short(item.regeneratedTo))}</code> in #spec-channel</div>`
        : "";
      return bubble(item.rejectPayload, { hideButtons: true, footer: regen + note });
    }
    // pending
    const rejectBox = item.rejecting ? `
      <div class="reject-box">
        <textarea id="${item.id}-reason" placeholder="Why is this spec being rejected? (required)"></textarea>
        <div class="rb-err" id="${item.id}-err"></div>
        <div class="rb-actions">
          <button class="sl-btn sl-btn-danger" data-action="submit_reject" data-value='{"spec_id":"${item.specId}","item":"${item.id}"}'>Confirm reject</button>
          <button class="sl-btn" data-action="cancel_reject" data-value='{"item":"${item.id}"}'>Cancel</button>
        </div>
      </div>` : "";
    return bubble(item.payload, { below: rejectBox });
  }).join("");
  list.scrollTop = list.scrollHeight;
}

async function sendToReview(specId, specMsgId) {
  try {
    const resp = await api("/review", { spec_id: specId, requested_by: DEMO_USER });
    // Mark the originating spec bubble as sent.
    const sm = state.spec.find((m) => m.specId === specId);
    if (sm) sm.sentToReview = true;
    renderSpec();
    // Add to review channel.
    state.review.push({
      id: nextId(), kind: "review", payload: resp.slack_message,
      specId, status: "pending", rejecting: false,
    });
    bumpBadge("review");
    renderReview();
    setTab("review");
  } catch (e) { showError(e.message); }
}

async function approveSpec(specId) {
  try {
    const resp = await api("/approve", { spec_id: specId, actor: DEMO_USER });
    const item = state.review.find((r) => r.specId === specId && r.status === "pending");
    if (item) { item.status = "approved"; item.opportunityId = resp.opportunity_id; }
    renderReview();
    // The approve response's slack_message IS the deal-tracking post.
    state.deal.push({ id: nextId(), kind: "slack", payload: resp.slack_message });
    bumpBadge("deal");
    renderDeal();
    setTab("deal");
  } catch (e) { showError(e.message); }
}

async function submitReject(specId, itemId) {
  const ta = el(`${itemId}-reason`);
  const reason = (ta && ta.value || "").trim();
  if (!reason) { // client-side guard (backend also enforces non-empty)
    el(`${itemId}-err`).textContent = "A reason is required to reject.";
    return;
  }
  try {
    const resp = await api("/reject", { spec_id: specId, actor: DEMO_USER, reason });
    const item = state.review.find((r) => r.id === itemId);
    if (item) { item.status = "rejected"; item.rejectPayload = resp.slack_message; }
    renderReview();
  } catch (e) { showError(e.message); }
}

// --- regenerate (from a rejected review item) -------------------------------
function regenButton(item) {
  return `<div class="msg-actions">
    <button class="sl-btn sl-btn-primary" data-action="regenerate_open" data-value='{"item":"${item.id}"}'>↻ Regenerate spec</button>
  </div>`;
}

function regenComposer(item) {
  return `<div class="regen-box">
    <label class="regen-label">Add correction context <span class="muted">(optional, max 500 chars)</span></label>
    <textarea id="${item.id}-ctx" data-counter="${item.id}-count"
      placeholder="e.g. Narrow scope to the first batch only; defer the weekly cadence; set a concrete acceptance threshold."></textarea>
    <div class="regen-foot"><span class="counter" id="${item.id}-count">0/500</span></div>
    <div class="rb-actions">
      <button class="sl-btn sl-btn-primary" id="${item.id}-submit" data-action="regenerate_submit" data-value='{"spec_id":"${item.specId}","item":"${item.id}"}'>Regenerate</button>
      <button class="sl-btn" data-action="regenerate_cancel" data-value='{"item":"${item.id}"}'>Cancel</button>
    </div>
  </div>`;
}

function openRegen(itemId) {
  const item = state.review.find((r) => r.id === itemId);
  if (item) { item.regenerating = true; renderReview(); }
}
function cancelRegen(itemId) {
  const item = state.review.find((r) => r.id === itemId);
  if (item) { item.regenerating = false; renderReview(); }
}

async function submitRegen(specId, itemId) {
  const ta = el(`${itemId}-ctx`);
  const ctx = (ta && ta.value || "").trim();
  if (ctx.length > 500) return;  // counter already disables submit; backend also enforces
  const body = { spec_id: specId, requested_by: DEMO_USER };
  if (ctx) body.correction_context = ctx;  // omit when blank (it's optional)
  try {
    const resp = await api("/regenerate", body);
    const item = state.review.find((r) => r.id === itemId);
    if (item) { item.regenerating = false; item.regeneratedTo = resp.spec_id; }
    renderReview();
    handleSpecResponse(resp);  // new draft renders in #spec-channel (with lineage tag)
    setTab("spec");
  } catch (e) { showError(e.message); }
}

// Live char counter for the regenerate composer (delegated input handler).
function onReviewInput(e) {
  const ta = e.target;
  if (!ta.matches || !ta.matches("textarea[data-counter]")) return;
  const counter = el(ta.dataset.counter);
  if (!counter) return;
  const n = ta.value.length;
  counter.textContent = `${n}/500`;
  const over = n > 500;
  counter.classList.toggle("over", over);            // turns red past 500
  const submitBtn = el(ta.id.replace("-ctx", "-submit"));
  if (submitBtn) submitBtn.disabled = over;          // disable submit past 500
}

// --- soft delete (from a draft spec bubble) ---------------------------------
function openDelete(mid) {
  const m = state.spec.find((x) => x.id === mid);
  if (m) { m.deleting = true; m.deleteError = null; renderSpec(); }
}
function cancelDelete(mid) {
  const m = state.spec.find((x) => x.id === mid);
  if (m) { m.deleting = false; renderSpec(); }
}
async function confirmDelete(specId, mid) {
  try {
    await api("/spec/delete", { spec_id: specId, actor: DEMO_USER });
    const m = state.spec.find((x) => x.id === mid);
    if (m) { m.deleted = true; m.deleting = false; }
    renderSpec();
  } catch (e) {
    // Mirror the backend guard gracefully (e.g. 409 if it's not deletable).
    const m = state.spec.find((x) => x.id === mid);
    if (m) { m.deleting = false; m.deleteError = e.message; }
    renderSpec();
  }
}

// ---------------------------------------------------------------- TAB 3: deal channel
function renderDeal() {
  const list = el("deal-list");
  if (!state.deal.length) {
    list.innerHTML = `<div class="empty-state">No opportunities yet — approve a spec in <b>#spec-review</b> and it posts here.</div>`;
    return;
  }
  list.innerHTML = state.deal.map((m) => bubble(m.payload, { hideButtons: true })).join("");
  list.scrollTop = list.scrollHeight;
}

// ---------------------------------------------------------------- delegated button clicks
function onChannelClick(e) {
  const btn = e.target.closest("button[data-action]");
  if (!btn) return;
  const action = btn.dataset.action;
  let val = {};
  try { val = JSON.parse(btn.dataset.value || "{}"); } catch (_) {}

  // Server-calling actions route through runBusy (synchronous re-entrancy guard
  // + disable + spinner + restore). Local-only toggles call their handler direct.
  switch (action) {
    // --- server calls (busy-wrapped; `btn` is the clicked element) ---
    case "send_to_review":    return runBusy(btn, () => sendToReview(val.spec_id), "Sending…");
    case "approve_spec":      return runBusy(btn, () => approveSpec(val.spec_id), "Approving…");
    case "submit_reject":     return runBusy(btn, () => submitReject(val.spec_id, val.item), "Rejecting…");
    case "dedup_proceed":     return runBusy(btn, () => resumeSpec(val.ref, "proceed"), "Working…");
    case "dedup_link":        return runBusy(btn, () => resumeSpec(val.ref, "link"), "Working…");
    case "dedup_escalate":    return runBusy(btn, () => resumeSpec(val.ref, "escalate"), "Working…");
    case "regenerate_submit": return runBusy(btn, () => submitRegen(val.spec_id, val.item), "Regenerating…");
    case "confirm_delete":    return runBusy(btn, () => confirmDelete(val.spec_id, val.mid), "Deleting…");
    // --- local-only toggles (no server call; must NOT be busy-wrapped) ---
    case "reject_spec":       return openReject(val.spec_id);
    case "cancel_reject":     return cancelReject(val.item);
    case "delete_spec":       return openDelete(val.mid);
    case "cancel_delete":     return cancelDelete(val.mid);
    case "regenerate_open":   return openRegen(val.item);
    case "regenerate_cancel": return cancelRegen(val.item);
  }
}

function openReject(specId) {
  const item = state.review.find((r) => r.specId === specId && r.status === "pending");
  if (item) { item.rejecting = true; renderReview(); }
}
function cancelReject(itemId) {
  const item = state.review.find((r) => r.id === itemId);
  if (item) { item.rejecting = false; renderReview(); }
}

async function resumeSpec(ref, choice) {
  try {
    const resp = await api("/spec/resume", { ref, choice });
    handleSpecResponse(resp);
  } catch (e) { showError(e.message); }
}

// ---------------------------------------------------------------- TAB 4: dashboard
function buildDashQuery() {
  const f = state.filters;
  const p = new URLSearchParams();
  if (f.date_from) p.set("date_from", f.date_from);
  if (f.date_to) p.set("date_to", f.date_to);
  if (f.cadence) p.set("cadence", f.cadence);
  // multi-select: comma-joined; empty array -> param omitted (no filter = all)
  if (f.use_case.length) p.set("use_case", f.use_case.join(","));
  if (f.segment.length) p.set("segment", f.segment.join(","));
  if (f.region.length) p.set("region", f.region.join(","));
  const s = p.toString();
  return s ? "?" + s : "";
}

async function loadDashboard() {
  el("dash-root").innerHTML = `<div class="dash-loading">Loading dashboard from the warehouse…</div>`;
  if (state.tab === "di") el("di-root").innerHTML = `<div class="dash-loading">Loading demand intelligence…</div>`;
  try {
    state.dashboard = await api("/dashboard-data" + buildDashQuery());
    renderDashboard();
    if (state.tab === "di") renderDI();   // DI reflects the same (re)loaded data
  } catch (e) {
    const msg = `<div class="dash-error">Couldn't load /dashboard-data — ${escapeHtml(e.message)}</div>`;
    el("dash-root").innerHTML = msg;
    if (state.tab === "di") el("di-root").innerHTML = msg;
  }
}

// ---------------------------------------------------------------- TAB 5: Demand Intelligence
// Renders from the cached state.dashboard.demand_intelligence — no second fetch.
function renderDI() {
  const root = el("di-root");
  if (!root) return;
  const d = state.dashboard;
  const di = d && d.demand_intelligence;
  if (!di) {
    root.innerHTML = `<div class="dash-error">No demand-intelligence data — open the Dashboard tab first to load it.</div>`;
    return;
  }
  const h = di.headline || {};
  root.innerHTML = `
    <div class="dash-head"><h1>Demand Intelligence</h1>
      <div class="freshness">🛈 Capability-gap = RED capability × escalation flag. Declined = rejected. Dollars are estimated value at discovery.</div>
    </div>
    ${diHeadlineHtml(h)}
    <div class="pillar">
      <div class="pillar-title"><h2>Capability-gap demand — domain × segment</h2>
        <span class="sub">estimated value · RED + escalated</span></div>
      ${diHeatmapHtml(di.heatmap || [])}
    </div>
    <div class="pillar">
      <div class="cards c2">
        <div class="card"><h3>Gap demand by escalation reason</h3>${diReasonBarsHtml(di.by_reason || [])}</div>
        <div class="card"><h3>Gap vs. declined by domain</h3>${diDomainHtml(di.by_domain || [])}</div>
      </div>
    </div>`;
}

// Hero row — 3 prominent stat tiles (distinct from the dashboard scorecards).
function diHeadlineHtml(h) {
  const tiles = [
    { v: fmtMoney(h.gap_value || 0), l: "Capability-Gap Demand",
      sub: `${(Number(h.gap_specs) || 0).toLocaleString()} specs · RED + escalated`, cls: "di-gap" },
    { v: fmtMoney(h.declined_value || 0), l: "Declined Demand",
      sub: `${(Number(h.declined_specs) || 0).toLocaleString()} specs turned away`, cls: "di-dec" },
    { v: h.top_domain || "—", l: "Top Gap Domain", sub: "highest gap $", cls: "di-top" },
  ];
  return `<div class="di-hero">${tiles.map((t) =>
    `<div class="di-hero-tile ${t.cls}">
       <div class="dh-v">${escapeHtml(t.v)}</div>
       <div class="dh-l">${escapeHtml(t.l)}</div>
       <div class="dh-sub">${escapeHtml(t.sub)}</div>
     </div>`).join("")}</div>`;
}

// Gap heatmap — hand-rolled CSS grid. Rows = domains (by row-total desc),
// columns = segments (canonical order, derived from data). Cell background
// intensity ∝ gap $ via heatColor() (sqrt scale lifts mid cells); empty cells muted.
function diHeatmapHtml(cells) {
  if (!cells.length) return `<div class="note">No capability-gap demand in the current range.</div>`;
  const SEG_ORDER = ["Enterprise", "Mid-Market", "SMB"];
  const present = [...new Set(cells.map((c) => c.segment))];
  const segs = SEG_ORDER.filter((s) => present.includes(s))
    .concat(present.filter((s) => !SEG_ORDER.includes(s)));   // any unexpected segments last
  const cellMap = {}, rowTotal = {};
  cells.forEach((c) => {
    (cellMap[c.domain] = cellMap[c.domain] || {})[c.segment] = c;
    rowTotal[c.domain] = (rowTotal[c.domain] || 0) + (c.value || 0);
  });
  const domains = Object.keys(rowTotal).sort((a, b) => rowTotal[b] - rowTotal[a]);
  const maxVal = Math.max(...cells.map((c) => c.value || 0), 1);

  const cols = `minmax(130px, 1.3fr) repeat(${segs.length}, 1fr)`;
  let grid = `<div class="heatmap" style="grid-template-columns:${cols}">`;
  grid += `<div class="hm-corner">domain ＼ segment</div>`;
  segs.forEach((s) => { grid += `<div class="hm-colhead">${escapeHtml(s)}</div>`; });
  domains.forEach((dom) => {
    grid += `<div class="hm-rowhead">${escapeHtml(dom)}</div>`;
    segs.forEach((s) => {
      const c = cellMap[dom] && cellMap[dom][s];
      if (!c || !(c.value > 0)) { grid += `<div class="hm-cell hm-empty">—</div>`; return; }
      const t = Math.sqrt((c.value || 0) / maxVal);
      const dark = t > 0.45;
      grid += `<div class="hm-cell" style="background:${heatColor(t)};color:${dark ? "#fff" : "var(--ink)"}">
        <div class="hm-val">${fmtMoney(c.value)}</div>
        <div class="hm-det">${Number(c.specs) || 0} specs · ${Number(c.declined_specs) || 0} declined</div>
      </div>`;
    });
  });
  grid += `</div>`;
  const legend = `<div class="hm-legend">
    <span class="hm-legend-lbl">$0</span>
    <span class="hm-legend-bar"></span>
    <span class="hm-legend-lbl">${fmtMoney(maxVal)}</span>
    <span class="hm-legend-note">deeper red = higher capability-gap $</span>
  </div>`;
  return grid + legend;
}

// pale-warm → brand-red ramp for the gap heatmap (warm/red reads as "gap").
// Deep endpoint is the app's brand red #c2194e (= var(--slack-red-d) = --di-deep);
// the legend gradient bar terminates at the same rgb. Pale endpoint + sqrt scale
// are unchanged.
function heatColor(t) {
  t = Math.max(0, Math.min(1, t));
  const a = [251, 233, 226], b = [194, 25, 78];   // #FBE9E2 -> #c2194e (brand red)
  const c = a.map((av, i) => Math.round(av + (b[i] - av) * t));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
}

// Horizontal bars from by_reason ($ value, sorted desc). Tolerant of any buckets.
function diReasonBarsHtml(rows) {
  if (!rows.length) return `<div class="note">No escalation-flagged gap demand in range.</div>`;
  const max = Math.max(...rows.map((r) => r.value || 0), 1);
  return `<div class="di-bars">${rows.map((r) => {
    const w = Math.round((r.value || 0) / max * 100);
    return `<div class="di-bar-row">
      <div class="di-bar-lbl">${escapeHtml(prettyKey(r.reason))}</div>
      <div class="di-bar-track"><div class="di-bar-fill" style="width:${w}%"></div></div>
      <div class="di-bar-val">${fmtMoney(r.value)} · ${Number(r.specs) || 0}</div>
    </div>`;
  }).join("")}</div>`;
}

// Gap vs. declined by domain — grouped bars (gap = burgundy, declined = red).
function diDomainHtml(rows) {
  if (!rows.length) return `<div class="note">No gap demand by domain in range.</div>`;
  const max = Math.max(...rows.map((r) => Math.max(r.gap_value || 0, r.declined_value || 0)), 1);
  const pct = (v) => Math.round((v || 0) / max * 100);
  return `<div class="di-dom">
    <div class="di-dom-legend"><span class="dot dot-gap"></span>Gap&nbsp;&nbsp;<span class="dot dot-dec"></span>Declined</div>
    ${rows.map((r) => `
      <div class="di-dom-row">
        <div class="di-dom-lbl">${escapeHtml(r.domain)}</div>
        <div class="di-dom-bars">
          <div class="di-dom-bar di-dom-gap" style="width:${pct(r.gap_value)}%" title="Gap ${fmtMoney(r.gap_value)} · ${Number(r.gap_specs) || 0} specs"></div>
          <div class="di-dom-bar di-dom-dec" style="width:${pct(r.declined_value)}%" title="Declined ${fmtMoney(r.declined_value)} · ${Number(r.declined_specs) || 0} specs"></div>
        </div>
        <div class="di-dom-val">${fmtMoney(r.gap_value)} / ${fmtMoney(r.declined_value)}</div>
      </div>`).join("")}
  </div>`;
}

function renderDashboard() {
  const d = state.dashboard;
  const f = state.filters;
  const fil = d.filters || { available_use_cases: [], available_segments: [], available_regions: [] };
  const s2 = d.spec_to_opportunity;
  const revNote = (d.opportunity_to_won.revenue_per_win_type || {}).note || "";
  // STATIC REPLAY: the filter bar is a fixed snapshot (every selection returns
  // the same baked payload), so show it visibly disabled with an explainer note
  // instead of letting a viewer trigger a no-op. Live mode: both are empty/absent.
  const fbClass = window.STATIC_REPLAY ? "filter-bar static-locked" : "filter-bar";
  const fbNote = window.STATIC_REPLAY
    ? `<div class="fb-static-note">🔒 Filters are interactive in the live demo — this shared view is a fixed snapshot.</div>`
    : "";
  // Refresh also refetches, so disable it in static mode (it's already inert —
  // attachDashFilters wires nothing — this just stops it from looking clickable).
  const refreshAttr = window.STATIC_REPLAY ? ' disabled title="Fixed snapshot — refresh disabled"' : "";

  el("dash-root").innerHTML = `
    <div class="dash-head">
      <h1>SpecOps — Pipeline Analytics</h1>
      <button class="refresh-btn" id="dash-refresh"${refreshAttr}>↻ Refresh</button>
      <div class="freshness">🛈 ${escapeHtml(d.data_freshness || "")}</div>
    </div>

    <!-- GLOBAL FILTER BAR -->
    <div class="${fbClass}">
      <div class="fb-group">
        <span class="fb-label">Range</span>
        <input type="date" id="f-from" value="${f.date_from}" />
        <span class="fb-dash">→</span>
        <input type="date" id="f-to" value="${f.date_to}" />
        <div class="presets" id="f-presets">
          <button data-preset="ytd" class="${f.preset === "ytd" ? "on" : ""}">YTD</button>
          <button data-preset="6m" class="${f.preset === "6m" ? "on" : ""}">6M</button>
          <button data-preset="30d" class="${f.preset === "30d" ? "on" : ""}">30D</button>
          <button data-preset="7d" class="${f.preset === "7d" ? "on" : ""}">7D</button>
        </div>
      </div>
      <div class="fb-group">
        <span class="fb-label">Cadence</span>
        <div class="seg-toggle" id="f-cadence">
          <button data-cad="daily" class="${f.cadence === "daily" ? "on" : ""}">Daily</button>
          <button data-cad="weekly" class="${f.cadence === "weekly" ? "on" : ""}">Weekly</button>
          <button data-cad="monthly" class="${f.cadence === "monthly" ? "on" : ""}">Monthly</button>
        </div>
      </div>
      <div class="fb-group">
        <span class="fb-label">Use case</span>
        ${multiSelectHtml("use_case", fil.available_use_cases, f.use_case, "All use cases")}
      </div>
      <div class="fb-group">
        <span class="fb-label">Segment × Region</span>
        ${multiSelectHtml("segment", fil.available_segments, f.segment, "All segments")}
        ${multiSelectHtml("region", fil.available_regions, f.region, "All regions")}
      </div>
      ${fbNote}
    </div>

    <!-- SCORECARD ROW (from business_funnel) -->
    ${scorecardsHtml(d.business_funnel)}

    <!-- SECTION 1 -->
    <div class="pillar">
      <div class="pillar-title"><h2>Spec Generation</h2>
        <span class="sub">time series · ${escapeHtml(f.cadence)} buckets</span></div>
      <div class="cards c3">
        <div class="card"><h3>Spec volume by status</h3><div class="chart-wrap"><canvas id="c-spec-status"></canvas></div></div>
        <div class="card"><h3>Rejection volume by reason</h3><div class="chart-wrap"><canvas id="c-rej-reason"></canvas></div></div>
        <div class="card"><h3>Approval volume by use case</h3><div class="chart-wrap"><canvas id="c-appr-uc"></canvas></div></div>
      </div>
    </div>

    <!-- SECTION 2: pipeline flow + stage velocity (SVG, no Chart.js) -->
    <div class="pillar">
      <div class="pillar-title"><h2>Spec → Opportunity</h2>
        <span class="sub">pipeline flow + stage velocity</span></div>
      <div class="card">
        <h3>Pipeline flow — deal journeys <span style="color:var(--ink-mute);font-weight:400">(dollar-weighted)</span></h3>
        <div class="viz-wrap viz-sankey">${pipelineFlowSvg(d.pipeline_flow)}</div>
      </div>
      <div class="card velocity-block">
        <div class="velocity-head">
          <h3>Stage Velocity</h3>
          <span class="velocity-sub">average days between stages</span>
        </div>
        ${velocityFlowHtml(s2)}
        <div id="velocity-diagnostic" class="velocity-diag">Period-over-period diagnostic — coming next</div>
      </div>
    </div>

    <!-- SECTION 3 -->
    <div class="pillar">
      <div class="pillar-title"><h2>Opportunity → Closed Won</h2>
        <span class="sub">pipeline, win type, revenue</span></div>
      <div class="cards c2">
        <div class="card tall"><h3>Pipeline value &amp; deal volume by segment</h3>
          <div class="chart-wrap"><canvas id="c-pipeline"></canvas></div></div>
        <div class="card"><h3>Win count &amp; win rate by win type</h3>
          <div class="chart-wrap"><canvas id="c-wintype"></canvas></div></div>
      </div>
      <div class="cards c2" style="margin-top:16px">
        <div class="card tall"><h3>Running ACV (cumulative contract value)</h3>
          <div class="chart-wrap"><canvas id="c-runacv"></canvas></div></div>
        <div class="card"><h3>Revenue per win type <span style="color:var(--ink-mute);font-weight:400">(avg ACV)</span></h3>
          <div class="chart-wrap" style="height:200px"><canvas id="c-revtype"></canvas></div>
          <div class="note">${escapeHtml(revNote)}</div></div>
      </div>
    </div>`;

  attachDashFilters();
  drawCharts(d);
}

function optionList(items, selected, allLabel) {
  const opts = [`<option value="">${escapeHtml(allLabel)}</option>`];
  for (const it of items || []) {
    opts.push(`<option value="${escapeAttr(it)}" ${it === selected ? "selected" : ""}>${escapeHtml(it)}</option>`);
  }
  return opts.join("");
}

// --- multi-select dropdown (checkbox panel) ---------------------------------
// A button styled like the filter-bar selects that opens a checkbox panel.
// `selected` is the array from state.filters[key]; empty = "all" (allLabel).
function msLabel(selected, allLabel) {
  const sel = selected || [];
  if (sel.length === 0) return allLabel;
  if (sel.length === 1) return sel[0];
  return `${sel.length} selected`;
}

function multiSelectHtml(key, items, selected, allLabel) {
  const sel = selected || [];
  const opts = (items || [])
    .map((it) =>
      `<label class="ms-opt"><input type="checkbox" value="${escapeAttr(it)}" ${sel.includes(it) ? "checked" : ""}/>` +
      `<span>${escapeHtml(it)}</span></label>`
    )
    .join("");
  return `<div class="ms" data-ms="${escapeAttr(key)}">
      <button type="button" class="ms-toggle" data-all="${escapeAttr(allLabel)}">${escapeHtml(msLabel(sel, allLabel))} <span class="ms-caret">▾</span></button>
      <div class="ms-panel" hidden>${opts}</div>
    </div>`;
}

// --- scorecard tiles (from business_funnel) ---------------------------------
// Each tile: { key, label, fmt, kind, title? }.
//   kind "rel" -> delta shown as relative %  (count / $ metrics)
//   kind "pp"  -> delta shown in percentage POINTS (rate metrics)
function scorecardsHtml(bf) {
  if (!bf) return "";
  const num = (n) => (Number(n) || 0).toLocaleString();
  const fmtPct = (r) => (r == null ? "—" : Math.round(r * 100) + "%");
  const tiles = [
    { key: "specs", label: "Total Specs", fmt: num, kind: "rel" },
    { key: "opportunities", label: "Opportunities", fmt: num, kind: "rel" },
    { key: "won", label: "Closed Won", fmt: num, kind: "rel" },
    { key: "won_acv", label: "Won ACV", fmt: fmtMoney, kind: "rel" },
    { key: "open_pipeline", label: "Open Pipeline", fmt: fmtMoney, kind: "rel" },
    { key: "spec_to_opp_rate", label: "Spec→Opp Conv", fmt: fmtPct, kind: "pp" },
    { key: "win_rate_all", label: "Win Rate", fmt: fmtPct, kind: "pp", title: "Won ÷ all opps (not win-among-closed)" },
  ];
  const prior = bf.prior || null;
  return `<div class="scorecard-row">${tiles
    .map((t) => {
      const cur = bf[t.key];
      const valHtml = `<div class="sc-v">${escapeHtml(t.fmt(cur))}</div>`;
      const labelHtml = t.title
        ? `<div class="sc-l" title="${escapeAttr(t.title)}">${escapeHtml(t.label)} <span class="sc-info">ⓘ</span></div>`
        : `<div class="sc-l">${escapeHtml(t.label)}</div>`;
      return `<div class="scorecard">${valHtml}${labelHtml}${deltaHtml(cur, prior ? prior[t.key] : undefined, t.kind)}</div>`;
    })
    .join("")}</div>`;
}

// MoM-style delta line. Hidden (empty string) when prior is absent or its value
// is null/0 — never "▲∞%". "rel" = relative %; "pp" = percentage points.
function deltaHtml(cur, prev, kind) {
  if (prev == null || cur == null) return "";
  let amount, suffix;
  if (kind === "pp") {
    amount = Math.round((cur - prev) * 100);           // points on a 0-1 rate
    suffix = "pp";
  } else {
    if (!prev) return "";                               // prior 0 -> no relative %
    amount = Math.round(((cur - prev) / prev) * 100);   // relative %
    suffix = "%";
  }
  if (amount === 0) return `<div class="sc-d sc-flat">▬ 0${suffix} vs prior period</div>`;
  const up = amount > 0;
  const arrow = up ? "▲" : "▼";
  const cls = up ? "sc-up" : "sc-down";
  return `<div class="sc-d ${cls}">${arrow}${Math.abs(amount)}${suffix} vs prior period</div>`;
}

// --- pipeline FLOW Sankey (hand-rolled SVG; stage-to-stage transitions) -------
// Left-to-right flow: nodes are stages in funnel-depth columns (Discovery,
// Proposal, Negotiation, then a terminal column of Closed Won / Closed Lost).
// Each transition is a curved band from its from-node to its to-node, thickness
// ∝ $ amount (dollar-weighted). Bypass bands (Discovery→Negotiation) sweep past
// the Proposal column; early-exit bands (Discovery→Closed Lost) run to the
// terminal column — both read as "skips". Terminal-bound bands are colored by
// destination (Won green, Lost grey); in-funnel advances use the navy→periwinkle
// ramp. A per-transition legend (deals + $) renders beneath the SVG.
function pipelineFlowSvg(flow) {
  const transitions = (flow && flow.transitions) || [];
  const openNow = (flow && flow.open_now) || [];
  const STAGES = ["Discovery", "Proposal", "Negotiation", "Closed Won", "Closed Lost"];
  const COLS = { "Discovery": 0, "Proposal": 1, "Negotiation": 2, "Closed Won": 3, "Closed Lost": 3 };
  const RANK = {}; STAGES.forEach((s, i) => (RANK[s] = i));
  const openMap = {}; openNow.forEach((o) => (openMap[o.stage] = o));

  const totalAmt = transitions.reduce((a, t) => a + (t.amount || 0), 0);
  if (!transitions.length || totalAmt <= 0) {
    return `<svg class="viz-svg" viewBox="0 0 760 80" preserveAspectRatio="xMidYMid meet"><text x="380" y="44" text-anchor="middle" class="sk-empty">No deal transitions in range</text></svg>`;
  }

  const inflow = {}, outflow = {}, inDeals = {};
  STAGES.forEach((s) => { inflow[s] = 0; outflow[s] = 0; inDeals[s] = 0; });
  transitions.forEach((t) => {
    outflow[t.from] += t.amount || 0;
    inflow[t.to] += t.amount || 0;
    inDeals[t.to] += t.deals || 0;
  });
  const openAmt = (s) => (openMap[s] ? openMap[s].amount || 0 : 0);
  // node $ value: Discovery (source) = outflow + still-open; others balance to inflow
  const nodeVal = {};
  STAGES.forEach((s) => { nodeVal[s] = s === "Discovery" ? outflow[s] + openAmt(s) : inflow[s]; });

  // geometry
  const W = 760, padTop = 30, padBot = 12, nodeW = 13, availH = 300, GAPN = 16;
  const f1 = (n) => n.toFixed(1);
  const colX = [70, 290, 470, 650];
  const colNodes = [[], [], [], []];
  STAGES.forEach((s) => colNodes[COLS[s]].push(s));
  const colTotal = colNodes.map((list) => list.reduce((a, s) => a + nodeVal[s], 0));
  const maxNodes = Math.max(...colNodes.map((l) => l.length));
  const scale = (availH - (maxNodes - 1) * GAPN) / Math.max(...colTotal, 1);
  const H = padTop + availH + padBot;

  // place nodes (centered vertical stack per column)
  const nodes = {};
  colNodes.forEach((list, c) => {
    const stackH = list.reduce((a, s) => a + Math.max(3, nodeVal[s] * scale), 0) + (list.length - 1) * GAPN;
    let y = padTop + (availH - stackH) / 2;
    list.forEach((s) => {
      const h = Math.max(3, nodeVal[s] * scale);
      nodes[s] = { x: colX[c], y, h, c };
      y += h + GAPN;
    });
  });

  // band port allocation: out-ports stack top-down by funnel order (already sorted
  // by the backend); in-ports stack by (to-rank, from-rank). Mutating shared objs.
  const bands = transitions.map((t) => ({ ...t, h: Math.max(2, (t.amount || 0) * scale) }));
  const outCur = {}, inCur = {};
  STAGES.forEach((s) => { outCur[s] = nodes[s].y; inCur[s] = nodes[s].y; });
  bands.forEach((b) => { b.sy0 = outCur[b.from]; outCur[b.from] += b.h; });
  [...bands].sort((a, b) => (RANK[a.to] - RANK[b.to]) || (RANK[a.from] - RANK[b.from]))
    .forEach((b) => { b.ty0 = inCur[b.to]; inCur[b.to] += b.h; });

  const nodeColor = { "Discovery": C.navy, "Proposal": C.periDim, "Negotiation": C.peri, "Closed Won": C.green, "Closed Lost": C.lost };
  const bandColor = (t) => t.to === "Closed Won" ? C.green : t.to === "Closed Lost" ? C.lost : (nodeColor[t.from] || C.peri);

  let svg = `<svg class="viz-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Pipeline deal-journey flow, dollar-weighted">`;
  // bands first (under nodes)
  bands.forEach((b) => {
    const x0 = nodes[b.from].x + nodeW, x1 = nodes[b.to].x, xm = (x0 + x1) / 2;
    const d =
      `M ${x0} ${f1(b.sy0)} C ${xm} ${f1(b.sy0)}, ${xm} ${f1(b.ty0)}, ${x1} ${f1(b.ty0)} ` +
      `L ${x1} ${f1(b.ty0 + b.h)} C ${xm} ${f1(b.ty0 + b.h)}, ${xm} ${f1(b.sy0 + b.h)}, ${x0} ${f1(b.sy0 + b.h)} Z`;
    svg += `<path d="${d}" fill="${bandColor(b)}" opacity="0.42" />`;
  });
  // nodes + labels
  STAGES.forEach((s) => {
    const n = nodes[s];
    svg += `<rect x="${n.x}" y="${f1(n.y)}" width="${nodeW}" height="${f1(n.h)}" rx="2" fill="${nodeColor[s]}" />`;
    const open = openMap[s];
    if (n.c < 3) {
      // funnel node: name above, "(N open)" line beneath the name
      svg += `<text x="${n.x + nodeW / 2}" y="${f1(n.y - 14)}" text-anchor="middle" class="fl-node">${escapeHtml(s)}</text>`;
      if (open) svg += `<text x="${n.x + nodeW / 2}" y="${f1(n.y - 3)}" text-anchor="middle" class="fl-open">${open.deals} open · ${fmtMoney(open.amount)}</text>`;
    } else {
      // terminal node: label to the right (stage + total deals in)
      svg += `<text x="${n.x + nodeW + 8}" y="${f1(n.y + n.h / 2 + 4)}" class="fl-node">${escapeHtml(s)} · ${inDeals[s]} · ${fmtMoney(inflow[s])}</text>`;
    }
  });
  svg += `</svg>`;

  // legend: one row per transition (deals + $), colored swatch keyed to the band.
  const legend = `<div class="flow-legend">${transitions.map((t) =>
    `<div class="fl-item"><span class="fl-swatch" style="background:${bandColor(t)}"></span>` +
    `<span class="fl-route">${escapeHtml(t.from)} → ${escapeHtml(t.to)}</span>` +
    `<span class="fl-stat">${t.deals} · ${fmtMoney(t.amount)}</span></div>`).join("")}</div>`;
  return svg + legend;
}

// Prominent stage-velocity step-flow. SAME data + values as before (velocity_days
// avg_days between consecutive stages); only the rendering is promoted from tiny
// grey text to a titled chip/connector flow.
function velocityFlowHtml(s2) {
  const velo = (s2 && s2.velocity_days) || [];
  // Discovery →(Xd)→ Proposal →(Yd)→ Negotiation →(Zd)→ Closed
  const order = ["Discovery", "Proposal", "Negotiation", "Closed"];
  const vmap = {};
  velo.forEach((v) => { vmap[v.from] = v.avg_days; });
  const parts = [];
  order.forEach((st, i) => {
    parts.push(`<span class="vf-chip">${escapeHtml(st)}</span>`);
    if (i < order.length - 1) {
      const days = vmap[st];
      parts.push(`<span class="vf-conn"><span class="vf-days">${days == null ? "—" : days + "d"}</span></span>`);
    }
  });
  return `<div class="velocity-flow">${parts.join("")}</div>`;
}

function attachDashFilters() {
  // STATIC REPLAY: wire NO handlers — the filter bar is visibly disabled and must
  // not trigger a no-op loadDashboard() (it would refetch the same baked snapshot).
  // The dashboard already rendered from the baked payload; drawCharts runs after
  // this. Live mode (flag falsy): no early return → everything wires as today.
  if (window.STATIC_REPLAY) return;
  el("dash-refresh").addEventListener("click", () => { state.dashboard = null; loadDashboard(); });
  // Manually editing either date input means the range no longer matches a
  // preset, so clear the active-preset highlight.
  el("f-from").addEventListener("change", (e) => { state.filters.date_from = e.target.value; state.filters.preset = ""; loadDashboard(); });
  el("f-to").addEventListener("change", (e) => { state.filters.date_to = e.target.value; state.filters.preset = ""; loadDashboard(); });
  el("f-presets").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-preset]");
    if (b) applyPreset(b.dataset.preset);
  });
  el("f-cadence").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-cad]");
    if (b) { state.filters.cadence = b.dataset.cad; loadDashboard(); }
  });
  // multi-select dropdowns (use_case / segment / region)
  document.querySelectorAll(".ms").forEach((ms) => wireMultiSelect(ms));
  // re-open a panel that was open before the re-render (each checkbox change
  // re-renders the dashboard; this keeps the panel open for further selection)
  if (state.openMs) {
    const panel = document.querySelector(`.ms[data-ms="${state.openMs}"] .ms-panel`);
    if (panel) panel.hidden = false;
  }
}

function closeAllMsPanels() {
  document.querySelectorAll(".ms-panel").forEach((p) => { p.hidden = true; });
}

function wireMultiSelect(ms) {
  const key = ms.dataset.ms;
  const toggle = ms.querySelector(".ms-toggle");
  const panel = ms.querySelector(".ms-panel");
  toggle.addEventListener("click", (e) => {
    e.stopPropagation();   // don't let the document outside-click handler see this
    if (state.openMs === key) { state.openMs = null; panel.hidden = true; }
    else { closeAllMsPanels(); state.openMs = key; panel.hidden = false; }
  });
  panel.addEventListener("change", (e) => {
    const cb = e.target;
    if (!cb.matches || !cb.matches('input[type="checkbox"]')) return;
    const arr = state.filters[key];   // array; "" -> all
    if (cb.checked) { if (!arr.includes(cb.value)) arr.push(cb.value); }
    else { const i = arr.indexOf(cb.value); if (i >= 0) arr.splice(i, 1); }
    state.openMs = key;   // keep this panel open across the re-render
    loadDashboard();      // apply immediately (consistent with the other filters)
  });
}

function applyPreset(p) {
  const today = new Date();
  const isoD = (d) => d.toISOString().slice(0, 10);
  let from;
  const to = isoD(today);
  if (p === "ytd") from = `${today.getFullYear()}-01-01`;
  else if (p === "6m") { const d = new Date(today); d.setMonth(d.getMonth() - 6); from = isoD(d); }
  else if (p === "30d") { const d = new Date(today); d.setDate(d.getDate() - 30); from = isoD(d); }
  else { const d = new Date(today); d.setDate(d.getDate() - 7); from = isoD(d); }
  state.filters.date_from = from;
  state.filters.date_to = to;
  state.filters.preset = p;   // highlight the chosen preset (UI-only)
  loadDashboard();
}

function pct(x) { return x == null ? "—" : Math.round(x * 100) + "%"; }

// Palette for charts — navy/periwinkle to match the chrome. Green/red keep their
// Slack semantics (Closed Won / approved = green; rejected = red).
const C = {
  ink: "#131722", navy: "#1E2740", navyMid: "#2A3454", slate: "#9AA3B8",
  peri: "#6C7CF0", periSoft: "#8B93F8", periDim: "#4E5AC0",
  green: "#2EB67D", greenD: "#259c69", red: "#E01E5A", lost: "#B9BECC", mute: "#6B7280",
};

function destroyCharts() {
  Object.values(state.charts).forEach((c) => c && c.destroy());
  state.charts = {};
}

function drawCharts(d) {
  destroyCharts();
  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  Chart.defaults.color = "#3A4150";

  const s1 = d.spec_generation;
  const s3 = d.opportunity_to_won;
  const wtLabels = d.win_type_labels || {};
  const wtKeys = Object.keys(wtLabels);

  // SECTION 1 — three time-series LINE charts (x = cadence buckets).
  const statusColor = { draft: C.slate, in_review: C.peri, approved: C.green, rejected: C.red };
  lineChart("c-spec-status", s1.spec_volume_by_status, (k) => statusColor[k] || C.peri);
  lineChart("c-rej-reason", s1.rejection_volume_by_reason, (k, i) => seriesColor(i));
  // Approval-by-use-case has 15+ series -> keep top 5 by total volume, collapse the
  // rest into a muted-grey "Other". Frontend-only; backend response unchanged.
  const apprUc = topNSeries(s1.approval_volume_by_use_case, 5, "Other");
  lineChart("c-appr-uc", apprUc, (k, i) => (k === "Other" ? C.mute : seriesColor(i)));

  // SECTION 2 — funnel + Sankey + velocity are now hand-rolled SVG/HTML rendered
  // in renderDashboard's template (no Chart.js instance here). The old c-funnel
  // bar chart was removed, so nothing is tracked in state.charts for it.

  // SECTION 3a — pipeline value (bars) + deal volume (line) by segment (KEPT).
  const seg = s3.pipeline_value_and_volume_by_segment || {};
  const segLabels = Object.keys(seg);
  state.charts.pipeline = new Chart(el("c-pipeline"), {
    type: "bar",
    data: {
      labels: segLabels,
      datasets: [
        { type: "bar", label: "Pipeline value", yAxisID: "y",
          data: segLabels.map((s) => seg[s].pipeline_value), backgroundColor: C.peri, borderRadius: 6 },
        { type: "line", label: "Deal volume", yAxisID: "y1",
          data: segLabels.map((s) => seg[s].deal_volume),
          borderColor: C.ink, backgroundColor: C.ink, tension: 0.3, borderWidth: 3, pointRadius: 5, pointBackgroundColor: C.ink },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { position: "bottom" },
        tooltip: { callbacks: { label: (ctx) =>
          ctx.dataset.label === "Pipeline value" ? `Pipeline value: ${fmtMoney(ctx.raw)}` : `Deal volume: ${ctx.raw}` } } },
      scales: {
        y: { position: "left", beginAtZero: true, ticks: { callback: (v) => fmtMoney(v) }, title: { display: true, text: "Pipeline value" } },
        y1: { position: "right", beginAtZero: true, grid: { drawOnChartArea: false }, ticks: { precision: 0 }, title: { display: true, text: "Deal volume" } },
      },
    },
  });

  // SECTION 3b — win count & win rate by win type.
  const wr = s3.win_rate_by_win_type || {};
  state.charts.wintype = new Chart(el("c-wintype"), {
    type: "bar",
    data: {
      labels: wtKeys.map((k) => wtLabels[k]),
      datasets: [{ data: wtKeys.map((k) => (wr[k] ? wr[k].wins : 0)),
        backgroundColor: [C.peri, C.periDim, C.green, C.slate], borderRadius: 6 }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => {
          const k = wtKeys[ctx.dataIndex]; const r = wr[k] ? wr[k].win_rate : null;
          return `${ctx.raw} wins · ${r == null ? "—" : Math.round(r * 100) + "% of closed"}`;
        } } } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });

  // SECTION 3c — running ACV (cumulative line).
  const ra = s3.running_acv || [];
  state.charts.runacv = new Chart(el("c-runacv"), {
    type: "line",
    data: {
      labels: ra.map((r) => r.period),
      datasets: [{ label: "Running ACV", data: ra.map((r) => r.running_acv),
        borderColor: C.peri, backgroundColor: "rgba(108,124,240,0.12)", fill: true, tension: 0.3, borderWidth: 2, pointRadius: 2 }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => `Cumulative ACV: ${fmtMoney(ctx.raw)}` } } },
      scales: { y: { beginAtZero: true, ticks: { callback: (v) => fmtMoney(v) } }, x: { ticks: { maxRotation: 0, autoSkip: true } } },
    },
  });

  // SECTION 3d — revenue per win type (avg ACV — the efficiency story).
  const rev = (s3.revenue_per_win_type || {}).by_type || {};
  state.charts.revtype = new Chart(el("c-revtype"), {
    type: "bar",
    data: {
      labels: wtKeys.map((k) => wtLabels[k]),
      datasets: [{ data: wtKeys.map((k) => (rev[k] ? rev[k].avg_acv : null)),
        backgroundColor: C.periDim, borderRadius: 6 }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => `Avg ACV: ${ctx.raw == null ? "—" : fmtMoney(ctx.raw)}` } } },
      scales: { y: { beginAtZero: true, ticks: { callback: (v) => fmtMoney(v) } } },
    },
  });
}

// Keep the top-N series (by total volume across all periods) and collapse the
// rest into one `otherLabel` series (per-period sum of the dropped keys). Returns
// the same {keys, data} shape lineChart expects. No-op when keys.length <= n.
function topNSeries(series, n, otherLabel) {
  const keys = (series && series.keys) || [];
  const data = (series && series.data) || [];
  if (keys.length <= n) return series;
  const totals = keys
    .map((k) => ({ k, total: data.reduce((s, r) => s + (r[k] || 0), 0) }))
    .sort((a, b) => b.total - a.total);
  const top = totals.slice(0, n).map((x) => x.k);
  const topSet = new Set(top);
  const newData = data.map((r) => {
    const row = { period: r.period };
    let other = 0;
    for (const k of keys) {
      if (topSet.has(k)) row[k] = r[k] || 0;
      else other += r[k] || 0;
    }
    row[otherLabel] = other;
    return row;
  });
  return { keys: [...top, otherLabel], data: newData };
}

// Generic time-series LINE chart for Section 1 ({keys, data:[{period, k:v}]}).
function lineChart(canvasId, series, colorFor) {
  const data = (series && series.data) || [];
  const keys = (series && series.keys) || [];
  const labels = data.map((r) => r.period);
  const datasets = keys.map((k, i) => {
    const col = colorFor(k, i);
    return { label: prettyKey(k), data: data.map((r) => r[k] || 0),
      borderColor: col, backgroundColor: col, tension: 0.3, borderWidth: 2, pointRadius: 2, fill: false };
  });
  state.charts[canvasId] = new Chart(el(canvasId), {
    type: "line",
    data: { labels, datasets },
    options: {
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } }, x: { ticks: { maxRotation: 0, autoSkip: true } } },
    },
  });
}

// Distinct-ish color cycle for dynamic series (rejection reasons, use cases).
const SERIES_PALETTE = ["#6C7CF0", "#2EB67D", "#4E5AC0", "#2A3454", "#E8A13B", "#9AA3B8", "#8B93F8", "#E01E5A"];
function seriesColor(i) { return SERIES_PALETTE[i % SERIES_PALETTE.length]; }

function prettyStatus(s) {
  return { draft: "Draft", in_review: "In review", approved: "Approved", rejected: "Rejected" }[s] || s;
}
function prettyKey(k) { return String(k).replace(/_/g, " "); }

// ---------------------------------------------------------------- init
function initComposer() {
  const sel = el("transcript-select");
  sel.innerHTML = Object.entries(window.TRANSCRIPTS)
    .map(([k, t]) => `<option value="${k}">${t.label}</option>`).join("");
  const updatePreview = () => {
    const t = window.TRANSCRIPTS[sel.value];
    el("composer-preview").textContent = t ? t.text.slice(0, 320) + "…" : "";
  };
  sel.addEventListener("change", updatePreview);
  updatePreview();
  el("run-spec").addEventListener("click", (e) => runBusy(e.currentTarget, runSpec, "Running /spec…"));
}

function init() {
  // nav
  document.querySelectorAll(".chan-item").forEach((b) =>
    b.addEventListener("click", () => setTab(b.dataset.tab)));
  // delegated button clicks across the three channels
  ["spec-list", "review-list", "deal-list"].forEach((id) =>
    el(id).addEventListener("click", onChannelClick));
  // live char counter for the regenerate composer (review channel)
  el("review-list").addEventListener("input", onReviewInput);
  // close any open multi-select panel on an outside click (added once; the
  // panels' selections are already applied live, so no reload is needed here)
  document.addEventListener("click", (e) => {
    if (!state.openMs) return;
    if (e.target.closest && e.target.closest(".ms")) return;
    state.openMs = null;
    closeAllMsPanels();
  });

  initComposer();
  renderSpec();
  renderReview();
  renderDeal();
}

document.addEventListener("DOMContentLoaded", init);
