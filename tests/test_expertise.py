import pytest

from amplifier_smart_tool_stories import Stories, StoriesError
from amplifier_smart_tool_stories.expertise import catalog, load, planning_instruction


def test_catalog_and_loading_are_bounded_and_packaged(tmp_path):
    api = Stories(tmp_path)
    rows = api.storytelling_capabilities()["approaches"]
    assert len(rows) == 10
    assert len({r["id"] for r in rows}) == 10
    for row in rows:
        text, evidence = load([row["id"]])
        assert row["name"] in text and len(evidence[0]["sha256"]) == 64
        assert row["sources"] == evidence[0]["sources"]
    text, evidence = load(["adaptation", "executive"])
    assert "Technical explanation guidance:" not in text
    assert [e["id"] for e in evidence] == ["adaptation", "executive"]
    assert all(row["description"] in planning_instruction() for row in catalog())


@pytest.mark.parametrize(
    "selection",
    [None, [], ["../review"], ["unknown"], ["general", "general"], ["general", "data", "release"], [{}]],
)
def test_invalid_routing_never_loads_arbitrary_resources(selection):
    with pytest.raises(StoriesError) as exc:
        load(selection)
    assert exc.value.code == "invalid_model_result"


def test_invalid_document_gets_one_structural_repair_then_real_review(monkeypatch):
    import copy
    import json
    import time
    from types import SimpleNamespace

    from amplifier_smart_tool_stories import intelligence

    valid = {
        "title": "A finding",
        "subtitle": "",
        "blocks": [
            {
                "id": "p",
                "kind": "paragraph",
                "text": "A bounded finding.",
                "items": [],
                "rows": [],
                "evidence_ids": [],
            }
        ],
    }
    invalid = copy.deepcopy(valid)
    del invalid["blocks"][0]["rows"]

    class Session:
        coordinator = {"providers": {"p": object()}}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    async def session():
        return Session()

    async def prepared(config):
        return SimpleNamespace(create_session=session)

    answers = [
        {"evidence": [], "expertise": ["technical"], "plan": "Explain"},
        {
            "changes": {
                "summary": "Requested change",
                "material_changes": [],
                "omissions": [],
                "assumptions": [],
            },
            "calculations": [],
            "action": "revise",
            "message": "Draft",
            "document": invalid,
        },
        {
            "changes": {
                "summary": "Requested change",
                "material_changes": [],
                "omissions": [],
                "assumptions": [],
            },
            "calculations": [],
            "action": "revise",
            "message": "Repaired",
            "document": valid,
        },
        {"semantic": {"status": "passed", "findings": []}, "visual": {"status": "passed", "findings": []}},
    ]
    prompts = []

    async def complete(provider, config, messages, *args, **kwargs):
        prompts.append(messages[0]["content"])
        answer = answers.pop(0)
        if "action" in answer:
            answer.setdefault(
                "changes",
                {"summary": "Requested revision", "material_changes": [], "omissions": [], "assumptions": []},
            )
            answer.setdefault("calculations", [])
        return json.dumps(answer), {}

    async def render(html, timeout, media=None):
        return {
            "images": [{"sha256": "a" * 64, "data": "image"}],
            "findings": [],
            "rendered_text": "A finding",
        }

    monkeypatch.setattr(intelligence, "prepared", prepared)
    monkeypatch.setattr(intelligence, "complete", complete)
    monkeypatch.setattr(intelligence, "render", render)
    story = {
        "kind": "document",
        "sources": [],
        "title": "Title",
        "purpose": "Explain",
        "audience": "Developers",
        "revisions": [],
        "annotations": [],
    }
    operation = {
        "kind": "generate",
        "provider": {"provider": "openai"},
        "revision_id": None,
        "annotation_id": None,
        "deadline": time.time() + 20,
        "grant": {"max_output_tokens": 1000},
    }
    result = intelligence.execute(story, operation, lambda: False)
    assert result["quality_review"]["passed"]
    assert result["review_attempts"][0]["stage"] == "document_structure"
    assert result["review_attempts"][0]["visual"] == "not_performed"
    assert result["provenance"]["model_calls"] == 4
    assert "single repair allowance" in prompts[2]
    assert not answers
    answers.extend(
        [
            {"evidence": [], "expertise": ["technical"], "plan": "Explain"},
            {
                "changes": {
                    "summary": "Requested change",
                    "material_changes": [],
                    "omissions": [],
                    "assumptions": [],
                },
                "calculations": [],
                "action": "revise",
                "message": "Draft",
                "document": invalid,
            },
            {
                "changes": {
                    "summary": "Requested change",
                    "material_changes": [],
                    "omissions": [],
                    "assumptions": [],
                },
                "calculations": [],
                "action": "revise",
                "message": "Still invalid",
                "document": invalid,
            },
        ]
    )
    with pytest.raises(StoriesError):
        intelligence.execute(story, operation, lambda: False)
    assert not answers  # No repeated repair loop or imaginary rendered pass.
