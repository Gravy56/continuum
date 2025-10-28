const API_URL = "https://continuum-5ue5.onrender.com";
const socket = io(API_URL);

let nickname = "";
let timeLeft = 0;
let timerInterval = null;

const joinBtn = document.getElementById("join-btn");
const nicknameInput = document.getElementById("nickname");
const queueStatus = document.getElementById("queue-status");
const writingSection = document.getElementById("writing-section");
const previousEntry = document.getElementById("previous-entry");
const newEntry = document.getElementById("new-entry");
const timerDisplay = document.getElementById("timer");
const submitBtn = document.getElementById("submit-btn");
const bookContent = document.getElementById("book-content");

async function joinQueue() {
  nickname = nicknameInput.value.trim();
  if (!nickname) return alert("Enter a nickname!");

  const res = await fetch(`${API_URL}/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: nickname })
  });
  const data = await res.json();
  queueStatus.textContent = data.message;
}

async function fetchBook() {
  const res = await fetch(`${API_URL}/entries`);
  const data = await res.json();
  bookContent.innerHTML = data.map(e => `<p><b>${e.author}:</b> ${e.text}</p>`).join("");
}

function startTurn(user, duration) {
  if (user !== nickname) {
    writingSection.classList.add("hidden");
    timerDisplay.textContent = `${user}'s turn (${duration}s)`;
    return;
  }
  writingSection.classList.remove("hidden");
  newEntry.value = "";
  fetchLastEntry();

  timeLeft = duration;
  timerDisplay.textContent = `Time left: ${timeLeft}s`;

  timerInterval = setInterval(() => {
    timeLeft -= 1;
    timerDisplay.textContent = `Time left: ${timeLeft}s`;
    if (timeLeft <= 0) endTurn();
  }, 1000);
}

function endTurn() {
  clearInterval(timerInterval);
  writingSection.classList.add("hidden");
  timerDisplay.textContent = "";
}

async function fetchLastEntry() {
  const res = await fetch(`${API_URL}/entries`);
  const data = await res.json();
  const lastEntry = data[data.length - 1];
  previousEntry.textContent = lastEntry ? lastEntry.text : "The story begins...";
}

submitBtn.addEventListener("click", async () => {
  const text = newEntry.value.trim();
  if (!text) return;

  await fetch(`${API_URL}/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: nickname, text })
  });
  newEntry.value = "";
  endTurn();
});

joinBtn.addEventListener("click", joinQueue);

// Live socket updates
socket.on("new_entry", entry => {
  const p = document.createElement("p");
  p.innerHTML = `<b>${entry.author}:</b> ${entry.text}`;
  bookContent.appendChild(p);
});

socket.on("turn_start", data => startTurn(data.user, data.time));
socket.on("turn_end", data => {
  if (data.user === nickname) endTurn();
});

// Load initial book
fetchBook();
