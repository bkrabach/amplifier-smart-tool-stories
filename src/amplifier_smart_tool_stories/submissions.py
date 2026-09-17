"""Native internal submission schemas; not public or side-effecting tools."""

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
    }
)
COMPOSITION = obj(
    {
        "action": {"type": "string", "enum": ["answer", "clarify", "revise"]},
        "message": TEXT,
        "html": TEXT,
        "limitations": TEXTS,
    }
)
SECTION = obj({"status": {"type": "string", "enum": ["passed", "failed"]}, "findings": TEXTS})
REVIEW = obj({"semantic": SECTION, "visual": SECTION, "warnings": TEXTS})

GENERATION = obj({**COMPOSITION["properties"], "action": {"type": "string", "enum": ["revise", "clarify"]}})
REPAIR = obj({**COMPOSITION["properties"], "action": {"type": "string", "enum": ["revise"]}})
