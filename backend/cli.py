from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path
import html
from datetime import datetime

from core import (
    ELEMENT_TYPES,
    FORMATS,
    LINK_RELATIONS,
    connect,
    init_db,
    # element CRUD
    create_element,
    get_element,
    list_elements,
    update_element,
    delete_element,
    # tags
    list_tags,
    add_tags,
    remove_tags,
    clear_tags,
    set_tags,
    list_elements_by_tag,
    # links
    create_link,
    get_link,
    list_links,
    update_link,
    delete_link,
    list_links_for_element,
)


def _read_body(body: str | None, file: str | None) -> str:
    """Read the body text from --body, --file or stdin."""
    if file:
        return Path(file).expanduser().read_text(encoding="utf-8")
    if body is not None:
        return body
    data = sys.stdin.read()
    return data.strip("\n")


def _split_csv_or_repeat(values: list[str] | None) -> list[str]:
    """
    Split comma-separated strings in command-line inputs. If a value contains
    commas, it will be split; otherwise values are appended directly. Empty
    parts are discarded.
    """
    if not values:
        return []
    out: list[str] = []
    for v in values:
        parts = [p.strip() for p in v.split(",")] if "," in v else [v.strip()]
        out.extend([p for p in parts if p])
    return out


# -----------------------------------------------------------------------------
# CLI commands for core actions
# -----------------------------------------------------------------------------


