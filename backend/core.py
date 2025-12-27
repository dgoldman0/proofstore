from __future__ import annotations

import datetime as dt
import secrets
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Optional, Sequence

"""
core.py

This module provides the storage backend for the proofstore project. It defines
the schema and a set of functions for working with proof elements, tags and
links. It also includes semantic validation for link relations. Elements
support different textual formats (plain text, markdown, HTML, LaTeX) so that
clients can render content appropriately.

The functions in this module do not perform any I/O beyond interacting with
SQLite; callers are responsible for handling user input and converting these
functions into CLI or HTTP handlers.
"""

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Supported element types. See ELEMENT_TYPES in other modules for consistency.
ELEMENT_TYPES: tuple[str, ...] = (
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
)

# Supported body formats. Clients should select one of these values when
# creating or updating elements. The default is 'plain'.
FORMATS: tuple[str, ...] = (
    "plain",     # raw text with no markup
    "markdown",  # GitHub‑flavoured markdown
    "html",      # HTML (should be sanitised on display)
    "latex",     # LaTeX (KaTeX or similar rendering on client)
)

# Supported link relation types. These mirror typical mathematical relationships
# between statements.
LINK_RELATIONS: tuple[str, ...] = (
    "proves",           # proof -> statement
    "uses",             # statement/proof -> definition/axiom/lemma/statement
    "implies",          # statement -> statement
    "equivalent_to",    # statement <-> statement
    "example_of",       # example -> statement/definition
    "counterexample_to",# counterexample -> statement/definition
    "related",          # generic relationship
)

# Define subsets of element types used for link semantics
STATEMENTS = {
    "axiom", "postulate", "lemma", "proposition", "theorem", "corollary"
}
DERIVED_STATEMENTS = {"lemma", "proposition", "theorem", "corollary"}
STATEMENT_OR_DEF = STATEMENTS | {"definition"}
STATEMENT_LIKE_FOR_EQ = {"definition", "lemma", "proposition", "theorem", "corollary"}

# Semantic rules for links. Each relation specifies allowable source and
# destination types. See validate_link_semantics() for enforcement.
REL_RULES: dict[str, tuple[set[str], set[str]]] = {
    "proves": ( {"proof"}, DERIVED_STATEMENTS ),
    "uses": ( STATEMENTS | {"proof"}, STATEMENT_OR_DEF ),
    "example_of": ( {"example"}, STATEMENT_LIKE_FOR_EQ ),
    "counterexample_to": ( {"counterexample"}, STATEMENT_LIKE_FOR_EQ ),
    "equivalent_to": ( STATEMENT_LIKE_FOR_EQ, STATEMENT_LIKE_FOR_EQ ),
    "implies": ( STATEMENTS, STATEMENTS ),
    "related": ( set(ELEMENT_TYPES), set(ELEMENT_TYPES) ),
}

# -----------------------------------------------------------------------------
# Utility functions
# -----------------------------------------------------------------------------

