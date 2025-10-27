const API_URL = "https://continuum-backend.onrender.com";
let nickname = prompt("Enter your nickname:");
let timerInterval;
let timeLeft = 120;

// Join queue on load
fetch(`${API_URL}/join`, {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({username: nickname})
});

// Update story & check turn
async function update() {
  const res = await fetch(`${API_URL}/entries`);
  const entries = await res.json();

  const fullBook = document.getElementById("full-book");
  fullBook.innerHTML = "";
  entries.forEach(e => {
      fullBook.innerHTML += `${e.username}: ${e.content}\n\n`;
  });

  const lastEntry = entries[entries.length - 1];
  document.getElementById("last-entry").innerText = lastEntry ? `${lastEntry.username}: ${lastEntry.content}` : "";

  // Check whose turn
  const turnRes = await fetch(`${API_URL}/current_turn`);
  const turnData = await turnRes.json();

  const submitBtn = document.getElementById("submit-btn");
  const entryInput = document.getElementById("entry-input");

  if(turnData.username === nickname) {
      entryInput.disabled = false;
      submitBtn.disabled = false;
      // Calculate remaining time
      const elapsed = Math.floor(Date.now()/1000 - turnData.start_time);
      timeLeft = 120 - elapsed;
      startTimer();
  } else {
      entryInput.disabled = true;
      submitBtn.disabled = true;
      document.getElementById("timer").innerText = `Waiting for ${turnData.username}...`;
      clearInterval(timerInterval);
  }
}

async function submitEntry() {
    clearInterval(timerInterval);
    const content = document.getElementById("entry-input").value.trim();
    if(!content) return;

    const res = await fetch(`${API_URL}/add`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username: nickname, content})
    });

    const data = await res.json();
    if(data.error) alert(data.error);

    document.getElementById("entry-input").value = "";
    update();
}

// Timer countdown
function startTimer() {
    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
        timeLeft--;
        let minutes = Math.floor(timeLeft / 60);
        let seconds = timeLeft % 60;
        document.getElementById("timer").innerText = `Time left: ${minutes}:${seconds < 10 ? "0":""}${seconds}`;
        if(timeLeft <= 0) {
            clearInterval(timerInterval);
            alert("Time's up! Your turn ended.");
            update();  // refresh turn
        }
    }, 1000);
}

// Update every 5s
setInterval(update, 5000);
update();
