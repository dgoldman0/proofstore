import React, { useState } from "react";
import { createElement } from "../api.js";

export default function ElementForm({ onCreated }) {
  const [type, setType] = useState("theorem");
  const [format, setFormat] = useState("plain");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function handleCreate() {
    setMsg("");
    setBusy(true);
    try {
      const payload = { type, format, title, body };
      await createElement(payload);

      setTitle("");
      setBody("");
      onCreated?.();
      setMsg("Created.");
    } catch (e) {
      setMsg(e?.message || "Create failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <h2 style={styles.h2}>New element</h2>
      </div>

      <div style={styles.grid2}>
        <label style={styles.label}>
          <div style={styles.labelText}>Type</div>
          <select
            value={type}
            onChange={(e) => setType(e.target.value)}
            style={styles.select}
          >
            {[
              "definition",
              "axiom",
              "postulate",
              "lemma",
              "proposition",
              "theorem",
              "corollary",
              "proof",
              "example",
              "counterexample",
              "remark",
            ].map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>

        <label style={styles.label}>
          <div style={styles.labelText}>Format</div>
          <select
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            style={styles.select}
          >
            {["plain", "markdown", "html", "latex"].map((f) => (
              <option key={f} value={f}>
                {f}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label style={styles.label}>
        <div style={styles.labelText}>Title</div>
        <input
          placeholder="e.g. Fermat's Little Theorem"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={styles.input}
        />
      </label>

      <label style={styles.label}>
        <div style={styles.labelText}>Body</div>
        <textarea
          rows={12}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder={
            format === "markdown"
              ? "Write Markdown..."
              : format === "latex"
              ? "Write LaTeX/KaTeX..."
              : format === "html"
              ? "Write HTML (will be sanitized)..."
              : "Write plain text..."
          }
          style={styles.textarea}
        />
      </label>

      <div style={styles.footer}>
        <button
          onClick={handleCreate}
          disabled={busy || !title.trim() || !body.trim()}
          style={{
            ...styles.button,
            opacity: busy || !title.trim() || !body.trim() ? 0.6 : 1,
            cursor: busy || !title.trim() || !body.trim() ? "not-allowed" : "pointer",
          }}
        >
          {busy ? "Creating…" : "Create"}
        </button>

        <div style={styles.msg} aria-live="polite">
          {msg}
        </div>
      </div>
    </div>
  );
}

const styles = {
  card: {
    maxWidth: 900,
    margin: "0 auto",
    padding: 35,
    border: "1px solid #ddd",
    borderRadius: 12,
    background: "#fff",
  },
  header: {
    display: "flex",
    alignItems: "baseline",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  h2: { margin: 0, fontSize: 18, fontWeight: 700 },
  grid2: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 12,
    marginBottom: 12,
  },
  label: { display: "block", marginBottom: 12 },
  labelText: { fontSize: 12, fontWeight: 600, marginBottom: 6, color: "#333" },
  input: {
    width: "100%",
    padding: "10px 12px",
    border: "1px solid #ccc",
    borderRadius: 10,
    fontSize: 14,
    outline: "none",
  },
  select: {
    width: "100%",
    padding: "10px 12px",
    border: "1px solid #ccc",
    borderRadius: 10,
    fontSize: 14,
    outline: "none",
    background: "#fff",
  },
  textarea: {
    width: "100%",
    padding: "10px 12px",
    border: "1px solid #ccc",
    borderRadius: 10,
    fontSize: 14,
    outline: "none",
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    lineHeight: 1.4,
    resize: "vertical",
  },
  footer: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    marginTop: 6,
  },
  button: {
    padding: "10px 14px",
    border: "1px solid #222",
    borderRadius: 10,
    background: "#111",
    color: "#fff",
    fontWeight: 700,
    fontSize: 14,
  },
  msg: { fontSize: 13, color: "#444" },
};
