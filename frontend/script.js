const backendURL = "https://your-render-url.onrender.com"; // replace with your actual Render backend URL
const socket = io(backendURL);
let username = prompt("Enter your nickname:");
let entryBox = document.getElementById("entryBox");
let submitBtn = document.getElementById("submitBtn");
let entriesDiv = document.getElementById("entries");
let turnDiv = document.getElementById("turn-status");

// Load entries
fetch(`${backendURL}/entries`)
  .then(res => res.json())
  .then(entries => {
    entries.forEach(appendEntry);
  });

socket.on("new_entry", (entry) => {
  appendEntry(entry);
});

socket.on("turn_update", (data) => {
  updateTurnDisplay(data);
});

submitBtn.onclick = async () => {
  const text = entryBox.value.trim();
  if (!text) return alert("Write something first!");

  const res = await fetch(`${backendURL}/add`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, content: text }),
  });
  const data = await res.json();
  if (data.error) alert(data.error);
  else entryBox.value = "";
};

function appendEntry(entry) {
  const div = document.createElement("div");
  div.className = "entry";
  const date = new Date(entry.timestamp * 1000).toLocaleString();
  div.innerHTML = `<strong>${entry.author}</strong> (${date})<br>${entry.content}<hr>`;
  entriesDiv.appendChild(div);
  entriesDiv.scrollTop = entriesDiv.scrollHeight;
}

function updateTurnDisplay(data) {
  turnDiv.innerHTML = `
    <p><b>Current turn:</b> ${data.current_turn || "None"}</p>
    <p><b>Queue:</b> ${data.queue.join(", ") || "Empty"}</p>
    <p><b>Time remaining:</b> ${data.remaining_time}s</p>
  `;
}
