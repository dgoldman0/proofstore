import React, { useEffect, useRef, useState } from "react";
import { getElement, deleteElement, updateElement } from "../api.js";
import TagsEditor from "./TagsEditor.jsx";
import LinksPanel from "./LinksPanel.jsx";
import { marked } from "marked";
import DOMPurify from "dompurify";
import katex from "katex";
import renderMathInElement from "katex/contrib/auto-render";
import "katex/dist/katex.min.css";

// Optional: include only if it exists in your katex install
// import "katex/dist/contrib/auto-render.css";

function LatexText({ text }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    ref.current.textContent = text ?? "";
    renderMathInElement(ref.current, {
      delimiters: [
        { left: "\\[", right: "\\]", display: true },
        { left: "\\(", right: "\\)", display: false },
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
        ],
      throwOnError: false,
      strict: "warn",
    });
  }, [text]);

  return <div ref={ref} style={{ whiteSpace: "pre-wrap" }} />;
}

function renderBody(format, body) {
  const fmt = (format || "plain").toLowerCase();
  const text = body ?? "";

  if (fmt === "markdown") {
    const html = marked.parse(text);
    const safe = DOMPurify.sanitize(html);
    return <div dangerouslySetInnerHTML={{ __html: safe }} />;
  }

  if (fmt === "html") {
    const safe = DOMPurify.sanitize(text);
    return <div dangerouslySetInnerHTML={{ __html: safe }} />;
  }

  if (fmt === "latex") {
    // text + TeX delimiters
    return <LatexText text={text} />;
  }

  return <pre style={{ whiteSpace: "pre-wrap" }}>{text}</pre>;
}

const TYPES = [
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
];

const FORMATS = ["plain", "markdown", "html", "latex"];

export default function ElementDetail({ id, onUpdated }) {
  const [e, setE] = useState(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({
    type: "theorem",
    format: "plain",
    title: "",
    body: "",
  });

  useEffect(() => {
    let alive = true;
    setMsg("");
    setE(null);
    setEditing(false);

    getElement(id)
      .then((data) => {
        if (!alive) return;
        setE(data);
        setDraft({
          type: data.type || "theorem",
          format: data.format || "plain",
          title: data.title || "",
          body: data.body || "",
        });
      })
      .catch((err) => alive && setMsg(err?.message || "Failed to load element."));

    return () => {
      alive = false;
    };
  }, [id]);

  async function handleSave() {
    setMsg("");
    setBusy(true);
    try {
      const payload = {
        type: draft.type,
        format: draft.format,
        title: draft.title,
        body: draft.body,
      };
      await updateElement(id, payload);
      const fresh = await getElement(id);
      setE(fresh);
      setEditing(false);
      onUpdated?.();
      setMsg("Saved.");
    } catch (err) {
      setMsg(err?.message || "Save failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setMsg("");
    setBusy(true);
    try {
      await deleteElement(id);
      onUpdated?.();
    } catch (err) {
      setMsg(err?.message || "Delete failed.");
    } finally {
      setBusy(false);
    }
  }

  if (msg && !e) return <div style={{ color: "#b00" }}>{msg}</div>;
  if (!e) return null;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <h2 style={{ marginTop: 0, marginBottom: 6 }}>{e.title}</h2>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
            <code style={{ fontSize: 12, color: "#555" }}>{e.id}</code>
            <button
              onClick={() => navigator.clipboard.writeText(e.id)}
              style={{ fontSize: 12, padding: "4px 8px" }}
            >
              Copy ID
            </button>
          </div>
          <p style={{ marginTop: 0 }}>
            <b>{e.type}</b>{" "}
            {e.format && e.format !== "plain" ? (
              <span style={{ color: "#888" }}>[{e.format}]</span>
            ) : null}
          </p>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
          {!editing ? (
            <button onClick={() => setEditing(true)}>Edit</button>
          ) : (
            <>
              <button onClick={handleSave} disabled={busy}>
                {busy ? "Saving…" : "Save"}
              </button>
              <button
                onClick={() => {
                  setEditing(false);
                  setDraft({
                    type: e.type,
                    format: e.format || "plain",
                    title: e.title,
                    body: e.body,
                  });
                  setMsg("");
                }}
                disabled={busy}
              >
                Cancel
              </button>
            </>
          )}
          <button onClick={handleDelete} disabled={busy}>
            Delete
          </button>
        </div>
      </div>

      {msg ? <div style={{ color: msg === "Saved." ? "#060" : "#b00" }}>{msg}</div> : null}

      {!editing ? (
        <div style={{ marginTop: 12 }}>{renderBody(e.format, e.body)}</div>
      ) : (
        <div style={{ marginTop: 12 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <label>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Type</div>
              <select
                value={draft.type}
                onChange={(ev) => setDraft((d) => ({ ...d, type: ev.target.value }))}
                style={{ width: "100%", padding: 10 }}
              >
                {TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </label>

            <label>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Format</div>
              <select
                value={draft.format}
                onChange={(ev) => setDraft((d) => ({ ...d, format: ev.target.value }))}
                style={{ width: "100%", padding: 10 }}
              >
                {FORMATS.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <label style={{ display: "block", marginTop: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Title</div>
            <input
              value={draft.title}
              onChange={(ev) => setDraft((d) => ({ ...d, title: ev.target.value }))}
              style={{ width: "100%", padding: 10 }}
            />
          </label>

          <label style={{ display: "block", marginTop: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>Body</div>
            <textarea
              rows={14}
              value={draft.body}
              onChange={(ev) => setDraft((d) => ({ ...d, body: ev.target.value }))}
              style={{
                width: "100%",
                padding: 10,
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
              }}
            />
          </label>

          <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #ddd" }}>
            <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8, color: "#666" }}>
              Preview
            </div>
            {renderBody(draft.format, draft.body)}
          </div>
        </div>
      )}

      <hr />
      <TagsEditor element={e} onChange={setE} />
      <hr />
      <LinksPanel elementId={id} />
    </div>
  );
}
