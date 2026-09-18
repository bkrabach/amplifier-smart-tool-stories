"""Native internal submission schemas; not public or side-effecting tools."""

from .expertise import catalog

TEXT = {"type": "string"}
TEXTS = {"type": "array", "items": TEXT}


def obj(properties):
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


EVIDENCE = obj(
    {
        "evidence": {
            "type": "array",
            "items": obj({"id": TEXT, "excerpt_id": TEXT, "claim": TEXT}),
        },
        "limitations": TEXTS,
        "plan": TEXT,
        "expertise": {
            "type": "array",
            "minItems": 1,
            "maxItems": 2,
            "items": {"type": "string", "enum": [r["id"] for r in catalog()]},
        },
    }
)
CHANGES = obj({"summary": TEXT, "material_changes": TEXTS, "omissions": TEXTS, "assumptions": TEXTS})
CALCULATIONS = {
    "type": "array",
    "items": obj(
        {
            "id": TEXT,
            "operation": {
                "type": "string",
                "enum": ["sum", "difference", "product", "ratio", "percent_change"],
            },
            "inputs": {"type": "array", "items": obj({"evidence_id": TEXT, "value": TEXT})},
            "result": TEXT,
            "decimal_places": {"type": "integer"},
            "unit": TEXT,
        }
    ),
}
COMPOSITION = obj(
    {
        "action": {"type": "string", "enum": ["answer", "clarify", "revise"]},
        "message": TEXT,
        "changes": CHANGES,
        "calculations": CALCULATIONS,
        "html": TEXT,
        "limitations": TEXTS,
    }
)
SECTION = obj({"status": {"type": "string", "enum": ["passed", "failed"]}, "findings": TEXTS})
REVIEW = obj({"semantic": SECTION, "visual": SECTION, "warnings": TEXTS})

GENERATION = obj({**COMPOSITION["properties"], "action": {"type": "string", "enum": ["revise", "clarify"]}})
REPAIR = obj({**COMPOSITION["properties"], "action": {"type": "string", "enum": ["revise"]}})

DOCUMENT = obj(
    {
        "title": TEXT,
        "subtitle": TEXT,
        "blocks": {
            "type": "array",
            "items": obj(
                {
                    "id": TEXT,
                    "kind": {"type": "string", "enum": ["heading", "paragraph", "quote", "list", "table"]},
                    "text": TEXT,
                    "items": TEXTS,
                    "rows": {"type": "array", "items": TEXTS},
                    "evidence_ids": TEXTS,
                }
            ),
        },
    }
)
DOCUMENT_COMPOSITION = obj(
    {
        "action": COMPOSITION["properties"]["action"],
        "message": TEXT,
        "changes": CHANGES,
        "calculations": CALCULATIONS,
        "document": DOCUMENT,
        "limitations": TEXTS,
    }
)
DOCUMENT_GENERATION = obj(
    {**DOCUMENT_COMPOSITION["properties"], "action": GENERATION["properties"]["action"]}
)
DOCUMENT_REPAIR = obj({**DOCUMENT_COMPOSITION["properties"], "action": REPAIR["properties"]["action"]})

NARRATION_SCRIPT = obj(
    {
        "throughline": TEXT,
        "slides": {
            "type": "array",
            "items": obj({"slide": {"type": "integer"}, "text": TEXT, "references": TEXTS}),
        },
        "limitations": TEXTS,
    }
)
NARRATION_REVIEW = obj({"source_fidelity": SECTION, "spoken_story": SECTION})
