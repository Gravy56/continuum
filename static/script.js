// static/script.js - frontend updated for cooldown and full-book view
let my = { user_id: null, nickname: null };
const POLL_MS = 1000; // status poll
const DRAFT_SAVE_MS = 2000; // autosave draft when writing
const PAD = s => String(s).padStart(2,'0');

let statusTimer = null;
let draftTimer = null;
let lastDraftSent = "";

function $(s){ return document.querySelector(s); }
function el(tag, cls=''){ const e=document.createElement(tag); if(cls) e.className=cls; return e; }

async function api(path, opts={}) {
  const res = await fetch('/api/' + path, opts);
  return res.json();
}

async function init() {
  const info = await api('myinfo');
  if (info.user_id) {
    my = info;
    showControls();
  } else {
    document.getElementById('register').classList.remove('hidden');
  }
  attachUI();
  startPolling();
  refreshFeed();
  refreshBook();
}

function attachUI() {
  $('#btn-register').onclick = async () => {
    const nick = $('#nick').value.trim();
    if (!nick) { $('#reg-msg').textContent = 'Pick a nickname.'; return; }
    const res = await api('register', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({nickname: nick}) });
    if (res.ok) {
      my = { user_id: res.user_id, nickname: res.nickname };
      showControls();
    } else {
      $('#reg-msg').textContent = res.error || 'Could not register.';
    }
  };

  $('#btn-join').onclick = async () => {
    const res = await api('join_queue', { method: 'POST' });
    if (!res.ok) {
      if (res.error === "Cooldown active") {
        const s = res.cooldown_seconds || 0;
        alert(`You are on cooldown. Wait ${Math.ceil(s/60)}m ${s%60}s`);
      } else {
        alert(res.error || 'Could not join queue.');
      }
    }
  };

  $('#btn-leave').onclick = async () => {
    await api('leave_queue', { method: 'POST' });
  };

  $('#btn-submit').onclick = async () => {
    const text = $('#writer-box').value.trim();
    if (!text) return alert('Write something first.');
    $('#btn-submit').disabled = true;
    const res = await api('submit', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text}) });
    if (!res.ok) {
      alert(res.error || 'Submit failed.');
    } else {
      $('#writer-box').value = '';
      refreshFeed();
      refreshBook();
    }
    $('#btn-submit').disabled = false;
  };

  $('#writer-box').addEventListener('input', () => {
    if ($('#writer-box').disabled) return;
    scheduleDraftSave();
  });
}

function scheduleDraftSave(){
  if (draftTimer) clearTimeout(draftTimer);
  draftTimer = setTimeout(sendDraft, DRAFT_SAVE_MS);
}

async function sendDraft(){
  const text = $('#writer-box').value;
  if (text === lastDraftSent) return;
  lastDraftSent = text;
  await api('update_draft', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({text}) });
}

function showControls(){
  document.getElementById('register').classList.add('hidden');
  document.getElementById('controls').classList.remove('hidden');
  $('#reg-msg').textContent = `You are logged as "${my.nickname}"`;
}

async function pollStatus(){
  const s = await api('status');
  if (!s.ok) return;
  // queue
  const qlist = s.queue || [];
  const qEl = $('#queue-list');
  qEl.innerHTML = '';
  qlist.forEach(q => {
    const li = el('li');
    li.textContent = q.nickname;
    qEl.appendChild(li);
  });

  // show cooldown note if any
  const cd = s.my_cooldown_seconds;
  const cdNote = $('#cooldown-note');
  if (cd && cd > 0) {
    const mm = Math.floor(cd/60);
    const ss = cd % 60;
    cdNote.textContent = `You are on cooldown: ${mm}m ${ss}s`;
    $('#btn-join').disabled = true;
  } else {
    cdNote.textContent = '';
    $('#btn-join').disabled = false;
  }

  // current writer
  if (s.current_nickname) {
    $('#current-info').textContent = `Writing: ${s.current_nickname}`;
  } else {
    $('#current-info').textContent = `No active writer`;
  }

  // timer
  const tleft = s.time_left || 0;
  $('#timer').textContent = `${PAD(Math.floor(tleft/60))}:${PAD(tleft%60)}`;

  // enable writer box if it's your turn
  const myinfo = await api('myinfo');
  const meId = myinfo.user_id;
  if (s.current_user_id && String(s.current_user_id) === String(meId)) {
    $('#writer-box').disabled = false;
    $('#btn-submit').disabled = false;
    $('#writer-status').textContent = 'Your turn — write!';
    // try to load existing draft (so you can resume if page reload)
    const d = await api('get_draft');
    if (d.ok) {
      if ($('#writer-box').value.trim().length === 0) {
        $('#writer-box').value = d.draft || '';
      }
    }
    // start autosave schedule
    scheduleDraftSave();
  } else {
    $('#writer-box').disabled = true;
    $('#btn-submit').disabled = true;
    $('#writer-status').textContent = 'Not your turn';
  }

  // show live draft for everyone
  const draft = s.current_draft || "";
  $('#live-draft').textContent = draft ? draft : "—";

  // update last-entry shown above writer (fetch full book but only show last entry)
  await refreshLastEntry();
}

async function refreshFeed(){
}

async function refreshBook(){
  const b = await api('book');
  if (!b.ok) return;
  const container = $('#full-book');
  container.innerHTML = '';
  b.entries.forEach(ent => {
    const div = el('div','feed-item');
    const meta = el('div','meta'); meta.textContent = `#${ent.turn_number} • ${ent.nickname || 'anon'} • ${new Date(ent.timestamp).toLocaleString()}`;
    const txt = el('div','text'); txt.textContent = ent.text;
    div.appendChild(meta); div.appendChild(txt);
    container.appendChild(div);
  });
}

async function refreshLastEntry(){
  const b = await api('book');
  if (!b.ok) return;
  if (b.entries && b.entries.length > 0) {
    const last = b.entries[b.entries.length - 1]; // oldest->newest, so last is newest entry
    $('#last-entry').textContent = last.text;
  } else {
    $('#last-entry').textContent = "No entries yet — be first to write.";
  }
}

function startPolling(){
  if (statusTimer) clearInterval(statusTimer);
  statusTimer = setInterval(()=>{ pollStatus(); }, POLL_MS);
  // feed & book refresh less often
  setInterval(refreshFeed, 3000);
  setInterval(refreshBook, 5000);
  // initial
  pollStatus();
  refreshFeed();
  refreshBook();
}

window.addEventListener('load', init);
