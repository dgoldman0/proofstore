from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path

from .core import (
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
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))