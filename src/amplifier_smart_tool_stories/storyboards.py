"""Structured storyboard validation and deterministic rendering."""

import copy
import json
import re
from html import escape
from importlib.resources import files

from .errors import require
from .submissions import TEXT, TEXTS, obj

BRIEF = obj({"intent": TEXT, "assumptions": TEXTS, "open_questions": TEXTS})
PANEL = obj(
    {
        "id": TEXT,
        "title": TEXT,
        "action": TEXT,
        "visual": TEXT,
        "asset_id": TEXT,
        "narration": TEXT,
        "notes": TEXT,
        "evidence_ids": TEXTS,
        "production_requirements": {"type": "array", "items": TEXT, "maxItems": 4},
    }
)
BOARD = obj(
    {
        "name": TEXT,
        "approach": TEXT,
        "tradeoff": TEXT,
        "panels": {"type": "array", "items": PANEL, "minItems": 1, "maxItems": 8},
    }
)


def text(value, label, maximum=2000, nonempty=False):
    require(
        isinstance(value, str) and len(value) <= maximum and (not nonempty or bool(value.strip())),
        f"Invalid {label}.",
    )


def checked_brief(brief):
    require(
        isinstance(brief, dict) and set(brief) == set(BRIEF["properties"]),
        "Brief requires intent, assumptions and open_questions.",
    )
    text(brief["intent"], "brief intent", 10000, True)
    for field in ("assumptions", "open_questions"):
        require(isinstance(brief[field], list) and len(brief[field]) <= 20, f"Invalid {field}.")
        for entry in brief[field]:
            text(entry, field, 1000, True)
    return copy.deepcopy(brief)


def checked(board, evidence=None, assets=None, fidelity="mixed"):
    require(
        isinstance(board, dict) and set(board) == set(BOARD["properties"]),
        "Storyboard requires name, approach, tradeoff and panels.",
    )
    for field in ("name", "approach", "tradeoff"):
        text(board[field], field, 500, field != "tradeoff")
    require(fidelity in {"outline", "mixed", "illustrated"}, "Choose outline, mixed or illustrated fidelity.")
    panels = board["panels"]
    require(isinstance(panels, list) and 1 <= len(panels) <= 8, "Supply 1–8 panels per direction.")
    ids = set()
    refs = None if evidence is None else {e["id"] for e in evidence}
    media = None if assets is None else {a["id"]: a for a in assets}
    for panel in panels:
        require(
            isinstance(panel, dict)
            and set(PANEL["properties"]) - {"production_requirements"} <= set(panel)
            and set(panel) <= set(PANEL["properties"]),
            "Panels require id, title, action, visual, asset_id, narration, notes and evidence_ids.",
        )
        requirements = panel.get("production_requirements", [])
        require(
            isinstance(requirements, list) and len(requirements) <= 4,
            "Supply at most four production requirements per panel.",
        )
        for requirement in requirements:
            text(requirement, "production requirement", 500, True)
        pid = panel["id"]
        require(
            isinstance(pid, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,47}", pid) and pid not in ids,
            "Panel IDs must be unique safe identifiers.",
        )
        ids.add(pid)
        for field in ("title", "action", "visual", "asset_id", "narration", "notes"):
            text(
                panel[field],
                field,
                500 if field in {"title", "asset_id"} else 1200,
                field in {"title", "action"},
            )
        aid = panel["asset_id"]
        require(not aid or media is None or aid in media, "Panel refers to an unavailable asset.")
        require(
            not aid or media is None or media[aid]["mime_type"].startswith("image/"),
            "Storyboard panels support still image assets; describe planned video in notes.",
        )
        require(
            not aid or media is None or media[aid].get("frames", 1) == 1,
            "Storyboard panel images must be still images.",
        )
        require(
            fidelity != "illustrated" or bool(aid),
            "Illustrated delivery requires an image for every panel; supply images or request mixed/outline.",
        )
        require(
            isinstance(panel["evidence_ids"], list)
            and len(panel["evidence_ids"]) <= 12
            and all(isinstance(r, str) and (refs is None or r in refs) for r in panel["evidence_ids"]),
            "Panel cites unavailable evidence.",
        )
    return copy.deepcopy(board)


def render_storyboard(board, evidence=None, assets=None, fidelity="mixed"):
    board = checked(board, evidence, assets, fidelity)
    chunks = []
    for index, panel in enumerate(board["panels"]):
        pid = "panel-" + panel["id"]
        image = (
            f'<img src="asset:{escape(panel["asset_id"], quote=True)}" '
            f'alt="{escape(panel["visual"] or panel["title"], quote=True)}">'
            if panel["asset_id"]
            else '<div class="planned">'
            + ("Planned visual" if panel["visual"] else "Outline · no image")
            + "</div>"
        )
        fields = [
            ("Action", "action"),
            ("Visual intent", "visual"),
            ("Narration / dialogue", "narration"),
            ("Production notes", "notes"),
        ]
        details = "".join(
            f'<div id="{pid}-{key}-block"><strong>{label}</strong><p id="{pid}-{key}">{escape(panel[key])}</p></div>'
            for label, key in fields
            if panel[key]
        )
        if panel.get("production_requirements"):
            details += '<div class="production-requirements"><strong>Production requirements</strong>'
            details += "".join(
                f'<p id="{pid}-requirement-{i + 1}">{i + 1}. {escape(requirement)}</p>'
                for i, requirement in enumerate(panel["production_requirements"])
            )
            details += "</div>"
        if panel["evidence_ids"]:
            details += (
                f'<p id="{pid}-evidence" class="references">Evidence: '
                + escape(", ".join(panel["evidence_ids"]))
                + "</p>"
            )
        if index == 0:
            details += (
                '<div><strong>Direction</strong><p id="direction-approach">'
                + escape(board["approach"])
                + "</p>"
            )
            if board["tradeoff"]:
                details += '<p id="direction-tradeoff">Tradeoff: ' + escape(board["tradeoff"]) + "</p>"
            details += "</div>"
        chunks.append(
            f'<section class="storyboard-panel" id="{pid}">'
            f'<p id="{pid}-position" class="eyebrow">{index + 1} / {len(board["panels"])} · {escape(board["name"])}</p>'
            f'<h2 id="{pid}-title">{escape(panel["title"])}</h2>'
            f'<div class="visual">{image}</div><div class="panel-copy">{details}</div></section>'
        )
    css = files("amplifier_smart_tool_stories").joinpath("resources/storyboard.css").read_text()
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>'
        + escape(board["name"])
        + "</title><style>"
        + css
        + "</style></head><body>"
        '<article class="stories-document stories-storyboard" id="storyboard">'
        + "".join(chunks)
        + "</article></body></html>"
    )


def decode_containers(value, schema):
    """Decode provider-encoded JSON containers only where the schema requires them.

    This does not coerce text/scalars or repair invalid content. Normal domain
    validation still applies after decoding, including limits and allowed fields.
    """
    kind = schema.get("type")
    if isinstance(value, str) and kind in {"object", "array"}:
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return value
    if kind == "object" and isinstance(value, dict):
        properties = schema.get("properties", {})
        return {k: decode_containers(v, properties.get(k, {})) for k, v in value.items()}
    if kind == "array" and isinstance(value, list):
        return [decode_containers(v, schema.get("items", {})) for v in value]
    return value
