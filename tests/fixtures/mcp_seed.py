"""Provider-free retained Stories work for portable-host integration checks."""

import argparse
import base64
import io
import json

from PIL import Image

from amplifier_smart_tool_stories import Stories


def seed(storage):
    api = Stories(storage)
    image = Image.new("RGB", (360, 200), "#d7c9ee")
    for x in range(360):
        for y in range(200):
            image.putpixel((x, y), (80 + x // 3, 70 + y // 2, 150))
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    asset = api.import_media(
        "Retained concept illustration",
        "image/png",
        "mcp-seed-image",
        data_base64=base64.b64encode(stream.getvalue()).decode(),
        attribution="Deterministic test illustration; no image model.",
    )
    asset_id = asset["asset"]["id"]

    def board(name):
        return {
            "name": name,
            "approach": "Follow a fictional request from arrival to completion.",
            "tradeoff": "A concrete journey, with less architectural detail.",
            "panels": [
                {
                    "id": "arrival",
                    "title": "A request arrives",
                    "action": "The team receives a fictional request.",
                    "visual": "A conceptual illustration",
                    "asset_id": asset_id,
                    "narration": "Begin with the need.",
                    "notes": "Conceptual, not observed evidence.",
                    "evidence_ids": [],
                },
                {
                    "id": "handoff",
                    "title": "The next person can act",
                    "action": "Context travels with the request.",
                    "visual": "An unillustrated handoff",
                    "asset_id": "",
                    "narration": "",
                    "notes": "",
                    "evidence_ids": [],
                },
            ],
        }

    first = api.create_storyboard(
        "Portable handoff review",
        board("Follow the request"),
        "mcp-seed-story",
        asset_ids=[asset_id],
        fidelity="mixed",
    )
    second = api.revise_storyboard(
        first["story_id"],
        first["revision_id"],
        board("Reveal the context"),
        "mcp-seed-alternative",
        new_direction=True,
    )
    return {**first, "comparison_revision": second["revision_id"], "asset_id": asset_id}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage", required=True)
    print(json.dumps(seed(parser.parse_args().storage)))