def now_utc_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format without microseconds."""
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def secure_uuid4_str() -> str:
    """Return a cryptographically secure random UUID4 as a string."""
    u = uuid.UUID(bytes=secrets.token_bytes(16), version=4)
    return str(u)


def connect(db_path: Path) -> sqlite3.Connection:
    """
    Connect to the SQLite database at the given path. The directory for the
    database file is created if necessary. The connection will have row_factory
    set to sqlite3.Row and foreign keys enabled.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        sqlite3.Connection instance.
    """
    db_path = db_path.expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """
    Initialise the database schema if not present. Creates tables for
    elements, tags and links, and associated indexes. The elements table
    includes a 'format' column with a default of 'plain'. A unique index on
    (src_id, dst_id, rel) prevents duplicate links of the same type.
    """
    type_list = ", ".join([f"'{t}'" for t in ELEMENT_TYPES])
    rel_list = ", ".join([f"'{r}'" for r in LINK_RELATIONS])
    format_list = ", ".join([f"'{f}'" for f in FORMATS])

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS elements (
            id         TEXT PRIMARY KEY,
            type       TEXT NOT NULL CHECK(type IN ({type_list})),
            format     TEXT NOT NULL CHECK(format IN ({format_list})) DEFAULT 'plain',
            title      TEXT NOT NULL,
            body       TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS element_tags (
            element_id TEXT NOT NULL,
            tag        TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (element_id, tag),
            FOREIGN KEY (element_id) REFERENCES elements(id) ON DELETE CASCADE
        );
        """
    )

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS element_links (
            id         TEXT PRIMARY KEY,
            src_id     TEXT NOT NULL,
            dst_id     TEXT NOT NULL,
            rel        TEXT NOT NULL CHECK(rel IN ({rel_list})),
            note       TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (src_id) REFERENCES elements(id) ON DELETE CASCADE,
            FOREIGN KEY (dst_id) REFERENCES elements(id) ON DELETE CASCADE
        );
        """
    )

    # Indexes for performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_elements_type ON elements(type);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_elements_title ON elements(title);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_elements_format ON elements(format);")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON element_tags(tag);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_element ON element_tags(element_id);")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_links_src ON element_links(src_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_links_dst ON element_links(dst_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_links_rel ON element_links(rel);")
    # Unique index prevents duplicate links of the same relation between the same elements
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_links_src_dst_rel ON element_links(src_id, dst_id, rel);"
    )

    conn.commit()


# -----------------------------------------------------------------------------
# Validation helpers
# -----------------------------------------------------------------------------

def validate_type(t: str) -> str:
    """Ensure that a supplied element type is valid."""
    if t not in ELEMENT_TYPES:
        raise ValueError(f"Invalid type '{t}'. Must be one of: {', '.join(ELEMENT_TYPES)}")
    return t


def validate_format(fmt: str) -> str:
    """Ensure that a supplied format is valid."""
    if fmt not in FORMATS:
        raise ValueError(f"Invalid format '{fmt}'. Must be one of: {', '.join(FORMATS)}")
    return fmt


def validate_rel(rel: str) -> str:
    """Ensure that a supplied link relation is valid."""
    if rel not in LINK_RELATIONS:
        raise ValueError(f"Invalid rel '{rel}'. Must be one of: {', '.join(LINK_RELATIONS)}")
    return rel


def _fetch_type(conn: sqlite3.Connection, element_id: str) -> Optional[str]:
    """Return the type of the element with the given ID or None if missing."""
    r = conn.execute("SELECT type FROM elements WHERE id = ?;", (element_id,)).fetchone()
    return r["type"] if r else None


def validate_link_semantics(conn: sqlite3.Connection, *, src_id: str, dst_id: str, rel: str) -> None:
    """
    Enforce semantic link rules defined in REL_RULES. Raises ValueError if the link
    would be invalid. Also checks that both element IDs exist and that they are
    distinct. See REL_RULES for the allowed type combinations.
    """
    rel = validate_rel(rel)
    if src_id == dst_id:
        raise ValueError("src_id and dst_id must differ")
    src_type = _fetch_type(conn, src_id)
    dst_type = _fetch_type(conn, dst_id)
    if not src_type:
        raise ValueError(f"src_id not found: {src_id}")
    if not dst_type:
        raise ValueError(f"dst_id not found: {dst_id}")
    allowed_src, allowed_dst = REL_RULES[rel]
    if src_type not in allowed_src:
        raise ValueError(
            f"rel '{rel}' requires src type in {sorted(allowed_src)}, got '{src_type}'"
        )
    if dst_type not in allowed_dst:
        raise ValueError(
            f"rel '{rel}' requires dst type in {sorted(allowed_dst)}, got '{dst_type}'"
        )


# -----------------------------------------------------------------------------
# Element CRUD (with format and tags)
# -----------------------------------------------------------------------------

def create_element(
    conn: sqlite3.Connection,
    *,
    type: str,
    title: str,
    body: str,
    format: str = "plain",
    tags: Optional[Sequence[str]] = None,
    id: Optional[str] = None,
) -> str:
    """
    Insert a new element into the database. A cryptographically secure UUID4
    will be generated if `id` is None. The type and format are validated.

    Args:
        conn: SQLite connection
        type: Element type (must be in ELEMENT_TYPES)
        title: Short title of the element
        body: Full text of the element
        format: Body format (must be in FORMATS; default 'plain')
        tags: Optional list of tags to associate with the element
        id: Optional explicit UUID; generate automatically if None

    Returns:
        The UUID of the newly created element
    """
    validate_type(type)
    validate_format(format)
    if not title.strip():
        raise ValueError("title is empty")
    if not body.strip():
        raise ValueError("body is empty")
    element_id = id or secure_uuid4_str()
    ts = now_utc_iso()
    conn.execute(
        """
        INSERT INTO elements (id, type, format, title, body, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (element_id, type, format, title, body, ts, ts),
    )
    if tags is not None:
        set_tags(conn, element_id, tags)
    conn.commit()
    return element_id


