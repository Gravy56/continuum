# app.py
from flask import Flask, g, render_template, request, jsonify, session
import sqlite3
from datetime import datetime, timezone, timedelta
import os

DATABASE = 'project-continuum/continuum.db'
TURN_SECONDS = 120  # 2 minutes per turn
COOLDOWN_SECONDS = 300  # 5 minutes cooldown

app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = sqlite3.connect(DATABASE, check_same_thread=False)
        db.row_factory = sqlite3.Row
        g._database = db
    return db

@app.teardown_appcontext
def close_connection(exc):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def iso_from_dt(dt):
    return dt.isoformat()

def parse_iso(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def get_state(key):
    db = get_db()
    cur = db.execute("SELECT v FROM state WHERE k = ?", (key,))
    r = cur.fetchone()
    return None if r is None else r['v']

def set_state(key, val):
    db = get_db()
    db.execute("INSERT OR REPLACE INTO state (k, v) VALUES (?, ?)", (key, str(val)))
    db.commit()

def set_user_cooldown(user_id, seconds=COOLDOWN_SECONDS):
    db = get_db()
    until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    db.execute("UPDATE users SET cooldown_until = ? WHERE id = ?", (until.isoformat(), user_id))
    db.commit()

def get_user_cooldown(user_id):
    db = get_db()
    cur = db.execute("SELECT cooldown_until FROM users WHERE id = ?", (user_id,))
    r = cur.fetchone()
    if not r or not r["cooldown_until"]:
        return None
    return parse_iso(r["cooldown_until"])

def advance_turn_if_needed():
    """
    If current turn is active and not expired -> leave it.
    If expired -> apply cooldown to previous user and promote next in queue.
    If no active user -> promote next in queue.
    This function is called on API endpoints to keep state fresh.
    """
    db = get_db()
    current = get_state("current_user_id")
    turn_start = get_state("turn_start")

    # if there is a current user and start time, check expiry
    if current and current != "NULL" and turn_start and turn_start != "NULL":
        try:
            start_dt = parse_iso(turn_start)
            if start_dt:
                elapsed = (datetime.now(timezone.utc) - start_dt).total_seconds()
                if elapsed < TURN_SECONDS:
                    return  # still active
                else:
                    # expired -> give cooldown to the previous user
                    try:
                        prev_uid = int(current)
                        set_user_cooldown(prev_uid, COOLDOWN_SECONDS)
                    except Exception:
                        pass
        except Exception:
            pass

    # either no active writer or expired -> assign next queue member
    cur = db.execute("SELECT q.id as qid, q.user_id, u.nickname FROM queue q JOIN users u ON q.user_id = u.id ORDER BY q.id LIMIT 1")
    nextr = cur.fetchone()
    if nextr:
        set_state("current_user_id", str(nextr['user_id']))
        set_state("turn_start", now_iso())
        set_state("current_draft", "")  # reset draft
        db.execute("DELETE FROM queue WHERE id = ?", (nextr['qid'],))
        db.commit()
    else:
        set_state("current_user_id", "NULL")
        set_state("turn_start", "NULL")
        set_state("current_draft", "")

@app.route("/")
def index():
    advance_turn_if_needed()
    return render_template("index.html")

@app.route("/api/register", methods=["POST"])
def register():
    nickname = request.json.get("nickname", "").strip()
    if not nickname:
        return jsonify({"ok": False, "error": "Nickname required"}), 400
    db = get_db()
    cur = db.execute("INSERT INTO users (nickname, cooldown_until) VALUES (?, ?)", (nickname, None))
    db.commit()
    uid = cur.lastrowid
    session['user_id'] = uid
    session['nickname'] = nickname
    return jsonify({"ok": True, "user_id": uid, "nickname": nickname})

@app.route("/api/join_queue", methods=["POST"])
def join_queue():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"ok": False, "error": "Not registered"}), 403
    # check cooldown
    cooldown_until = get_user_cooldown(uid)
    if cooldown_until and cooldown_until > datetime.now(timezone.utc):
        remaining = int((cooldown_until - datetime.now(timezone.utc)).total_seconds())
        return jsonify({"ok": False, "error": "Cooldown active", "cooldown_seconds": remaining}), 400
    db = get_db()
    cur = db.execute("SELECT 1 FROM queue WHERE user_id = ?", (uid,))
    if cur.fetchone():
        return jsonify({"ok": False, "error": "Already in queue"}), 400
    db.execute("INSERT INTO queue (user_id, joined_at) VALUES (?, ?)", (uid, now_iso()))
    db.commit()
    advance_turn_if_needed()
    return jsonify({"ok": True})

@app.route("/api/leave_queue", methods=["POST"])
def leave_queue():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"ok": False, "error": "Not registered"}), 403
    db = get_db()
    db.execute("DELETE FROM queue WHERE user_id = ?", (uid,))
    db.commit()
    return jsonify({"ok": True})

