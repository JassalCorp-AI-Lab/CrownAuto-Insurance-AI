// CrownAuto Insurance AI — minimal chat client.
// Streams graph progress over SSE (fetch + ReadableStream, since EventSource can't POST).

const $ = (sel) => document.querySelector(sel);
const chatEl = $("#chat");
const welcomeEl = $("#welcome");
const form = $("#composer");
const input = $("#input");
const sendBtn = $("#send");
const fileInput = $("#fileInput");
const attachmentEl = $("#attachment");
const attachmentImg = $("#attachmentImg");
const attachmentName = $("#attachmentName");

const MAX_IMAGE_MB = 8;
const TOOL_LABELS = {
  vehicle_lookup: "Looking up vehicle",
  calculate_premium: "Calculating premiums",
  postal_code_risk: "Checking territory risk",
  verify_policy: "Verifying policy",
  analyze_damage_image: "Analyzing damage photo (vision)",
  estimate_payout: "Estimating payout",
  policy_kb_search: "Searching policy knowledge base",
};

let sessionId = newSessionId();
let pendingFile = null;
let busy = false;

function newSessionId() {
  return (crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random())).slice(0, 36);
}

// ─── Tiny, safe Markdown renderer (escape first, then format) ──────────
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function inline(s) {
  return s
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
}
function renderMarkdown(text) {
  const lines = escapeHtml(text || "").split(/\r?\n/);
  let html = "", list = null, para = [];
  const flushPara = () => { if (para.length) { html += `<p>${inline(para.join("<br>"))}</p>`; para = []; } };
  const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
  for (const raw of lines) {
    const line = raw.trimEnd();
    let m;
    if (!line.trim()) { flushPara(); closeList(); continue; }
    if (/^(-{3,}|\*{3,})$/.test(line.trim())) { flushPara(); closeList(); html += "<hr>"; continue; }
    if ((m = line.match(/^#{1,6}\s+(.*)$/))) { flushPara(); closeList(); html += `<h4>${inline(m[1])}</h4>`; continue; }
    if ((m = line.match(/^\s*[-*•]\s+(.*)$/))) {
      flushPara(); if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; }
      html += `<li>${inline(m[1])}</li>`; continue;
    }
    if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
      flushPara(); if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; }
      html += `<li>${inline(m[1])}</li>`; continue;
    }
    closeList(); para.push(line);
  }
  flushPara(); closeList();
  return html;
}

// ─── DOM helpers ───────────────────────────────────────────────────────
function scrollDown() { chatEl.scrollTop = chatEl.scrollHeight; }

function addUserMessage(text, imageUrl) {
  welcomeEl.hidden = true;
  const row = document.createElement("div");
  row.className = "msg user";
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  if (imageUrl) {
    const img = document.createElement("img");
    img.src = imageUrl; img.alt = "Uploaded damage photo";
    bubble.appendChild(img);
  }
  if (text) bubble.appendChild(document.createTextNode(text));
  row.appendChild(bubble);
  chatEl.appendChild(row);
  scrollDown();
}

function addBotMessage() {
  const row = document.createElement("div");
  row.className = "msg bot";
  row.innerHTML = `
    <div class="bubble">
      <div class="meta"></div>
      <div class="progress"><ul class="steps"><li class="pending">Understanding your request…</li></ul></div>
      <div class="content"></div>
    </div>`;
  chatEl.appendChild(row);
  scrollDown();
  const q = (s) => row.querySelector(s);
  return { row, bubble: q(".bubble"), meta: q(".meta"), steps: q(".steps"), progress: q(".progress"), content: q(".content"), tools: [] };
}

function setStep(view, text, pending = true) {
  const prev = view.steps.querySelector("li.pending");
  if (prev) prev.classList.remove("pending");
  const li = document.createElement("li");
  li.innerHTML = text;
  if (pending) li.className = "pending";
  view.steps.appendChild(li);
  scrollDown();
}

function addAgentBadge(view, agent, label) {
  const b = document.createElement("span");
  b.className = `badge ${agent || ""}`;
  b.textContent = label || agent || "Assistant";
  view.meta.appendChild(b);
}

function addToolChip(view, name) {
  const chip = document.createElement("span");
  chip.className = "tool";
  chip.textContent = name;
  view.meta.appendChild(chip);
  view.tools.push({ name, el: chip, done: false });
}

function markTool(view, name, ok) {
  const t = view.tools.find((x) => x.name === name && !x.done);
  if (t) { t.done = true; t.el.classList.add(ok ? "ok" : "fail"); }
}