def get_element(
    conn: sqlite3.Connection,
    element_id: str,
    *,
    include_tags: bool = True,
) -> Optional[dict[str, Any]]:
    """
    Retrieve a single element by ID. Returns None if not found. Optionally
    includes tags.
    """
    row = conn.execute("SELECT * FROM elements WHERE id = ?;", (element_id,)).fetchone()
    if not row:
        return None
    d = {k: row[k] for k in row.keys()}
    if include_tags:
        d["tags"] = list_tags(conn, element_id)
    return d


def list_elements(
    conn: sqlite3.Connection,
    *,
    type: Optional[str] = None,
    q: Optional[str] = None,
    tag: Optional[str] = None,
    format: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    order_by: str = "updated_at",
    order_dir: str = "DESC",
    include_tags: bool = False,
) -> list[dict[str, Any]]:
    """
    List elements with optional filtering by type, search query, tag and
    format. Supports ordering and pagination. Optionally include tags in the
    returned dictionaries.
    """
    if type is not None:
        validate_type(type)
    if format is not None:
        validate_format(format)
    order_by_allowed = {"updated_at", "created_at", "title", "type", "format"}
    if order_by not in order_by_allowed:
        raise ValueError(f"order_by must be one of {sorted(order_by_allowed)}")
    order_dir_u = order_dir.upper()
    if order_dir_u not in {"ASC", "DESC"}:
        raise ValueError("order_dir must be ASC or DESC")
    where = []
    params: list[Any] = []
    join = ""
    if tag is not None:
        join = " JOIN element_tags et ON et.element_id = e.id "
        where.append("et.tag = ?")
        params.append(_normalize_tag(tag))
    if type:
        where.append("e.type = ?")
        params.append(type)
    if format:
        where.append("e.format = ?")
        params.append(format)
    if q:
        where.append("(e.title LIKE ? OR e.body LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = f"SELECT e.* FROM elements e{join}{where_sql} ORDER BY e.{order_by} {order_dir_u}"
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        sql += " LIMIT ?"
        params.append(limit)
    if offset is not None:
        if offset < 0:
            raise ValueError("offset must be >= 0")
        if limit is None:
            sql += " LIMIT -1"
        sql += " OFFSET ?"
        params.append(offset)
    rows = conn.execute(sql + ";", tuple(params)).fetchall()
    out = [{k: r[k] for k in r.keys()} for r in rows]
    if include_tags:
        for d in out:
            d["tags"] = list_tags(conn, d["id"])
    return out


def update_element(
    conn: sqlite3.Connection,
    element_id: str,
    *,
    type: Optional[str] = None,
    title: Optional[str] = None,
    body: Optional[str] = None,
    format: Optional[str] = None,
    tags: Optional[Sequence[str]] = None,  # replace if provided
) -> bool:
    """
    Update an existing element. Returns False if the element does not exist.
    Only the fields provided are updated. If tags is provided, replaces
    existing tags.
    """
    existing = conn.execute("SELECT * FROM elements WHERE id = ?;", (element_id,)).fetchone()
    if not existing:
        return False
    new_type = validate_type(type) if type is not None else existing["type"]
    new_title = title if title is not None else existing["title"]
    new_body = body if body is not None else existing["body"]
    new_format = validate_format(format) if format is not None else existing["format"]
    if not str(new_title).strip():
        raise ValueError("title is empty")
    if not str(new_body).strip():
        raise ValueError("body is empty")
    ts = now_utc_iso()
    conn.execute(
        """
        UPDATE elements
        SET type = ?, format = ?, title = ?, body = ?, updated_at = ?
        WHERE id = ?;
        """,
        (new_type, new_format, new_title, new_body, ts, element_id),
    )
    if tags is not None:
        set_tags(conn, element_id, tags)
    conn.commit()
    return True


def delete_element(conn: sqlite3.Connection, element_id: str) -> bool:
    """Delete an element by ID. Returns True if deleted."""
    cur = conn.execute("DELETE FROM elements WHERE id = ?;", (element_id,))
    conn.commit()
    return cur.rowcount > 0


# -----------------------------------------------------------------------------
# Tag management
# -----------------------------------------------------------------------------

def _normalize_tag(tag: str) -> str:
    t = (tag or "").strip()
    if not t:
        raise ValueError("tag is empty")
    if len(t) > 128:
        raise ValueError("tag too long (max 128)")
    return t


def _normalize_tags(tags: Sequence[str]) -> list[str]:
    norm = [_normalize_tag(t) for t in tags]
    seen: set[str] = set()
    out: list[str] = []
    for t in norm:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


def list_tags(conn: sqlite3.Connection, element_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT tag FROM element_tags WHERE element_id = ? ORDER BY tag ASC;",
        (element_id,),
    ).fetchall()
    return [r["tag"] for r in rows]


def add_tags(conn: sqlite3.Connection, element_id: str, tags: Sequence[str]) -> int:
    norm = _normalize_tags(tags)
    ts = now_utc_iso()
    added = 0
    for t in norm:
        cur = conn.execute(
            "INSERT OR IGNORE INTO element_tags (element_id, tag, created_at) VALUES (?, ?, ?);",
            (element_id, t, ts),
        )
        added += cur.rowcount
    conn.commit()
    return added


def remove_tags(conn: sqlite3.Connection, element_id: str, tags: Sequence[str]) -> int:
    norm = _normalize_tags(tags)
    removed = 0
    for t in norm:
        cur = conn.execute(
            "DELETE FROM element_tags WHERE element_id = ? AND tag = ?;",
            (element_id, t),
        )
        removed += cur.rowcount
    conn.commit()
    return removed


def clear_tags(conn: sqlite3.Connection, element_id: str) -> int:
    cur = conn.execute("DELETE FROM element_tags WHERE element_id = ?;", (element_id,))
    conn.commit()
    return cur.rowcount


def set_tags(conn: sqlite3.Connection, element_id: str, tags: Sequence[str]) -> None:
    norm = _normalize_tags(tags)
    ts = now_utc_iso()
    conn.execute("DELETE FROM element_tags WHERE element_id = ?;", (element_id,))
    for t in norm:
        conn.execute(
            "INSERT INTO element_tags (element_id, tag, created_at) VALUES (?, ?, ?);",
            (element_id, t, ts),
        )
    conn.commit()


def list_elements_by_tag(conn: sqlite3.Connection, tag: str, *, limit: Optional[int] = None) -> list[dict[str, Any]]:
    t = _normalize_tag(tag)
    sql = """
        SELECT e.* FROM elements e
        JOIN element_tags et ON et.element_id = e.id
        WHERE et.tag = ?
        ORDER BY e.updated_at DESC
    """
    params: list[Any] = [t]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        sql += " LIMIT ?"
        params.append(limit)
    rows = conn.execute(sql + ";", tuple(params)).fetchall()
    return [{k: r[k] for k in r.keys()} for r in rows]


# -----------------------------------------------------------------------------
# Link management
# -----------------------------------------------------------------------------

def create_link(
    conn: sqlite3.Connection,
    *,
    src_id: str,
    dst_id: str,
    rel: str,
    note: str = "",
    id: Optional[str] = None,
) -> str:
    """
    Create a new link between two elements. Enforces semantic rules and ensures
    no duplicate (src_id, dst_id, rel) exists. Returns the link UUID.
    """
    validate_rel(rel)
    # Semantic check and existence check
    validate_link_semantics(conn, src_id=src_id, dst_id=dst_id, rel=rel)
    link_id = id or secure_uuid4_str()
    ts = now_utc_iso()
    conn.execute(
        """
        INSERT INTO element_links (id, src_id, dst_id, rel, note, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (link_id, src_id, dst_id, rel, note or "", ts, ts),
    )
    conn.commit()
    return link_id


def get_link(conn: sqlite3.Connection, link_id: str) -> Optional[dict[str, Any]]:
    row = conn.execute("SELECT * FROM element_links WHERE id = ?;", (link_id,)).fetchone()
    return {k: row[k] for k in row.keys()} if row else None


def list_links(
    conn: sqlite3.Connection,
    *,
    src_id: Optional[str] = None,
    dst_id: Optional[str] = None,
    rel: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    order_by: str = "updated_at",
    order_dir: str = "DESC",
) -> list[dict[str, Any]]:
    order_by_allowed = {"updated_at", "created_at", "rel"}
    if order_by not in order_by_allowed:
        raise ValueError(f"order_by must be one of {sorted(order_by_allowed)}")
    order_dir_u = order_dir.upper()
    if order_dir_u not in {"ASC", "DESC"}:
        raise ValueError("order_dir must be ASC or DESC")
    where = []
    params: list[Any] = []
    if src_id:
        where.append("src_id = ?")
        params.append(src_id)
    if dst_id:
        where.append("dst_id = ?")
        params.append(dst_id)
    if rel:
        validate_rel(rel)
        where.append("rel = ?")
        params.append(rel)
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = f"SELECT * FROM element_links{where_sql} ORDER BY {order_by} {order_dir_u}"
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        sql += " LIMIT ?"
        params.append(limit)
    if offset is not None:
        if offset < 0:
            raise ValueError("offset must be >= 0")
        if limit is None:
            sql += " LIMIT -1"
        sql += " OFFSET ?"
        params.append(offset)
    rows = conn.execute(sql + ";", tuple(params)).fetchall()
    return [{k: r[k] for k in r.keys()} for r in rows]


def update_link(
    conn: sqlite3.Connection,
    link_id: str,
    *,
    rel: Optional[str] = None,
    note: Optional[str] = None,
) -> bool:
    existing = conn.execute("SELECT * FROM element_links WHERE id = ?;", (link_id,)).fetchone()
    if not existing:
        return False
    new_rel = validate_rel(rel) if rel is not None else existing["rel"]
    new_note = (note if note is not None else existing["note"]) or ""
    # Revalidate semantics if relation changed
    if rel is not None:
        validate_link_semantics(conn, src_id=existing["src_id"], dst_id=existing["dst_id"], rel=new_rel)
    ts = now_utc_iso()
    conn.execute(
        """
        UPDATE element_links
        SET rel = ?, note = ?, updated_at = ?
        WHERE id = ?;
        """,
        (new_rel, new_note, ts, link_id),
    )
    conn.commit()
    return True


def delete_link(conn: sqlite3.Connection, link_id: str) -> bool:
    cur = conn.execute("DELETE FROM element_links WHERE id = ?;", (link_id,))
    conn.commit()
    return cur.rowcount > 0


def list_links_for_element(
    conn: sqlite3.Connection,
    element_id: str,
    *,
    direction: str = "both",  # "out", "in", "both"
    rel: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    direction = (direction or "both").lower()
    if direction not in {"out", "in", "both"}:
        raise ValueError("direction must be one of: out, in, both")
    if rel is not None:
        validate_rel(rel)
    where = []
    params: list[Any] = []
    if direction == "out":
        where.append("src_id = ?")
        params.append(element_id)
    elif direction == "in":
        where.append("dst_id = ?")
        params.append(element_id)
    else:
        where.append("(src_id = ? OR dst_id = ?)")
        params.extend([element_id, element_id])
    if rel:
        where.append("rel = ?")
        params.append(rel)
    sql = "SELECT * FROM element_links WHERE " + " AND ".join(where) + " ORDER BY updated_at DESC"
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        sql += " LIMIT ?"
        params.append(limit)
    rows = conn.execute(sql + ";", tuple(params)).fetchall()
    return [{k: r[k] for k in r.keys()} for r in rows]