@app.route("/api/status")
def status():
    advance_turn_if_needed()
    current = get_state("current_user_id")
    turn_start = get_state("turn_start")
    time_left = 0
    if current and current != "NULL" and turn_start and turn_start != "NULL":
        start_dt = parse_iso(turn_start)
        if start_dt:
            elapsed = (datetime.now(timezone.utc) - start_dt).total_seconds()
            time_left = max(0, int(TURN_SECONDS - elapsed))
    else:
        current = None
        time_left = 0

    db = get_db()
    cur = db.execute("SELECT q.user_id, u.nickname FROM queue q JOIN users u ON q.user_id = u.id ORDER BY q.id LIMIT 50")
    qlist = [{"user_id": r["user_id"], "nickname": r["nickname"]} for r in cur.fetchall()]

    cur_writer = None
    if current and current != "NULL":
        cur2 = db.execute("SELECT nickname FROM users WHERE id = ?", (current,))
        r = cur2.fetchone()
        if r:
            cur_writer = r["nickname"]

    draft = get_state("current_draft") or ""
    # include my cooldown if session
    my_cooldown = None
    uid = session.get('user_id')
    if uid:
        cu = get_user_cooldown(uid)
        if cu and cu > datetime.now(timezone.utc):
            my_cooldown = int((cu - datetime.now(timezone.utc)).total_seconds())

    return jsonify({"ok": True, "current_user_id": current, "current_nickname": cur_writer, "time_left": time_left, "queue": qlist, "current_draft": draft, "my_cooldown_seconds": my_cooldown})

@app.route("/api/update_draft", methods=["POST"])
def update_draft():
    uid = session.get('user_id')
    if not uid:
        return jsonify({"ok": False, "error": "Not registered"}), 403
    current = get_state("current_user_id")
    if not current or current == "NULL" or str(uid) != str(current):
        return jsonify({"ok": False, "error": "Not your turn"}), 403
    text = request.json.get("text", "")
    if len(text) > 5000:
        return jsonify({"ok": False, "error": "Draft too long"}), 400
    set_state("current_draft", text)
    return jsonify({"ok": True})

@app.route("/api/get_draft")
def get_draft():
    draft = get_state("current_draft") or ""
    return jsonify({"ok": True, "draft": draft})

@app.route("/api/submit", methods=["POST"])
def submit():
    uid = session.get('user_id')
    nickname = session.get('nickname')
    if not uid:
        return jsonify({"ok": False, "error": "Not registered"}), 403
    current = get_state("current_user_id")
    turn_start = get_state("turn_start")
    if not current or current == "NULL":
        return jsonify({"ok": False, "error": "No active turn"}), 400
    if str(uid) != str(current):
        return jsonify({"ok": False, "error": "Not your turn"}), 403
    if not turn_start or turn_start == "NULL":
        return jsonify({"ok": False, "error": "Turn timing missing"}), 500
    start_dt = parse_iso(turn_start)
    elapsed = (datetime.now(timezone.utc) - start_dt).total_seconds()
    if elapsed > TURN_SECONDS:
        # time expired -> set cooldown for previous and advance
        set_user_cooldown(uid, COOLDOWN_SECONDS)
        advance_turn_if_needed()
        return jsonify({"ok": False, "error": "Time expired"}), 400
    text = request.json.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Empty text"}), 400
    db = get_db()
    tn = int(get_state("turn_number") or 0) + 1
    set_state("turn_number", tn)
    db.execute("INSERT INTO entries (user_id, nickname, text, timestamp, turn_number) VALUES (?, ?, ?, ?, ?)",
               (uid, nickname, text, now_iso(), tn))
    db.commit()
    # set cooldown for the submitter
    set_user_cooldown(uid, COOLDOWN_SECONDS)
    # clear draft and advance
    set_state("current_draft", "")
    advance_turn_if_needed()
    return jsonify({"ok": True})

@app.route("/api/feed")
def feed():
    # return entries newest-first for quick client refresh (but we also provide /api/book)
    db = get_db()
    cur = db.execute("SELECT id, nickname, text, timestamp, turn_number FROM entries ORDER BY id DESC LIMIT 200")
    rows = cur.fetchall()
    entries = [{"id": r["id"], "nickname": r["nickname"], "text": r["text"], "timestamp": r["timestamp"], "turn_number": r["turn_number"]} for r in rows]
    return jsonify({"ok": True, "entries": entries})

@app.route("/api/book")
def book():
    # full story oldest -> newest for reading like a book
    db = get_db()
    cur = db.execute("SELECT id, nickname, text, timestamp, turn_number FROM entries ORDER BY id ASC")
    rows = cur.fetchall()
    entries = [{"id": r["id"], "nickname": r["nickname"], "text": r["text"], "timestamp": r["timestamp"], "turn_number": r["turn_number"]} for r in rows]
    return jsonify({"ok": True, "entries": entries})

@app.route("/api/myinfo")
def myinfo():
    return jsonify({"user_id": session.get('user_id'), "nickname": session.get('nickname')})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
