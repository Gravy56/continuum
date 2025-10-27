from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import sqlite3

app = Flask(__name__)
CORS(app)

DB = "entries.db"
COOLDOWN = 5 * 60  # 5 minutes
TURN_DURATION = 2 * 60  # 2 minutes

queue = []  # list of usernames
current_turn = {"username": None, "start_time": None}


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            content TEXT,
            timestamp REAL
        )
    """)
    conn.commit()
    conn.close()


init_db()


@app.route("/join", methods=["POST"])
def join_queue():
    data = request.json
    username = data.get("username", "Anonymous")
    if username not in queue:
        queue.append(username)
    return jsonify({"queue": queue})


@app.route("/current_turn", methods=["GET"])
def get_current_turn():
    # Check if turn expired
    now = time.time()
    if current_turn["username"] and now - current_turn["start_time"] > TURN_DURATION:
        next_turn()
    return jsonify(current_turn)


def next_turn():
    global current_turn
    if queue:
        current_turn["username"] = queue.pop(0)
        current_turn["start_time"] = time.time()
        queue.append(current_turn["username"])
    else:
        current_turn = {"username": None, "start_time": None}


@app.route("/add", methods=["POST"])
def add_entry():
    global current_turn
    data = request.json
    username = data.get("username", "Anonymous")
    content = data.get("content", "").strip()

    if not content:
        return jsonify({"error": "Empty content"}), 400

    # Enforce queue
    if current_turn["username"] != username:
        return jsonify({"error": "It is not your turn yet."}), 403

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    # Check cooldown
    c.execute("SELECT timestamp FROM entries WHERE username=? ORDER BY id DESC LIMIT 1", (username,))
    row = c.fetchone()
    now = time.time()
    if row and now - row[0] < COOLDOWN:
        remaining = int((COOLDOWN - (now - row[0])) / 60)
        return jsonify({"error": f"Please wait {remaining} more minute(s) before posting again."}), 429

    c.execute("INSERT INTO entries (username, content, timestamp) VALUES (?, ?, ?)", (username, content, now))
    conn.commit()
    conn.close()

    next_turn()  # Move to next person in queue
    return jsonify({"success": True, "current_turn": current_turn})


@app.route("/entries", methods=["GET"])
def get_entries():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT username, content, timestamp FROM entries ORDER BY id ASC")
    data = [{"username": u, "content": c_, "timestamp": t} for (u, c_, t) in c.fetchall()]
    conn.close()
    return jsonify(data)


if __name__ == "__main__":
    next_turn()  # Initialize first turn
    app.run(host="0.0.0.0", port=5000)
