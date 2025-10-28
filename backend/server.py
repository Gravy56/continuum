from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json, os, time

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

BOOK_FILE = "book_data.json"
TURN_FILE = "turn_data.json"

TURN_TIME = 120  # seconds
COOLDOWN = 300  # 5 min

# --- Data Management ---
def load_json(file, default):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump(default, f)
        return default
    try:
        with open(file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# --- Routes ---
@app.route("/entries")
def get_entries():
    data = load_json(BOOK_FILE, {"entries": []})
    return jsonify(data["entries"])

@app.route("/add", methods=["POST"])
def add_entry():
    body = request.json
    name = body.get("name")
    text = body.get("text")
    if not name or not text:
        return jsonify({"error": "Missing data"}), 400

    entries = load_json(BOOK_FILE, {"entries": []})
    entries["entries"].append({
        "author": name,
        "text": text,
        "time": time.time()
    })
    save_json(BOOK_FILE, entries)

    # Broadcast new entry live
    socketio.emit("new_entry", entries["entries"][-1])
    return jsonify({"status": "ok"})

@app.route("/join", methods=["POST"])
def join_queue():
    name = request.json.get("name")
    data = load_json(TURN_FILE, {
        "queue": [], "current_turn": None, "turn_start_time": 0, "last_turns": {}
    })

    now = time.time()
    last = data["last_turns"].get(name, 0)
    if now - last < COOLDOWN:
        return jsonify({"message": f"Wait {int(COOLDOWN - (now - last))}s cooldown."})

    if name not in data["queue"]:
        data["queue"].append(name)
        save_json(TURN_FILE, data)
        socketio.emit("queue_update", data["queue"])
        return jsonify({"message": f"{name} joined the queue!"})
    return jsonify({"message": "Already in queue."})

@app.route("/current_turn")
def current_turn():
    data = load_json(TURN_FILE, {
        "queue": [], "current_turn": None, "turn_start_time": 0, "last_turns": {}
    })
    now = time.time()

    # Check for expired turn
    if data["current_turn"]:
        if now - data["turn_start_time"] > TURN_TIME:
            end_turn(data)
    else:
        if data["queue"]:
            start_turn(data)

    remaining = 0
    if data["current_turn"]:
        remaining = max(0, TURN_TIME - int(now - data["turn_start_time"]))

    save_json(TURN_FILE, data)
    return jsonify({"current": data["current_turn"], "time_left": remaining})

# --- Turn Logic ---
def start_turn(data):
    next_user = data["queue"].pop(0)
    data["current_turn"] = next_user
    data["turn_start_time"] = time.time()
    save_json(TURN_FILE, data)
    socketio.emit("turn_start", {"user": next_user, "time": TURN_TIME})

def end_turn(data):
    if not data["current_turn"]:
        return
    user = data["current_turn"]
    data["last_turns"][user] = time.time()
    data["current_turn"] = None
    data["turn_start_time"] = 0
    save_json(TURN_FILE, data)
    socketio.emit("turn_end", {"user": user})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=10000)
