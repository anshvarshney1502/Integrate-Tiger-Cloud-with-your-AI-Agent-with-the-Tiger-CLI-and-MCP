const API_BASE = window.location.origin;

async function fetchStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    if (!res.ok) throw new Error("Status API error");
    const data = await res.json();

    document.getElementById("mcp-status").textContent = "Tiger MCP: Active";
    document.getElementById("tools-count").textContent = data.tools_count || 0;
    document.getElementById("prompts-count").textContent = data.prompts_count || 0;
    document.getElementById("guardrail-status").textContent = `Mode: ${data.guardrail_mode ? data.guardrail_mode.toUpperCase() : "PROD"}`;

    renderBadges("tools-list", data.tools.map(t => t.name), "tool");
    renderBadges("skills-list", data.prompts.map(p => p.name), "prompt");
  } catch (err) {
    document.getElementById("mcp-status").textContent = "Tiger MCP: Offline";
    document.getElementById("mcp-status").className = "pill pill-warning";
    console.error("Failed to load status:", err);
  }
}

function renderBadges(containerId, items, type) {
  const container = document.getElementById(containerId);
  container.innerHTML = "";
  items.forEach(name => {
    const span = document.createElement("span");
    span.className = `badge ${type}`;
    span.textContent = name;
    container.appendChild(span);
  });
}

function switchTab(tabName) {
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.querySelectorAll(".tab-content").forEach(content => content.classList.remove("active"));

  if (event && event.target) {
    event.target.classList.add("active");
  }
  document.getElementById(`tab-${tabName}`).classList.add("active");

  if (tabName === "skill-viewer") {
    const select = document.getElementById("skill-select");
    loadSkill(select.value);
  }
}

function updateWeightLabel(val) {
  const pct = Math.round(val * 100);
  document.getElementById("weight-val").textContent = `${pct}% Vector / ${100 - pct}% BM25`;
}

async function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById("chat-input");
  const prompt = input.value.trim();
  if (!prompt) return;

  appendMessage("user", prompt);
  input.value = "";

  try {
    const res = await fetch(`${API_BASE}/api/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt })
    });
    const data = await res.json();
    let text = data.answer || JSON.stringify(data, null, 2);
    if (data.results && data.results.length > 0) {
      text += "\n\n" + data.results.map((r, i) => `**[${i+1}] ${r.title || "Doc"}**: ${r.content ? r.content.slice(0, 150) + "..." : ""}`).join("\n\n");
    }
    appendMessage("assistant", text);
  } catch (err) {
    appendMessage("assistant", `Error communicating with Tiger Agent: ${err.message}`);
  }
}

function appendMessage(sender, text) {
  const container = document.getElementById("chat-messages");
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${sender}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = text.replace(/\n/g, "<br>");

  msgDiv.appendChild(bubble);
  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;
}

function runQuickAction(prompt) {
  switchTab("chat");
  document.getElementById("chat-input").value = prompt;
  document.getElementById("chat-form").dispatchEvent(new Event("submit"));
}

async function handleDocsSearch() {
  const input = document.getElementById("docs-search-input");
  const query = input.value.trim();
  if (!query) return;

  const weight = parseFloat(document.getElementById("semantic-weight").value);
  const resultsContainer = document.getElementById("docs-results");
  resultsContainer.innerHTML = "<p class='placeholder-text'>Searching Tiger Data documentation...</p>";

  try {
    const res = await fetch(`${API_BASE}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit: 5, semantic_weight: weight })
    });
    const data = await res.json();
    if (!data.results || data.results.length === 0) {
      resultsContainer.innerHTML = "<p class='placeholder-text'>No matching documentation found.</p>";
      return;
    }

    resultsContainer.innerHTML = "";
    data.results.forEach((item, idx) => {
      const card = document.createElement("div");
      card.className = "doc-card";
      card.innerHTML = `
        <h3>#${idx + 1} - ${item.title || item.id || "Documentation Section"}</h3>
        <p>${item.content || JSON.stringify(item)}</p>
      `;
      resultsContainer.appendChild(card);
    });
  } catch (err) {
    resultsContainer.innerHTML = `<p class='placeholder-text'>Search error: ${err.message}</p>`;
  }
}

async function loadSkill(skillName) {
  const preview = document.getElementById("skill-content");
  preview.textContent = `Loading skill: ${skillName}...`;
  try {
    const res = await fetch(`${API_BASE}/api/skill?name=${encodeURIComponent(skillName)}`);
    const data = await res.json();
    preview.textContent = data.content || data.error || "No content returned.";
  } catch (err) {
    preview.textContent = `Error loading skill: ${err.message}`;
  }
}

window.addEventListener("DOMContentLoaded", () => {
  fetchStatus();
});
