"""Packaged, allowlisted writing guidance selected within evidence planning."""

import hashlib
import json
from importlib.resources import files

from .errors import require


def catalog():
    return json.loads(
        files("amplifier_smart_tool_stories").joinpath("resources/expertise/catalog.json").read_text()
    )


def planning_instruction():
    return (
        "\nSelect one or two expertise IDs for this request (including the latest comment). "
        "Use adaptation when retargeting existing content; pair it with the destination audience. "
        "Use general when no specialist applies. The caller does not route specialists.\n"
        + "\n".join(f"{row['id']}: {row['description']}" for row in catalog())
    )


def load(selected):
    rows = {r["id"]: r for r in catalog()}
    require(
        isinstance(selected, list)
        and 1 <= len(selected) <= 2
        and all(isinstance(s, str) and s in rows for s in selected)
        and len(set(selected)) == len(selected),
        "Evidence planning must select one or two known expertise IDs.",
        "invalid_model_result",
    )
    texts, provenance = [], []
    for key in selected:
        row = rows[key]
        text = (
            files("amplifier_smart_tool_stories").joinpath("resources/expertise", row["resource"]).read_text()
        )
        texts.append(f"\n{row['name']} guidance:\n{text}")
        provenance.append(
            {"id": key, "sha256": hashlib.sha256(text.encode()).hexdigest(), "sources": row["sources"]}
        )
    return "\n".join(texts), provenance
