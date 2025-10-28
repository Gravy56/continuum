import React, { useState, useEffect } from "react";
import "./App.css";

export default function App() {
  const [entries, setEntries] = useState([]);
  const [author, setAuthor] = useState("");
  const [text, setText] = useState("");
  const [cooldownMsg, setCooldownMsg] = useState("");

  useEffect(() => {
    fetch("/api/entries")
      .then(res => res.json())
      .then(setEntries);
  }, []);

  const handleSubmit = async () => {
    const res = await fetch("/api/add", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ author, text })
    });
    const data = await res.json();

    if (data.error) setCooldownMsg(data.error);
    else {
      setEntries(data.entries);
      setText("");
      setCooldownMsg("");
    }
  };

  return (
    <div className="notebook">
      <h1 className="title">The Continuum</h1>
      <div className="page">
        <div className="entries">
          {entries.map((e, i) => (
            <div key={i} className="entry">
              <span className="author">{e.author}:</span>
              <span className="text">{e.text}</span>
            </div>
          ))}
        </div>
        <div className="input-section">
          <input
            type="text"
            placeholder="Your name"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
          />
          <textarea
            placeholder="Continue the story..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button onClick={handleSubmit}>Submit</button>
          {cooldownMsg && <p className="cooldown">{cooldownMsg}</p>}
        </div>
      </div>
    </div>
  );
}
