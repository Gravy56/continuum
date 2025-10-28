from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import time
import threading
import json
import os
from flask import send_from_directory

@app.route('/')
@app.route('/<path:path>')
def serve_frontend(path=None):
    build_dir = os.path.join(os.path.dirname(__file__), 'build')
    if path and os.path.exists(os.path.join(build_dir, path)):
        return send_from_directory(build_dir, path)
    else:
        return send_from_directory(build_dir, 'index.html')

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

BOOK_FILE = "book_data.json"
TURN_FILE = "turn_data.json"

class Book:
    def __init__(self):
        self.entries = []

    def add_entry(self, author, content):
        self.entries.append({
            "author": author,
            "content": content,
            "timestamp": time.time()
        })
        self.save()

    def save(self):
        with open(BOOK_FILE, "w") as f:
            json.dump({"entries": self.entries}, f)

    def load(self):
        if os.path.exists(BOOK_FILE):
            with open(BOOK_FILE, "r") as f:
                self.entries = json.load(f).get("entries", [])
        else:
            self.entries = []

class TurnManager:
    def __init__(self, duration=120, cooldown=300):
        self.queue = []
        self.current_turn = None
        self.turn_start_time = 0
        self.duration = duration
        self.cooldown = cooldown
        self.last_turns = {}
        self.lock = threading.Lock()
        self.load()

    def load(self):
        if os.path.exists(TURN_FILE):
            with open(TURN_FILE, "r") as f:
                data = json.load(f)
                self.queue = data.get("queue", [])
                self.current_turn = data.get("current_turn")
                self.turn_start_time = data.get("turn_start_time", 0)
                self.last_turns = data.get("last_turns", {})
        else:
            self.save()

    def save(self):
        data = {
            "queue": self.queue,
            "current_turn": self.current_turn,
            "turn_start_time": self.turn_start_time,
            "last_turns": self.last_turns
        }
        with open(TURN_FILE, "w") as f:
            json.dump(data, f)

    def join_queue(self, username):
        with self.lock:
            now = time.time()
            if username in self.last_turns and now - self.last_turns[username] < self.cooldown:
                wait = int(self.cooldown - (now - self.last_turns[username]))
                return {"error": f"Cooldown active. Wait {wait}s."}

            if username in self.queue:
                return {"error": "Already in queue."}

            self.queue.append(username)
            self.save()
            return {"success": f"{username} joined the queue."}

    def next_turn(self):
        with self.lock:
            now = time.time()
            if self.current_turn and now - self.turn_start_time < self.duration:
                return self.current_turn

            if self.queue:
                self.current_turn = self.queue.pop(0)
                self.turn_start_time = now
                self.save()
                socketio.emit("turn_update", self.status())
                return self.current_turn
            else:
                self.current_turn = None
                self.save()
                socketio.emit("turn_update", self.status())
                return None

    def status(self):
        remaining = (
            max(0, self.duration - (time.time() - self.turn_start_time))
            if self.current_turn else 0
        )
        return {
            "current_turn": self.current_turn,
            "remaining_time": int(remaining),
            "queue": self.queue,
        }

book = Book()
book.load()
turns = TurnManager()

@app.route("/entries", methods=["GET"])
def get_entries():
    return jsonify(book.entries)

@app.route("/join", methods=["POST"])
def join_queue():
    username = request.json.get("username")
    result = turns.join_queue(username)
    socketio.emit("turn_update", turns.status())
    return jsonify(result)

@app.route("/add", methods=["POST"])
def add_entry():
    data = request.json
    username = data.get("username")
    content = data.get("content")

    if turns.current_turn != username:
        return jsonify({"error": "Not your turn."}), 403

    book.add_entry(username, content)
    turns.last_turns[username] = time.time()
    turns.save()
    turns.next_turn()

    socketio.emit("new_entry", book.entries[-1])
    return jsonify({"success": True})

@app.route("/current_turn", methods=["GET"])
def current_turn():
    turns.next_turn()
    return jsonify(turns.status())

def turn_watcher():
    """Background thread to auto-advance turns."""
    while True:
        time.sleep(1)
        turns.next_turn()

watcher_thread = threading.Thread(target=turn_watcher, daemon=True)
watcher_thread.start()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
