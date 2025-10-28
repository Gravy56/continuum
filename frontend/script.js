const API_URL = "https://continuum-5ue5.onrender.com"; // replace with your actual Render backend URL
let nickname = "";
let timeLeft = 0;
let timerInterval = null;
let currentTurnUser = null;

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
  if (!nickname) return alert("Enter a nickname first!");

  const res = await fetch(`${API_URL}/join`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: nickname })
  });
  const data = await res.json();

  queueStatus.textContent = data.message || "Joined the queue!";
}

async function checkTurn() {
  const res = await fetch(`${API_URL}/current_turn`);
  const data = await res.json();

  if (!data.current) return;

  currentTurnUser = data.current.user;
  timeLeft = data.current.time_left;

  if (currentTurnUser === nickname) {
    startTurn();
  } else {
    endTurn();
  }

  updateTimerDisplay();
}

function startTurn() {
  writingSection.classList.remove("hidden");
  fetchLastEntry();
  timerInterval = setInterval(() => {
    timeLeft -= 1;
    updateTimerDisplay();
    if (timeLeft <= 0) {
      clearInterval(timerInterval);
      endTurn();
    }
  }, 1000);
}

function endTurn() {
  writingSection.classList.add("hidden");
  clearInterval(timerInterval);
}

function updateTimerDisplay() {
  if (timeLeft > 0) {
    timerDisplay.textContent = `Time left: ${timeLeft}s`;
  } else {
    timerDisplay.textContent = "";
  }
}

async function fetchLastEntry() {
  const res = await fetch(`${API_URL}/entries`);
  const data = await res.json();
  const lastEntry = data[data.length - 1];
  previousEntry.textContent = lastEntry ? lastEntry.text : "The story begins...";
}

async function fetchBook() {
  const res = await fetch(`${API_URL}/entries`);
  const data = await res.json();
  bookContent.innerHTML = data.map(e => `<p><b>${e.author}:</b> ${e.text}</p>`).join("");
}

submitBtn.addEventListener("click", async () => {
  const text = newEntry.value.trim();
  if (!text) return alert("Write something first!");

  const res = await fetch(`${API_URL}/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: nickname, text })
  });

  if (res.ok) {
    newEntry.value = "";
    fetchBook();
    endTurn();
  }
});

joinBtn.addEventListener("click", joinQueue);

setInterval(fetchBook, 10000);
setInterval(checkTurn, 3000);
fetchBook();
