let username = "";
const API = "";

async function getEntries() {
  const res = await fetch(API + "/entries");
  const data = await res.json();
  const entriesDiv = document.getElementById("entries");
  entriesDiv.innerHTML = data.map(e => 
    `<p><b>${e.user}:</b> ${e.text}</p>`
  ).join("");
}

async function getTurnInfo() {
  const res = await fetch(API + "/current_turn");
  const data = await res.json();
  const turnDiv = document.getElementById("turnInfo");
  turnDiv.textContent = data.active_user
    ? `✍️ Current turn: ${data.active_user} (${Math.ceil(data.time_left)}s left)`
    : "🕒 Waiting for next writer...";
}

document.getElementById("joinQueue").onclick = async () => {
  username = document.getElementById("username").value.trim();
  if (!username) return alert("Enter your name first!");
  const res = await fetch(API + "/join", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({user: username})
  });
  const data = await res.json();
  alert(data.message || data.error);
};

document.getElementById("submit").onclick = async () => {
  const text = document.getElementById("entry").value.trim();
  if (!text) return alert("Write something first!");
  const res = await fetch(API + "/add", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({user: username, text})
  });
  const data = await res.json();
  if (data.error) alert(data.error);
  else {
    document.getElementById("entry").value = "";
    getEntries();
  }
};

setInterval(() => {
  getEntries();
  getTurnInfo();
}, 3000);

getEntries();
getTurnInfo();