// ─── Event handling ────────────────────────────────────────────────────
function handleEvent(view, ev) {
  switch (ev.type) {
    case "route":
      addAgentBadge(view, ev.agent, ev.label);
      setStep(view, `Routed to <strong>${escapeHtml(ev.label || ev.agent)}</strong> — thinking…`);
      break;
    case "tool_call":
      addToolChip(view, ev.name);
      setStep(view, `${escapeHtml(TOOL_LABELS[ev.name] || ev.name)} <code>${escapeHtml(ev.name)}</code>`);
      break;
    case "tool_result":
      markTool(view, ev.name, ev.ok);
      setStep(view, "Composing reply…");
      break;
    case "final":
      view.progress.remove();
      view.content.innerHTML = renderMarkdown(ev.reply);
      break;
    case "error":
      view.progress.remove();
      view.bubble.classList.add("error");
      view.content.textContent = "⚠️ " + ev.message;
      break;
  }
  scrollDown();
}

async function send(text) {
  if (busy) return;
  text = (text || "").trim();
  const file = pendingFile;
  if (!text && !file) return;

  busy = true; sendBtn.disabled = true;
  const previewUrl = file ? URL.createObjectURL(file) : null;
  addUserMessage(text, previewUrl);
  input.value = ""; autoGrow(); clearAttachment();

  const view = addBotMessage();
  const body = new FormData();
  body.append("message", text);
  body.append("session_id", sessionId);
  if (file) body.append("image", file);

  let gotTerminal = false;
  try {
    const res = await fetch("/api/chat/stream", { method: "POST", body });
    if (!res.ok) {
      let detail = res.statusText;
      try { detail = (await res.json()).detail || detail; } catch {}
      throw new Error(detail);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        const data = frame.split("\n").filter((l) => l.startsWith("data:")).map((l) => l.slice(5).trim()).join("");
        if (!data) continue;
        const ev = JSON.parse(data);
        if (ev.type === "final" || ev.type === "error") gotTerminal = true;
        handleEvent(view, ev);
      }
    }
    if (!gotTerminal) handleEvent(view, { type: "error", message: "Connection closed before a reply was received." });
  } catch (err) {
    handleEvent(view, { type: "error", message: err.message || String(err) });
  } finally {
    busy = false; sendBtn.disabled = false; input.focus();
  }
}

// ─── Attachments ───────────────────────────────────────────────────────
function clearAttachment() {
  pendingFile = null; fileInput.value = "";
  if (attachmentImg.src.startsWith("blob:")) URL.revokeObjectURL(attachmentImg.src); // free preview memory
  attachmentEl.hidden = true; attachmentImg.removeAttribute("src");
}
fileInput.addEventListener("change", () => {
  const f = fileInput.files[0];
  if (!f) return;
  if (f.size > MAX_IMAGE_MB * 1024 * 1024) { alert(`Please choose an image under ${MAX_IMAGE_MB} MB.`); clearAttachment(); return; }
  pendingFile = f;
  attachmentImg.src = URL.createObjectURL(f);
  attachmentName.textContent = f.name;
  attachmentEl.hidden = false;
  input.focus();
});
$("#removeAttachment").addEventListener("click", clearAttachment);

// ─── Composer behaviour ────────────────────────────────────────────────
function autoGrow() { input.style.height = "auto"; input.style.height = Math.min(input.scrollHeight, 160) + "px"; }
input.addEventListener("input", autoGrow);
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input.value); }
});
form.addEventListener("submit", (e) => { e.preventDefault(); send(input.value); });

document.querySelectorAll(".chip").forEach((chip) =>
  chip.addEventListener("click", () => {
    const prompt = chip.dataset.prompt;
    if (prompt.includes("file a claim")) { input.value = prompt; autoGrow(); input.focus(); fileInput.click(); }
    else send(prompt);
  })
);

$("#newChat").addEventListener("click", async () => {
  if (busy) return;
  const old = sessionId;
  sessionId = newSessionId();
  chatEl.querySelectorAll(".msg").forEach((m) => m.remove());
  welcomeEl.hidden = false; clearAttachment(); input.value = ""; autoGrow();
  fetch(`/api/session/${encodeURIComponent(old)}`, { method: "DELETE" }).catch(() => {});
});

// ─── Health check ──────────────────────────────────────────────────────
(async function health() {
  const el = $("#status"), label = el.querySelector("b");
  try {
    const h = await (await fetch("/api/health")).json();
    if (h.api_key_configured) { el.className = "status ok"; label.textContent = h.chat_model; el.title = `Model: ${h.chat_model}`; }
    else { el.className = "status warn"; label.textContent = "No API key"; el.title = "Set OPENAI_API_KEY in .env and restart"; }
  } catch {
    el.className = "status err"; label.textContent = "Offline";
  }
})();
