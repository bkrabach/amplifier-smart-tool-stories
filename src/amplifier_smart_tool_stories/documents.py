"""Portable document structure and deterministic HTML, independent of review state."""

import copy
import re
from html import escape
from importlib.resources import files

from .errors import require


def checked(document, evidence=None):
    require(
        isinstance(document, dict) and set(document) == {"title", "subtitle", "blocks"},
        "Document requires title, subtitle and blocks.",
    )
    require(
        isinstance(document["title"], str) and 0 < len(document["title"]) <= 200, "Invalid document title."
    )
    require(isinstance(document["subtitle"], str) and len(document["subtitle"]) <= 500, "Invalid subtitle.")
    blocks = document["blocks"]
    require(isinstance(blocks, list) and 1 <= len(blocks) <= 100, "Supply 1–100 document blocks.")
    ids = set()
    refs = None if evidence is None else {e["id"] for e in evidence}
    for block in blocks:
        require(
            isinstance(block, dict) and set(block) == {"id", "kind", "text", "items", "rows", "evidence_ids"},
            "Document blocks require id, kind, text, items, rows, evidence_ids.",
        )
        bid = block["id"]
        require(
            isinstance(bid, str)
            and re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}", bid)
            and not bid.startswith("reference-")
            and bid not in ids
            and bid not in {"document", "title", "subtitle", "source-references"},
            "Block IDs must be unique safe identifiers.",
        )
        ids.add(bid)
        kind = block["kind"]
        require(
            isinstance(kind, str) and kind in {"heading", "paragraph", "quote", "list", "table"},
            "Unsupported document block.",
        )
        require(
            isinstance(block["text"], str) and len(block["text"]) <= 1400,
            "Split long text into shorter blocks (1400 characters).",
        )
        require(
            isinstance(block["items"], list)
            and len(block["items"]) <= 8
            and all(isinstance(x, str) and 0 < len(x) <= 300 for x in block["items"]),
            "Lists support up to eight short items.",
        )
        rows = block["rows"]
        require(
            isinstance(rows, list)
            and len(rows) <= 8
            and all(
                isinstance(r, list)
                and 1 <= len(r) <= 5
                and all(isinstance(x, str) and len(x) <= 160 for x in r)
                for r in rows
            ),
            "Tables support up to eight rows and five short columns.",
        )
        if rows:
            require(
                sum(len(x) for r in rows for x in r) <= 1600,
                "Split dense tables into smaller tables (1600 characters).",
            )
            require(all(len(r) == len(rows[0]) for r in rows), "Table rows must have equal width.")
        require(
            bool(block["items"])
            if kind == "list"
            else bool(rows)
            if kind == "table"
            else bool(block["text"].strip()),
            "Document block is empty.",
        )
        require(
            (kind == "list" or not block["items"]) and (kind == "table" or not rows),
            "Unused block fields must be empty.",
        )
        require(
            isinstance(block["evidence_ids"], list)
            and all(isinstance(x, str) and (refs is None or x in refs) for x in block["evidence_ids"]),
            "Block cites unavailable evidence.",
        )
    return copy.deepcopy(document)


def render_document(document, evidence=None):
    document = checked(document, evidence)
    chunks = [f'<h1 id="title">{escape(document["title"])}</h1>']
    if document["subtitle"]:
        chunks.append(f'<p id="subtitle" class="subtitle">{escape(document["subtitle"])}</p>')
    for b in document["blocks"]:
        text, bid = escape(b["text"]), b["id"]
        if b["kind"] == "list":
            body = (
                (f"<p>{text}</p>" if text else "")
                + "<ul>"
                + "".join(f"<li>{escape(x)}</li>" for x in b["items"])
                + "</ul>"
            )
            tag = "section"
        elif b["kind"] == "table":
            body = (f"<caption>{text}</caption>" if text else "") + "".join(
                "<tr>"
                + "".join(
                    f"<{'th' if i == 0 else 'td'}>{escape(x)}</{'th' if i == 0 else 'td'}>" for x in row
                )
                + "</tr>"
                for i, row in enumerate(b["rows"])
            )
            tag = "table"
        else:
            tag = {"heading": "h2", "paragraph": "p", "quote": "blockquote"}[b["kind"]]
            body = text
        # Citation markers are artifact content. Review annotations never enter this renderer.
        if b["evidence_ids"]:
            citation = (
                '<small class="citations"> [' + ", ".join(escape(x) for x in b["evidence_ids"]) + "]</small>"
            )
            if tag != "table":
                body += citation
        if tag == "table":
            body = "<table>" + body + "</table>" + ("<p>" + citation + "</p>" if b["evidence_ids"] else "")
            tag = "section"
        chunks.append(
            f'<{tag} id="{bid}" data-evidence="{escape(",".join(b["evidence_ids"]))}">{body}</{tag}>'
        )
    if evidence:
        used = {x for b in document["blocks"] for x in b["evidence_ids"]}
        chunks.append('<h2 id="source-references">Source references</h2>')
        groups = {}
        for fact in evidence:
            if fact["id"] in used:
                groups.setdefault(fact["source_id"], []).append(fact["id"])
        for i, (source, ids) in enumerate(groups.items()):
            chunks.append(
                f'<p id="reference-{i}" class="source-reference">{escape(source)} — [{escape(", ".join(ids))}]</p>'
            )
    css = files("amplifier_smart_tool_stories").joinpath("resources/document.css").read_text()
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>'
        + escape(document["title"])
        + "</title><style>"
        + css
        + '</style></head><body><article class="stories-document" id="document">'
        + "".join(chunks)
        + "</article></body></html>"
    )
