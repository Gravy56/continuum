from flask import Flask, request, jsonify
from flask_cors import CORS
import time
import threading
import json
import os

app = Flask(__name__)
CORS(app)

BOOK_FILE = "book_data.json"

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
        data = {
            "entries": self.entries
        }
        with open(BOOK_FILE, "w") as f:
            json.dump(data, f)

    def load(self):
        if os.path.exists(BOOK_FILE):
            with open(BOOK_FILE, "r") as f:
                data = json.load(f)
                self.entries = data.get("entries", [])
        else:
            self.entries = []

class TurnManager:
    def __init__(self, duration=120):
        self.queue = []
        self.current_turn = None
        self.turn_start_time = 0
        self.duration = duration
        self.lock = threading.Lock()
        self.last_turns = {}
        self.cooldown = 300  # 5 min cooldown
        self.load_state()

    def load_state(self):
        if os.path.exists("turn_data.json"):
            with open("turn_data.json", "r") as f:
                data = json.load(f)
                self.queue = data.get("queue", [])
                self.current_turn = data.get("current_turn")
                self.turn_start_time = data.get("turn_start_time", 0)
                self.last_turns = data.get("last_turns", {})
        else:
            self.queue = []
            self.current_turn = None
            self.turn_start_time = 0
            self.last_turns = {}

    def save_state(self):
        data = {
            "queue": self.queue,
            "current_turn": self.current_turn,
            "turn_start_time": self.turn_start_time,
            "last_turns": self.last_turns
        }
        with open("turn_data.json", "w") as f:
            json.dump(data, f)

    def join_queue(self, username):
        with self.lock:
            now = time.time()
            if username in self.last_turns and now - self.last_turns[username] < self.cooldown:
                wait_time = int(self.cooldown - (now - self.last_turns[username]))
                return {"error": f"Cooldown active. Wait {wait_time}s."}

            if username in self.queue:
                return {"error": "You are already in the queue."}

            self.queue.append(username)
            self.save_state()
            return {"success": f"{username} joined the queue."}

    def next_turn(self):
        with self.lock:
            now = time.time()
            if self.current_turn and now - self.turn_start_time < self.duration:
                return self.current_turn  # Still ongoing

            if self.queue:
                self.current_turn = self.queue.pop(0)
                self.turn_start_time = now
                self.save_state()
                return self.current_turn
            else:
                self.current_turn = None
                self.save_state()
                return None

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
    return jsonify(result)

@app.route("/add", methods=["POST"])
def add_entry():
    data = request.json
    username = data.get("username")
    content = data.get("content")

    if turns.current_turn != username:
        return jsonify({"error": "It's not your turn."}), 403

    book.add_entry(username, content)
    turns.last_turns[username] = time.time()
    turns.save_state()
    turns.next_turn()
    return jsonify({"success": True})

@app.route("/current_turn", methods=["GET"])
def current_turn():
    turns.next_turn()
    remaining = max(0, turns.duration - (time.time() - turns.turn_start_time)) if turns.current_turn else 0
    return jsonify({
        "current_turn": turns.current_turn,
        "remaining_time": int(remaining),
        "queue": turns.queue
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
