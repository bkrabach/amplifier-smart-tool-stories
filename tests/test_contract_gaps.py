import copy

import pytest

from amplifier_smart_tool_stories import Stories
from amplifier_smart_tool_stories.accountability import validate_disclosures
from amplifier_smart_tool_stories.artifacts import evidence_checked, selected_evidence, source_excerpts
from amplifier_smart_tool_stories.errors import StoriesError

HTML = "<html><body><h1>A retained story</h1></body></html>"
GRANT = {"max_operations": 1, "timeout_seconds": 60}


def test_initial_question_continuation_is_correlated_and_exactly_once(tmp_path):
    api = Stories(
        tmp_path,
        intelligence=lambda *_: {
            "changes": {
                "summary": "Requested change",
                "material_changes": [],
                "omissions": [],
                "assumptions": [],
            },
            "calculations": [],
            "action": "clarify",
            "message": "Which audience?",
        },
    )
    receipt = api.generate("Brief", "Explain", "Unknown", [{"id": "s", "content": "A fact"}], GRANT, "first")
    op = api.run_operation(receipt["operation_id"])
    assert op["state"] == "needs_input"
    followup = api.answer_question(op["id"], "Team leads", GRANT, "answer")
    assert api.answer_question(op["id"], "Team leads", GRANT, "answer") == followup
    with pytest.raises(StoriesError, match="already answered"):
        api.answer_question(op["id"], "Another audience", GRANT, "another")
    assert api.get_operation(op["id"])["state"] == "continued"
    child = api.get_operation(followup["operation_id"])
    assert child["provider"] == op["provider"]
    assert child["story_id"] == receipt["story_id"]
    assert child["continuation"][0]["answer"] == "Team leads"
    api.run_operation(child["id"])
    second = api.answer_question(child["id"], "Use a technical tone", GRANT, "second-answer")
    assert len(api.get_operation(second["operation_id"])["continuation"]) == 2
    assert len(api.list_stories()) == 1
    api.cancel_operation(second["operation_id"])
    assert api.run_operation(second["operation_id"])["state"] == "cancelled"


def test_source_status_cannot_be_forged_by_extraction():
    sources = Stories._sources(
        [
            {
                "id": "s",
                "content": "Reported result: 10 seconds.",
                "kind": "summary",
                "attribution": "Caller notes; original report unavailable",
            }
        ]
    )
    catalog, index = source_excerpts(sources)
    assert catalog[0]["kind"] == "summary"
    evidence = selected_evidence(
        [{"id": "f", "excerpt_id": "s0-p0", "claim": "Caller reports 10 seconds"}], index, sources
    )
    evidence[0]["source_kind"] = "source"
    assert evidence_checked(evidence, sources)[0]["source_kind"] == "summary"
    assert evidence[0]["attribution"] == sources[0]["attribution"]
    with pytest.raises(StoriesError):
        Stories._sources([{"id": "s", "content": "x", "kind": "verified"}])


def calculation_result():
    return {
        "action": "revise",
        "changes": {
            "summary": "Shortened the introduction",
            "material_changes": ["Shortened introduction"],
            "omissions": [],
            "assumptions": [],
        },
        "evidence": [{"id": "f", "quote": "Duration changed from 10 to 8 seconds."}],
        "calculations": [
            {
                "id": "c",
                "operation": "percent_change",
                "inputs": [{"evidence_id": "f", "value": "10"}, {"evidence_id": "f", "value": "8"}],
                "result": "-20",
                "decimal_places": 0,
                "unit": "%",
            }
        ],
    }


def test_calculation_requires_supported_inputs_and_correct_arithmetic():
    result = calculation_result()
    validate_disclosures(result, {}, {"revision_id": "r"})
    assert result["calculations"][0]["verification"].startswith("passed:")
    for field, value in [("result", "20"), ("operation", "eval"), ("decimal_places", 1000)]:
        bad = calculation_result()
        bad["calculations"][0][field] = value
        with pytest.raises(StoriesError):
            validate_disclosures(bad, {}, {})
    bad = calculation_result()
    bad["calculations"][0]["inputs"][0]["value"] = "1"
    with pytest.raises(StoriesError, match="not present"):
        validate_disclosures(bad, {}, {})
    bad = calculation_result()
    del bad["changes"]["omissions"]
    with pytest.raises(StoriesError):
        validate_disclosures(bad, {}, {})


def test_acceptance_is_revision_specific_does_not_change_artifact_or_checks(tmp_path):
    api = Stories(tmp_path)
    first = api.create_story("Story", HTML, "import")
    before = copy.deepcopy(api.get_revision(first["story_id"], first["revision_id"]))
    receipt = api.accept_revision(first["story_id"], first["revision_id"], "accept")
    assert api.accept_revision(first["story_id"], first["revision_id"], "accept") == receipt
    assert api.get_revision(first["story_id"], first["revision_id"]) == before
    fresh = Stories(tmp_path)
    assert fresh.get_story(first["story_id"])["acceptances"] == [receipt["acceptance"]]
    assert fresh.read_changes(first["story_id"])["changes"][-1]["kind"] == "revision_accepted"
    with pytest.raises(StoriesError):
        api.accept_revision(first["story_id"], "wrong", "wrong-accept")


def test_missing_disclosures_fail_even_with_an_injected_adapter(tmp_path):
    api = Stories(tmp_path, intelligence=lambda *_: {"action": "clarify", "message": "Which audience?"})
    r = api.generate("Brief", "Explain", "Reader", [{"id": "s", "content": "Fact"}], GRANT, "first")
    assert api.run_operation(r["operation_id"])["state"] == "failed"
    assert api.get_story(r["story_id"])["revisions"] == []


def test_unclassified_source_keeps_legacy_retry_fingerprint():
    from amplifier_smart_tool_stories.artifacts import digest

    assert Stories._sources([{"id": "s", "content": "Fact"}]) == [
        {"id": "s", "name": "s", "content": "Fact", "sha256": digest("Fact")}
    ]


def test_calculation_disclosure_is_bound_to_review():
    from amplifier_smart_tool_stories.accountability import disclosure_hash

    result = calculation_result()
    original = disclosure_hash(result)
    result["changes"]["omissions"].append("Removed a measurement caveat")
    assert disclosure_hash(result) != original