def cmd_init(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    print(str(Path(args.db).expanduser().resolve()))
    return 0


def cmd_types(_: argparse.Namespace) -> int:
    for t in ELEMENT_TYPES:
        print(t)
    return 0


def cmd_formats(_: argparse.Namespace) -> int:
    for f in FORMATS:
        print(f)
    return 0


def cmd_rels(_: argparse.Namespace) -> int:
    for r in LINK_RELATIONS:
        print(r)
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    body = _read_body(args.body, args.file)
    tags = _split_csv_or_repeat(args.tag)
    element_id = create_element(
        conn,
        type=args.type,
        title=args.title,
        body=body,
        format=args.format,
        tags=tags or None,
    )
    print(element_id)
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    e = get_element(conn, args.id, include_tags=True)
    if not e:
        raise SystemExit(f"No entry found for id: {args.id}")
    print(f"id:         {e['id']}")
    print(f"type:       {e['type']}")
    print(f"format:     {e['format']}")
    print(f"title:      {e['title']}")
    print(f"created_at: {e['created_at']}")
    print(f"updated_at: {e['updated_at']}")
    print(f"tags:       {', '.join(e.get('tags', []))}")
    print("\n--- body ---\n")
    print(e["body"])
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    rows = list_elements(
        conn,
        type=args.type,
        q=args.q,
        tag=args.tag,
        format=args.format,
        limit=args.limit,
        offset=args.offset,
        include_tags=args.include_tags,
    )
    # Print IDs only
    if args.format_output == "ids":
        for r in rows:
            print(r["id"])
        return 0
    if not rows:
        return 0
    idw, datew = 36, 20
    typew = max(4, min(14, max(len(r["type"]) for r in rows)))
    fmtw = max(6, min(8, max(len(r["format"]) for r in rows)))
    print(f"{'id':<{idw}}  {'type':<{typew}}  {'fmt':<{fmtw}}  {'updated_at':<{datew}}  title")
    print("-" * (idw + typew + fmtw + datew + 10 + 20))
    for r in rows:
        title = str(r["title"]).replace("\n", " ").strip()
        print(
            f"{r['id']:<{idw}}  {r['type']:<{typew}}  {r['format']:<{fmtw}}  {r['updated_at']:<{datew}}  {title}"
        )
        if args.include_tags:
            tags = ", ".join(r.get("tags", []))
            if tags:
                print(f"{'':<{idw}}  {'':<{typew}}  {'':<{fmtw}}  {'':<{datew}}  tags: {tags}")
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    body = None
    if args.body is not None or args.file is not None:
        body = _read_body(args.body, args.file)
    elif args.read_stdin and not sys.stdin.isatty():
        body = sys.stdin.read().strip("\n")
    tags = None
    if args.tags_set is not None:
        tags = _split_csv_or_repeat(args.tags_set)
    ok = update_element(
        conn,
        args.id,
        type=args.type,
        title=args.title,
        body=body,
        format=args.format,
        tags=tags,
    )
    if not ok:
        raise SystemExit(f"No entry found for id: {args.id}")
    print(args.id)
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    if not args.yes:
        ans = input(f"Delete {args.id}? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            print("Canceled.")
            return 0
    ok = delete_element(conn, args.id)
    if not ok:
        raise SystemExit(f"No entry found for id: {args.id}")
    print(args.id)
    return 0


# -----------------------------------------------------------------------------
# Tags commands
# -----------------------------------------------------------------------------


def cmd_tags_list(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    tags = list_tags(conn, args.id)
    for t in tags:
        print(t)
    return 0


def cmd_tags_add(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    n = add_tags(conn, args.id, args.tags)
    print(n)
    return 0


def cmd_tags_remove(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    n = remove_tags(conn, args.id, args.tags)
    print(n)
    return 0


def cmd_tags_set(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    set_tags(conn, args.id, args.tags)
    print(args.id)
    return 0


def cmd_tags_clear(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    n = clear_tags(conn, args.id)
    print(n)
    return 0


def cmd_tags_find(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    rows = list_elements_by_tag(conn, args.tag, limit=args.limit)
    for r in rows:
        print(r["id"])
    return 0


# -----------------------------------------------------------------------------
# Links commands
# -----------------------------------------------------------------------------


def cmd_links_add(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    link_id = create_link(
        conn,
        src_id=args.src,
        dst_id=args.dst,
        rel=args.rel,
        note=args.note or "",
    )
    print(link_id)
    return 0


def cmd_links_get(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    l = get_link(conn, args.id)
    if not l:
        raise SystemExit(f"No link found for id: {args.id}")
    for k in ("id", "src_id", "dst_id", "rel", "note", "created_at", "updated_at"):
        print(f"{k}: {l[k]}")
    return 0


def cmd_links_list(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    rows = list_links(
        conn,
        src_id=args.src,
        dst_id=args.dst,
        rel=args.rel,
        limit=args.limit,
        offset=args.offset,
    )
    for r in rows:
        print(f"{r['id']}  {r['rel']}  {r['src_id']} -> {r['dst_id']}")
    return 0


def cmd_links_for(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    rows = list_links_for_element(
        conn,
        args.element_id,
        direction=args.direction,
        rel=args.rel,
        limit=args.limit,
    )
    for r in rows:
        print(f"{r['id']}  {r['rel']}  {r['src_id']} -> {r['dst_id']}")
    return 0


def cmd_links_update(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    ok = update_link(conn, args.id, rel=args.rel, note=args.note)
    if not ok:
        raise SystemExit(f"No link found for id: {args.id}")
    print(args.id)
    return 0


def cmd_links_delete(args: argparse.Namespace) -> int:
    conn = connect(Path(args.db))
    init_db(conn)
    if not args.yes:
        ans = input(f"Delete link {args.id}? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            print("Canceled.")
            return 0
    ok = delete_link(conn, args.id)
    if not ok:
        raise SystemExit(f"No link found for id: {args.id}")
    print(args.id)
    return 0


# -----------------------------------------------------------------------------
# Static Export
# -----------------------------------------------------------------------------

def cmd_export_html(args: argparse.Namespace) -> int:
    import html
    from datetime import datetime
    from pathlib import Path

    def esc(s: str) -> str:
        return html.escape(s or "", quote=True)

    conn = connect(Path(args.db))
    init_db(conn)

    # ---- load elements ----
    if args.id:
        e = get_element(conn, args.id, include_tags=True)
        if not e:
            raise SystemExit(f"No entry found for id: {args.id}")
        elements = [e]
    else:
        rows = list_elements(
            conn,
            type=args.type,
            q=args.q,
            tag=args.tag,
            format=None,
            limit=args.limit,
            offset=args.offset,
            include_tags=False,
        )
        elements = []
        for r in rows:
            rid = r.get("id")
            if rid:
                e = get_element(conn, rid, include_tags=True)
                if e:
                    elements.append(e)

    if args.format:
        elements = [e for e in elements if (e.get("format") or "").lower() == args.format.lower()]

    elements.sort(key=lambda e: e.get("updated_at", ""), reverse=True)

    # ---- output ----
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    title = args.title or "Proofstore Export"
    generated = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    html_parts: list[str] = []
    html_parts.append("<!doctype html>")
    html_parts.append("<html><head>")
    html_parts.append('<meta charset="utf-8">')
    html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    html_parts.append(f"<title>{esc(title)}</title>")

    # ---- styles (overflow-safe) ----
    html_parts.append(
        """
<style>
* { box-sizing: border-box; }

html, body {
  margin: 0;
  height: 100%;
  overflow: hidden;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
}

.layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

nav {
  flex: 0 0 320px;
  width: 320px;
  border-right: 1px solid #ddd;
  padding: 14px;
  overflow-y: auto;
}

main {
  flex: 1 1 auto;
  min-width: 0;
  padding: 18px;
  overflow-y: auto;
}

.navitem {
  display: block;
  padding: 8px;
  border-radius: 8px;
  text-decoration: none;
  color: #111;
}

.navitem:hover,
.navitem.active {
  background: #f3f4f6;
}

.meta {
  color: #666;
  font-size: 12px;
  margin-bottom: 8px;
}

.card {
  border: 1px solid #ddd;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 16px;
  max-width: 100%;
  min-width: 0;
}

.card.hidden { display: none; }

.pre {
  white-space: pre;
  font-family: ui-monospace, monospace;
  overflow-x: auto;
}

.card pre {
  max-width: 100%;
  overflow-x: auto;
}

.card code {
  word-break: break-word;
}

.card table {
  display: block;
  max-width: 100%;
  overflow-x: auto;
}

.card img, .card iframe, .card video, .card svg {
  max-width: 100%;
  height: auto;
}

.katex-display {
  max-width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
}

.pill {
  background: #f3f4f6;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
}

.id {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: #444;
}

.tags { margin-top: 6px; }

.tag {
  display: inline-block;
  margin-right: 6px;
  margin-bottom: 6px;
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  color: #333;
}
</style>
"""
    )

    # ---- JS deps ----
    html_parts.append('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">')
    html_parts.append('<script src="https://cdn.jsdelivr.net/npm/marked@10.0.0/marked.min.js"></script>')
    html_parts.append('<script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.0/dist/purify.min.js"></script>')
    html_parts.append('<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>')
    html_parts.append('<script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>')

    html_parts.append("</head><body>")
    html_parts.append('<div class="layout">')

    # ---- nav ----
    html_parts.append("<nav>")
    html_parts.append(f"<h3>{esc(title)}</h3>")
    html_parts.append(f"<div class='meta'>Generated {generated}</div>")
    html_parts.append("<a class='navitem' href='#all' data-target='__all__'><b>All</b></a>")

    for e in elements:
        html_parts.append(
            f"<a class='navitem' href='#e-{esc(e['id'])}' data-target='{esc(e['id'])}'>"
            f"<b>{esc(e.get('title',''))}</b><br>"
            f"<span class='meta'>{esc(e.get('type',''))} · {esc(e.get('format','plain'))}</span>"
            f"</a>"
        )
    html_parts.append("</nav>")

    # ---- main ----
    html_parts.append("<main>")
    for e in elements:
        eid = e["id"]
        fmt = (e.get("format") or "plain").lower()

        html_parts.append(f"<section class='card' id='e-{esc(eid)}'>")
        html_parts.append(f"<h2>{esc(e.get('title',''))}</h2>")
        html_parts.append(
            f"<div class='meta'>"
            f"<span class='pill'>{esc(e.get('type',''))}</span> "
            f"<span class='pill'>{esc(fmt)}</span> "
            f"<span class='id'>{esc(eid)}</span>"
            f"</div>"
        )

        if e.get("tags"):
            html_parts.append("<div class='tags'>")
            for t in e["tags"]:
                html_parts.append(f"<span class='tag'>{esc(str(t))}</span>")
            html_parts.append("</div>")

        html_parts.append(f"<div id='body-{esc(eid)}' data-format='{esc(fmt)}'></div>")
        html_parts.append(f"<script type='text/plain' id='raw-{esc(eid)}'>{esc(e.get('body',''))}</script>")

        html_parts.append("</section>")
    html_parts.append("</main>")
    html_parts.append("</div>")

    # ---- renderer + view controller ----
    html_parts.append(
        r"""
<script>
const katexOpts = {
  delimiters: [
    { left: "\\[", right: "\\]", display: true },
    { left: "$$", right: "$$", display: true },
    { left: "\\(", right: "\\)", display: false },
    { left: "$", right: "$", display: false },
  ],
  throwOnError: false,
};

function renderMarkdownLatex(el, src) {
  const math = [];
  const placeholder = i => `@@MATH_${i}@@`;

  const patterns = [
    /\$\$[\s\S]*?\$\$/g,
    /\\\[[\s\S]*?\\\]/g,
    /\\\([\s\S]*?\\\)/g,
    /\$[^$\n]+\$/g,
  ];

  let text = src || "";
  for (const re of patterns) {
    text = text.replace(re, m => {
      const i = math.length;
      math.push(m);
      return placeholder(i);
    });
  }

  let html = DOMPurify.sanitize(marked.parse(text));
  html = html.replace(/@@MATH_(\d+)@@/g, (_, n) => math[n] || "");
  el.innerHTML = html;
  renderMathInElement(el, katexOpts);
}

document.querySelectorAll("[id^='body-']").forEach(el => {
  const id = el.id.slice(5);
  const raw = document.getElementById("raw-" + id)?.textContent || "";
  const fmt = el.dataset.format;

  if (fmt === "markdown" || fmt === "latex") {
    renderMarkdownLatex(el, raw);
  } else if (fmt === "html") {
    el.innerHTML = DOMPurify.sanitize(raw);
    renderMathInElement(el, katexOpts);
  } else {
    el.classList.add("pre");
    el.textContent = raw;
  }
});

function setView(target) {
  document.querySelectorAll("section.card").forEach(c => {
    c.classList.toggle("hidden", target !== "__all__" && c.id !== "e-" + target);
  });

  document.querySelectorAll(".navitem").forEach(a => {
    a.classList.toggle("active", a.dataset.target === target);
  });

  document.querySelector("main").scrollTop = 0;
}

function syncFromHash() {
  const h = location.hash.replace("#", "");
  if (h === "all") return setView("__all__");
  if (h.startsWith("e-")) return setView(h.slice(2));
  const first = document.querySelector("section.card");
  if (first) setView(first.id.slice(2));
}

document.querySelector("nav").addEventListener("click", e => {
  const a = e.target.closest(".navitem");
  if (!a) return;
  e.preventDefault();
  const t = a.dataset.target;
  location.hash = t === "__all__" ? "#all" : "#e-" + t;
});

window.addEventListener("hashchange", syncFromHash);
syncFromHash();
</script>
"""
    )

    html_parts.append("</body></html>")
    out_path.write_text("\n".join(html_parts), encoding="utf-8")
    print(str(out_path))
    return 0


# -----------------------------------------------------------------------------
# Argument parser
# -----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    default_db = os.environ.get("PROOF_DB", "./proof_elements.sqlite3")
    p = argparse.ArgumentParser(
        prog="proofstore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """
            proofstore: minimal proof element store (SQLite) with formats, tags and links.

            Examples:
              proofstore --db proofs.db init
              proofstore --db proofs.db add --type theorem --title "FLT" --file flt.md --format markdown --tag number-theory --tag primes
              proofstore --db proofs.db list --type theorem --tag primes --include-tags
              proofstore --db proofs.db tags add <uuid> algebra topology
              proofstore --db proofs.db links add --src <proof_uuid> --dst <theorem_uuid> --rel proves --note "Main proof"
              proofstore --db proofs.db export-html --out export.html --with-links
            """
        ),
    )
    p.add_argument(
        "--db",
        default=default_db,
        help=f"SQLite db file path (default: {default_db})",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # init
    sp = sub.add_parser("init", help="Create tables/indexes if missing")
    sp.set_defaults(func=cmd_init)

    # types
    sp = sub.add_parser("types", help="List supported element types")
    sp.set_defaults(func=cmd_types)

    # formats
    sp = sub.add_parser("formats", help="List supported body formats")
    sp.set_defaults(func=cmd_formats)

    # relations
    sp = sub.add_parser("rels", help="List supported link relations")
    sp.set_defaults(func=cmd_rels)

    # add
    sp = sub.add_parser("add", help="Create an element (prints UUID)")
    sp.add_argument("--type", required=True, choices=ELEMENT_TYPES)
    sp.add_argument("--format", required=False, choices=FORMATS, default="plain")
    sp.add_argument("--title", required=True)
    sp.add_argument("--body", help="Body text (or use --file or stdin)")
    sp.add_argument("--file", help="Read body from a file")
    sp.add_argument("--tag", action="append", help="Tag (repeatable; comma-separated allowed)")
    sp.set_defaults(func=cmd_add)

    # get
    sp = sub.add_parser("get", help="Read an element by UUID")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_get)

    # list
    sp = sub.add_parser("list", help="List elements")
    sp.add_argument("--type", choices=ELEMENT_TYPES)
    sp.add_argument("--format", choices=FORMATS)
    sp.add_argument("--q", help="Search in title/body")
    sp.add_argument("--tag", help="Filter by tag")
    sp.add_argument("--limit", type=int)
    sp.add_argument("--offset", type=int)
    sp.add_argument("--format-output", choices=("table", "ids"), default="table", help="Output format")
    sp.add_argument("--include-tags", action="store_true", help="Include tags in output")
    sp.set_defaults(func=cmd_list)

    # update
    sp = sub.add_parser("update", help="Update an element (prints UUID)")
    sp.add_argument("id")
    sp.add_argument("--type", choices=ELEMENT_TYPES)
    sp.add_argument("--format", choices=FORMATS)
    sp.add_argument("--title")
    sp.add_argument("--body")
    sp.add_argument("--file")
    sp.add_argument(
        "--read-stdin",
        action="store_true",
        help="If stdin is piped, read it as the new body",
    )
    sp.add_argument(
        "--tags-set",
        action="append",
        help="Replace tags entirely (repeatable; comma-separated allowed)",
    )
    sp.set_defaults(func=cmd_update)

    # delete
    sp = sub.add_parser("delete", help="Delete an element (prints UUID)")
    sp.add_argument("id")
    sp.add_argument("--yes", action="store_true")
    sp.set_defaults(func=cmd_delete)

    # tags group
    t = sub.add_parser("tags", help="Manage tags")
    tsub = t.add_subparsers(dest="tags_cmd", required=True)

    sp = tsub.add_parser("list", help="List tags for an element")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_tags_list)

    sp = tsub.add_parser("add", help="Add tags to an element (prints count added)")
    sp.add_argument("id")
    sp.add_argument("tags", nargs="+")
    sp.set_defaults(func=cmd_tags_add)

    sp = tsub.add_parser("remove", help="Remove tags from an element (prints count removed)")
    sp.add_argument("id")
    sp.add_argument("tags", nargs="+")
    sp.set_defaults(func=cmd_tags_remove)

    sp = tsub.add_parser("set", help="Replace tags for an element")
    sp.add_argument("id")
    sp.add_argument("tags", nargs="*")
    sp.set_defaults(func=cmd_tags_set)

    sp = tsub.add_parser("clear", help="Clear all tags for an element (prints count removed)")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_tags_clear)

    sp = tsub.add_parser("find", help="Find elements by tag (prints element IDs)")
    sp.add_argument("tag")
    sp.add_argument("--limit", type=int)
    sp.set_defaults(func=cmd_tags_find)

    # links group
    l = sub.add_parser("links", help="Manage links between elements")
    lsub = l.add_subparsers(dest="links_cmd", required=True)

    sp = lsub.add_parser("add", help="Create a link (prints link UUID)")
    sp.add_argument("--src", required=True)
    sp.add_argument("--dst", required=True)
    sp.add_argument("--rel", required=True, choices=LINK_RELATIONS)
    sp.add_argument("--note")
    sp.set_defaults(func=cmd_links_add)

    sp = lsub.add_parser("get", help="Get a link by UUID")
    sp.add_argument("id")
    sp.set_defaults(func=cmd_links_get)

    sp = lsub.add_parser("list", help="List links")
    sp.add_argument("--src")
    sp.add_argument("--dst")
    sp.add_argument("--rel", choices=LINK_RELATIONS)
    sp.add_argument("--limit", type=int)
    sp.add_argument("--offset", type=int)
    sp.set_defaults(func=cmd_links_list)

    sp = lsub.add_parser("for", help="List links for a given element")
    sp.add_argument("element_id")
    sp.add_argument("--direction", choices=("out", "in", "both"), default="both")
    sp.add_argument("--rel", choices=LINK_RELATIONS)
    sp.add_argument("--limit", type=int)
    sp.set_defaults(func=cmd_links_for)

    sp = lsub.add_parser("update", help="Update a link")
    sp.add_argument("id")
    sp.add_argument("--rel", choices=LINK_RELATIONS)
    sp.add_argument("--note")
    sp.set_defaults(func=cmd_links_update)

    sp = lsub.add_parser("delete", help="Delete a link")
    sp.add_argument("id")
    sp.add_argument("--yes", action="store_true")
    sp.set_defaults(func=cmd_links_delete)

    # export-html (single, top-level)
    sp = sub.add_parser("export-html", help="Export elements as a single static HTML file")
    sp.add_argument("--out", required=True, help="Output HTML file path")
    sp.add_argument("--title", help="Document title")
    sp.add_argument("--id", help="Export only a single element UUID")
    sp.add_argument("--type", choices=ELEMENT_TYPES)
    sp.add_argument("--format", choices=FORMATS, help="Filter by body format")
    sp.add_argument("--tag", help="Filter by tag")
    sp.add_argument("--q", help="Search in title/body")
    sp.add_argument("--limit", type=int)
    sp.add_argument("--offset", type=int)
    sp.add_argument("--with-links", action="store_true", help="Include outgoing links section")
    sp.set_defaults(func=cmd_export_html)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    main()
