const audioInput = document.getElementById("audioFile");
const transcriptArea = document.getElementById("transcript");
const transcribeBtn = document.getElementById("transcribeBtn");
const summarizeBtn = document.getElementById("summarizeBtn");
const count = document.getElementById("transcriptCount");
const notice = document.getElementById("notice");
const emptyState = document.getElementById("emptyState");
const results = document.getElementById("results");
const copyBtn = document.getElementById("copyBtn");
const downloadBtn = document.getElementById("downloadBtn");

let latestNotes = null;

function showNotice(message, isError = false) {
  notice.textContent = message;
  notice.classList.remove("hidden", "error");
  if (isError) notice.classList.add("error");
}
function clearNotice() {
  notice.classList.add("hidden");
  notice.classList.remove("error");
}
function setBusy(button, busy, label) {
  button.disabled = busy;
  if (busy) {
    button.dataset.originalText = button.textContent;
    button.textContent = label;
  } else {
    button.textContent = button.dataset.originalText || label;
  }
}
function updateCount() {
  count.textContent = `${transcriptArea.value.length.toLocaleString()} characters`;
}
transcriptArea.addEventListener("input", updateCount);

transcribeBtn.addEventListener("click", async () => {
  clearNotice();
  const file = audioInput.files[0];
  if (!file) {
    showNotice("Please choose a meeting audio file first.", true);
    return;
  }
  const formData = new FormData();
  formData.append("audio", file);
  setBusy(transcribeBtn, true, "Transcribing…");
  try {
    const response = await fetch("/api/transcribe", { method: "POST", body: formData });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Transcription failed.");
    transcriptArea.value = data.transcript || "";
    updateCount();
    showNotice("Transcription complete. Review the transcript, then generate meeting notes.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(transcribeBtn, false, "Transcribe with Prisma");
  }
});

summarizeBtn.addEventListener("click", async () => {
  clearNotice();
  const transcript = transcriptArea.value.trim();
  if (transcript.length < 20) {
    showNotice("Paste a transcript or transcribe an audio file before generating notes.", true);
    return;
  }
  setBusy(summarizeBtn, true, "Generating…");
  try {
    const response = await fetch("/api/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Summary generation failed.");
    latestNotes = data.notes;
    renderNotes(latestNotes);
    showNotice("Meeting notes generated. Please review names, decisions, and action items before sharing.");
  } catch (error) {
    showNotice(error.message, true);
  } finally {
    setBusy(summarizeBtn, false, "Generate meeting notes →");
  }
});

function fillList(elementId, items, emptyText = "None identified.") {
  const el = document.getElementById(elementId);
  el.replaceChildren();
  if (!Array.isArray(items) || items.length === 0) {
    const li = document.createElement("li");
    li.textContent = emptyText;
    el.appendChild(li);
    return;
  }
  items.forEach(item => {
    const li = document.createElement("li");
    li.textContent = typeof item === "string" ? item : JSON.stringify(item);
    el.appendChild(li);
  });
}
function renderNotes(notes) {
  emptyState.classList.add("hidden");
  results.classList.remove("hidden");
  document.getElementById("summaryText").textContent = notes.summary || "No summary returned.";
  fillList("keyPoints", notes.key_points);
  fillList("decisions", notes.decisions);
  fillList("openQuestions", notes.open_questions);

  const actions = document.getElementById("actionItems");
  actions.replaceChildren();
  if (!Array.isArray(notes.action_items) || notes.action_items.length === 0) {
    const p = document.createElement("p");
    p.textContent = "No action items identified.";
    p.style.color = "#849087";
    actions.appendChild(p);
  } else {
    notes.action_items.forEach(item => {
      const row = document.createElement("div");
      row.className = "action-row";
      const task = document.createElement("div");
      task.textContent = item.task || "Task not specified";
      const owner = document.createElement("div");
      owner.className = "owner";
      owner.textContent = `Owner: ${item.owner || "Not specified"}`;
      const deadline = document.createElement("div");
      deadline.className = "deadline";
      deadline.textContent = `Due: ${item.deadline || "Not specified"}`;
      row.append(task, owner, deadline);
      actions.appendChild(row);
    });
  }
  copyBtn.disabled = false;
  downloadBtn.disabled = false;
}
function notesAsMarkdown(notes) {
  const bullets = arr => (Array.isArray(arr) && arr.length ? arr.map(x => `- ${typeof x === "string" ? x : JSON.stringify(x)}`).join("\\n") : "- None identified");
  const actions = Array.isArray(notes.action_items) && notes.action_items.length
    ? notes.action_items.map(a => `- **${a.task || "Task"}** — Owner: ${a.owner || "Not specified"} — Deadline: ${a.deadline || "Not specified"}`).join("\\n")
    : "- None identified";
  return `# Meeting Notes\\n\\n## Executive Summary\\n${notes.summary || ""}\\n\\n## Key Discussion Points\\n${bullets(notes.key_points)}\\n\\n## Decisions\\n${bullets(notes.decisions)}\\n\\n## Action Items\\n${actions}\\n\\n## Open Questions\\n${bullets(notes.open_questions)}\\n`;
}
copyBtn.addEventListener("click", async () => {
  if (!latestNotes) return;
  try {
    await navigator.clipboard.writeText(notesAsMarkdown(latestNotes));
    showNotice("Meeting notes copied to clipboard.");
  } catch {
    showNotice("Clipboard access was blocked by the browser. Use Download .md instead.", true);
  }
});
downloadBtn.addEventListener("click", () => {
  if (!latestNotes) return;
  const blob = new Blob([notesAsMarkdown(latestNotes)], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "meeting-notes.md";
  a.click();
  URL.revokeObjectURL(url);
});
updateCount();
