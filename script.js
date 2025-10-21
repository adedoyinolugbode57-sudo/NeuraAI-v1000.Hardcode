const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const upgradeBtn = document.getElementById("upgrade-btn");
const sessionHoursEl = document.getElementById("session-hours");
const bgSelect = document.getElementById("bg-select");
const langSelect = document.getElementById("lang-select");
const voiceToggle = document.getElementById("voice-toggle");

let voiceEnabled = true;  // Default voice ON
const userId = "local_user";  // Can be dynamic

// ----------------------------
// Helper: Display message
// ----------------------------
function displayMessage(sender, msg) {
    const div = document.createElement("div");
    div.className = sender;
    div.textContent = msg;
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ----------------------------
// Send message to Flask backend
// ----------------------------
async function sendMessage(message, premium=false) {
    const res = await fetch(`/chat?msg=${encodeURIComponent(message)}&user_id=${userId}&premium=${premium}`);
    const data = await res.json();
    displayMessage("bot", data.reply);
    sessionHoursEl.textContent = data.remaining_hours;
}

// ----------------------------
// Handle send button
// ----------------------------
sendBtn.addEventListener("click", () => {
    const message = userInput.value.trim();
    if(!message) return;
    displayMessage("user", message);
    sendMessage(message, false);
    userInput.value = "";
});

// ----------------------------
// Handle Enter key
// ----------------------------
userInput.addEventListener("keypress", (e) => {
    if(e.key === "Enter") sendBtn.click();
});

// ----------------------------
// Premium upgrade
// ----------------------------
upgradeBtn.addEventListener("click", async () => {
    const res = await fetch(`/upgrade?user_id=${userId}`, {method: "POST"});
    const data = await res.json();
    displayMessage("bot", data.message);
    sessionHoursEl.textContent = data.remaining_hours;
});

// ----------------------------
// Background selector
// ----------------------------
bgSelect.addEventListener("change", () => {
    document.querySelector(".app-container").className = `app-container ${bgSelect.value}`;
});

// ----------------------------
// Language selector (placeholder)
// ----------------------------
langSelect.addEventListener("change", () => {
    displayMessage("bot", `Language switched to ${langSelect.value}`);
});

// ----------------------------
// Voice toggle
// ----------------------------
voiceToggle.addEventListener("click", () => {
    voiceEnabled = !voiceEnabled;
    displayMessage("bot", `Voice ${voiceEnabled ? "enabled" : "disabled"}`);
});