"""
flaskapp.py

This module exposes a minimal Flask API for the proofstore backend. It
provides endpoints for listing supported types, formats and link relations,
creating and managing elements with different body formats, tags and links.
Use create_app() to obtain a Flask application configured with a SQLite
database path.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from flask import Flask, Blueprint, jsonify, request, g

from .core import (
    ELEMENT_TYPES,
    FORMATS,
    LINK_RELATIONS,
    connect,
    init_db,
    # elements
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
    # links
    create_link,
    get_link,
    list_links,
    update_link,
    delete_link,
    list_links_for_element,
)


def create_app(db_path: str | None = None) -> Flask:
    """Factory to create and configure the Flask application."""
    app = Flask(__name__)
    app.config["PROOF_DB"] = db_path or os.environ.get("PROOF_DB", "./proof_elements.sqlite3")
    api = Blueprint("api", __name__)

    def get_conn():
        if "conn" not in g:
            g.conn = connect(Path(app.config["PROOF_DB"]))
            init_db(g.conn)
        return g.conn

    @app.teardown_appcontext
    def close_conn(_exc):
        conn = g.pop("conn", None)
        if conn is not None:
            conn.close()

    def bad_request(msg: str):
        return jsonify({"error": msg}), 400

    # Metadata endpoints
    @api.get("/types")
    def types():
        return jsonify({"types": list(ELEMENT_TYPES)})

    @api.get("/formats")
    def formats():
        return jsonify({"formats": list(FORMATS)})

    @api.get("/rels")
    def rels():
        return jsonify({"rels": list(LINK_RELATIONS)})

    # Elements endpoints
    @api.post("/elements")
    def elements_create():
        data = request.get_json(force=True, silent=False) or {}
        try:
            element_id = create_element(
                get_conn(),
                type=str(data.get("type", "")).strip(),
                title=str(data.get("title", "")).strip(),
                body=str(data.get("body", "")).rstrip(),
                format=str(data.get("format", "plain")).strip() or "plain",
                tags=data.get("tags", None),
            )
        except Exception as e:
            return bad_request(str(e))
        return jsonify({"id": element_id}), 201

    @api.get("/elements")
    def elements_list():
        t = request.args.get("type")
        q = request.args.get("q")
        tag = request.args.get("tag")
        fmt = request.args.get("format")
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)
        include_tags = request.args.get("include_tags", "0") in ("1", "true", "yes")
        try:
            rows = list_elements(
                get_conn(),
                type=t,
                q=q,
                tag=tag,
                format=fmt,
                limit=limit,
                offset=offset,
                include_tags=include_tags,
            )
        except Exception as e:
            return bad_request(str(e))
        return jsonify({"elements": rows})

    @api.get("/elements/<element_id>")
    def elements_get(element_id: str):
        e = get_element(get_conn(), element_id, include_tags=True)
        if not e:
            return jsonify({"error": "not found"}), 404
        return jsonify(e)

    @api.patch("/elements/<element_id>")
    @api.put("/elements/<element_id>")
    def elements_update(element_id: str):
        data = request.get_json(force=True, silent=False) or {}
        try:
            ok = update_element(
                get_conn(),
                element_id,
                type=(str(data["type"]).strip() if "type" in data else None),
                title=(str(data["title"]).strip() if "title" in data else None),
                body=(str(data["body"]).rstrip() if "body" in data else None),
                format=(str(data["format"]).strip() if "format" in data else None),
                tags=(data["tags"] if "tags" in data else None),
            )
        except Exception as e:
            return bad_request(str(e))
        if not ok:
            return jsonify({"error": "not found"}), 404
        return jsonify({"id": element_id})

    @api.delete("/elements/<element_id>")
    def elements_delete(element_id: str):
        ok = delete_element(get_conn(), element_id)
        if not ok:
            return jsonify({"error": "not found"}), 404
        return jsonify({"id": element_id})

    # Tags endpoints
    @api.get("/elements/<element_id>/tags")
    def tags_get(element_id: str):
        # Ensure element exists
        if not get_element(get_conn(), element_id, include_tags=False):
            return jsonify({"error": "not found"}), 404
        return jsonify({"id": element_id, "tags": list_tags(get_conn(), element_id)})

    @api.put("/elements/<element_id>/tags")
    def tags_set_route(element_id: str):
        data = request.get_json(force=True, silent=False) or {}
        tags = data.get("tags", None)
        if tags is None:
            return bad_request("missing 'tags' list")
        try:
            set_tags(get_conn(), element_id, tags)
        except Exception as e:
            return bad_request(str(e))
        return jsonify({"id": element_id, "tags": list_tags(get_conn(), element_id)})

    @api.post("/elements/<element_id>/tags")
    def tags_add_route(element_id: str):
        data = request.get_json(force=True, silent=False) or {}
        tags = data.get("tags", None)
        if tags is None:
            return bad_request("missing 'tags' list")
        try:
            add_tags(get_conn(), element_id, tags)
        except Exception as e:
            return bad_request(str(e))
        return jsonify({"id": element_id, "tags": list_tags(get_conn(), element_id)})

    @api.delete("/elements/<element_id>/tags")
    def tags_delete_route(element_id: str):
        data = request.get_json(force=False, silent=True) or {}
        try:
            if "tags" in data and data["tags"] is not None:
                remove_tags(get_conn(), element_id, data["tags"])
            else:
                clear_tags(get_conn(), element_id)
        except Exception as e:
            return bad_request(str(e))
        return jsonify({"id": element_id, "tags": list_tags(get_conn(), element_id)})

    # Links endpoints
    @api.post("/links")
    def links_create():
        data = request.get_json(force=True, silent=False) or {}
        try:
            link_id = create_link(
                get_conn(),
                src_id=str(data.get("src_id", "")).strip(),
                dst_id=str(data.get("dst_id", "")).strip(),
                rel=str(data.get("rel", "")).strip(),
                note=str(data.get("note", "") or ""),
            )
        except Exception as e:
            return bad_request(str(e))
        return jsonify({"id": link_id}), 201

    @api.get("/links")
    def links_list_route():
        src_id = request.args.get("src_id")
        dst_id = request.args.get("dst_id")
        rel = request.args.get("rel")
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", type=int)
        try:
            rows = list_links(get_conn(), src_id=src_id, dst_id=dst_id, rel=rel, limit=limit, offset=offset)
        except Exception as e:
            return bad_request(str(e))
        return jsonify({"links": rows})

    @api.get("/links/<link_id>")
    def links_get_route(link_id: str):
        l = get_link(get_conn(), link_id)
        if not l:
            return jsonify({"error": "not found"}), 404
        return jsonify(l)

    @api.patch("/links/<link_id>")
    @api.put("/links/<link_id>")
    def links_update_route(link_id: str):
        data = request.get_json(force=True, silent=False) or {}
        try:
            ok = update_link(
                get_conn(),
                link_id,
                rel=(str(data["rel"]).strip() if "rel" in data else None),
                note=(str(data["note"]) if "note" in data else None),
            )
        except Exception as e:
            return bad_request(str(e))
        if not ok:
            return jsonify({"error": "not found"}), 404
        return jsonify({"id": link_id})

    @api.delete("/links/<link_id>")
    def links_delete_route(link_id: str):
        ok = delete_link(get_conn(), link_id)
        if not ok:
            return jsonify({"error": "not found"}), 404
        return jsonify({"id": link_id})

    @api.get("/elements/<element_id>/links")
    def links_for_element_route(element_id: str):
        direction = request.args.get("direction", "both")
        rel = request.args.get("rel")
        limit = request.args.get("limit", type=int)
        try:
            rows = list_links_for_element(get_conn(), element_id, direction=direction, rel=rel, limit=limit)
        except Exception as e:
            return bad_request(str(e))
        return jsonify({"element_id": element_id, "links": rows})

    app.register_blueprint(api, url_prefix="/api")
    return app


if __name__ == "__main__":
    # Standalone run for development/testing
    application = create_app()
    application.run(debug=True)