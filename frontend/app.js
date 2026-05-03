const userId = localStorage.getItem("electionAssistantUserId") || crypto.randomUUID();
localStorage.setItem("electionAssistantUserId", userId);

const chatLog = document.querySelector("#chat-log");
const profileForm = document.querySelector("#profile-form");
const chatForm = document.querySelector("#chat-form");
const timelineEl = document.querySelector("#timeline");
const centersEl = document.querySelector("#centers");
const guidanceEl = document.querySelector("#profile-guidance");

function currentProfile() {
  return {
    user_id: userId,
    age: Number(document.querySelector("#age").value),
    location: document.querySelector("#location").value.trim(),
    language: document.querySelector("#language").value.trim() || "English",
    first_time_voter: document.querySelector("#first-time").checked,
  };
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

function addMessage(role, content) {
  const bubble = document.createElement("div");
  bubble.className = `message ${role}`;
  bubble.textContent = content;
  chatLog.appendChild(bubble);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function saveProfile() {
  const payload = currentProfile();
  const result = await api("/user", { method: "POST", body: JSON.stringify(payload) });
  guidanceEl.textContent = result.guidance;
  await Promise.all([loadTimeline(), loadCenters()]);
}

async function sendMessage(message) {
  addMessage("user", message);
  const result = await api("/chat", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, message, profile: currentProfile() }),
  });
  addMessage("assistant", result.response);
}

async function loadTimeline() {
  const result = await api(`/timeline?user_id=${encodeURIComponent(userId)}`);
  timelineEl.innerHTML = "";
  result.steps.forEach((step) => {
    const item = document.createElement("li");
    const title = document.createElement("h3");
    const description = document.createElement("p");
    const actions = document.createElement("ul");
    title.textContent = step.title;
    description.textContent = step.description;
    step.actions.forEach((action) => {
      const actionItem = document.createElement("li");
      actionItem.textContent = action;
      actions.appendChild(actionItem);
    });
    item.append(title, description, actions);
    timelineEl.appendChild(item);
  });
}

async function loadCenters() {
  const result = await api(`/polling-centers?user_id=${encodeURIComponent(userId)}`);
  centersEl.innerHTML = "";
  result.centers.forEach((center) => {
    const card = document.createElement("article");
    card.className = "center";
    const name = document.createElement("strong");
    const address = document.createElement("p");
    const distance = document.createElement("p");
    name.textContent = center.name;
    address.textContent = center.address;
    distance.textContent = center.distance;
    card.append(name, address, distance);
    centersEl.appendChild(card);
  });
}

async function checkHealth() {
  const health = document.querySelector("#health");
  try {
    const result = await api("/health");
    health.textContent = result.firestore ? "Firestore connected" : "Local demo mode";
  } catch {
    health.textContent = "Service unavailable";
  }
}

profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  guidanceEl.textContent = "Saving profile...";
  try {
    await saveProfile();
  } catch (error) {
    guidanceEl.textContent = error.message;
  }
});

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = document.querySelector("#message");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  try {
    await sendMessage(message);
  } catch (error) {
    addMessage("assistant", `Sorry, I could not answer that yet. ${error.message}`);
  }
});

document.querySelectorAll("[data-message]").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.dataset.message));
});

document.querySelector("#refresh-timeline").addEventListener("click", loadTimeline);

checkHealth();
saveProfile();
addMessage("assistant", "Hi. Ask me about eligibility, documents, registration, polling day, or election timelines.");
