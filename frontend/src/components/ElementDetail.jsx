import React, { useEffect, useRef, useState } from "react";
import { getElement, deleteElement, updateElement } from "../api.js";
import TagsEditor from "./TagsEditor.jsx";
import LinksPanel from "./LinksPanel.jsx";
import { marked } from "marked";
import DOMPurify from "dompurify";
import renderMathInElement from "katex/contrib/auto-render";
import "katex/dist/katex.min.css";

/* ------------------------------------------------------------
   Shared button style
------------------------------------------------------------ */

const buttonStyle = {
  padding: "6px 12px",
  fontSize: 13,
  borderRadius: 4,
  border: "1px solid #ccc",
  background: "#f8f8f8",
  cursor: "pointer",
  lineHeight: 1.2,
};

const dangerButtonStyle = {
  ...buttonStyle,
  borderColor: "#c88",
  background: "#fff5f5",
};

/* ------------------------------------------------------------
   Markdown + LaTeX renderer
------------------------------------------------------------ */

function MarkdownLatex({ text }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current) return;

    const src = text ?? "";

    // Extract math *before* markdown can split it with <p>/<br>.
    const math = [];
    const placeholder = (i) => `@@MATH_${i}@@`;

    // Do display first, then inline.
    const patterns = [
      /\$\$[\s\S]*?\$\$/g,      // $$...$$
      /\\\[[\s\S]*?\\\]/g,      // \[...\]
      /\\\([\s\S]*?\\\)/g,      // \(...\)
      /\$[^$\n]+\$/g,           // $...$ (single-line inline; avoids greedy multiline weirdness)
    ];

    let protectedText = src;
    for (const re of patterns) {
      protectedText = protectedText.replace(re, (m) => {
        const i = math.length;
        math.push(m);
        return placeholder(i);
      });
    }

    // Markdown -> HTML -> sanitize
    const html = marked.parse(protectedText);
    let safe = DOMPurify.sanitize(html);

    // Restore math chunks
    safe = safe.replace(/@@MATH_(\d+)@@/g, (_, n) => math[Number(n)] ?? "");

    // Inject then KaTeX autorender
    ref.current.innerHTML = safe;

    renderMathInElement(ref.current, {
      delimiters: [
        { left: "\\[", right: "\\]", display: true },
        { left: "$$", right: "$$", display: true },
        { left: "\\(", right: "\\)", display: false },
        { left: "$", right: "$", display: false },
      ],
      throwOnError: false,
      strict: "warn",
    });
  }, [text]);

  return <div ref={ref} />;
}

/* ------------------------------------------------------------
   Body renderer
------------------------------------------------------------ */

function renderBody(format, body) {
  const fmt = (format || "plain").toLowerCase();
  const text = body ?? "";

  if (fmt === "markdown" || fmt === "latex") {
    return <MarkdownLatex text={text} />;
  }

  if (fmt === "html") {
    return <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(text) }} />;
  }

  return <pre style={{ whiteSpace: "pre-wrap" }}>{text}</pre>;
}

/* ------------------------------------------------------------
   Constants
------------------------------------------------------------ */

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

/* ------------------------------------------------------------
   Main component
------------------------------------------------------------ */

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
      await updateElement(id, draft);
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
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 12,
          alignItems: "flex-start",
        }}
      >
        <div>
          <h2 style={{ marginTop: 0, marginBottom: 6 }}>{e.title}</h2>

          <div
            style={{
              display: "flex",
              gap: 8,
              alignItems: "center",
              marginBottom: 8,
            }}
          >
            <code style={{ fontSize: 12, color: "#555" }}>{e.id}</code>
            <button
              style={buttonStyle}
              onClick={() => navigator.clipboard.writeText(e.id)}
            >
              Copy ID
            </button>
          </div>

          <p style={{ marginTop: 0 }}>
            <b>{e.type}</b>{" "}
            {e.format !== "plain" && (
              <span style={{ color: "#888" }}>[{e.format}]</span>
            )}
          </p>
        </div>

        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "flex-start",
          }}
        >
          {!editing ? (
            <button style={buttonStyle} onClick={() => setEditing(true)}>
              Edit
            </button>
          ) : (
            <>
              <button
                style={buttonStyle}
                onClick={handleSave}
                disabled={busy}
              >
                {busy ? "Saving…" : "Save"}
              </button>
              <button
                style={buttonStyle}
                disabled={busy}
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
              >
                Cancel
              </button>
            </>
          )}
          <button
            style={dangerButtonStyle}
            onClick={handleDelete}
            disabled={busy}
          >
            Delete
          </button>
        </div>
      </div>

      {msg && (
        <div style={{ color: msg === "Saved." ? "#060" : "#b00", marginTop: 8 }}>
          {msg}
        </div>
      )}

      {!editing ? (
        <div style={{ marginTop: 12 }}>{renderBody(e.format, e.body)}</div>
      ) : (
        <div style={{ marginTop: 12 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <label>
              <div style={{ fontSize: 12, fontWeight: 600 }}>Type</div>
              <select
                value={draft.type}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, type: e.target.value }))
                }
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
              <div style={{ fontSize: 12, fontWeight: 600 }}>Format</div>
              <select
                value={draft.format}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, format: e.target.value }))
                }
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
            <div style={{ fontSize: 12, fontWeight: 600 }}>Title</div>
            <input
              value={draft.title}
              onChange={(e) =>
                setDraft((d) => ({ ...d, title: e.target.value }))
              }
              style={{ width: "100%", padding: 10 }}
            />
          </label>

          <label style={{ display: "block", marginTop: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 600 }}>Body</div>
            <textarea
              rows={14}
              value={draft.body}
              onChange={(e) =>
                setDraft((d) => ({ ...d, body: e.target.value }))
              }
              style={{
                width: "100%",
                padding: 10,
                fontFamily:
                  "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
              }}
            />
          </label>

          <div style={{ marginTop: 12, borderTop: "1px solid #ddd", paddingTop: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#666" }}>
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
