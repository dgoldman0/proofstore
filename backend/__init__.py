"""
proofstore
===========

This package exposes high-level interfaces for creating and querying a
lightweight proof management store. It bundles constants and CRUD functions
from `core.py` so that external modules can import them without directly
touching implementation details. See documentation in `core.py` for details.
"""

from .core import (
    ELEMENT_TYPES,
    FORMATS,
    LINK_RELATIONS,
    connect,
    init_db,
    secure_uuid4_str,
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

__all__ = [
    "ELEMENT_TYPES",
    "FORMATS",
    "LINK_RELATIONS",
    "connect",
    "init_db",
    "secure_uuid4_str",
    "create_element",
    "get_element",
    "list_elements",
    "update_element",
    "delete_element",
    "list_tags",
    "add_tags",
    "remove_tags",
    "clear_tags",
    "set_tags",
    "list_elements_by_tag",
    "create_link",
    "get_link",
    "list_links",
    "update_link",
    "delete_link",
    "list_links_for_element",
]