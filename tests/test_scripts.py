"""Script retention, provider separation, bounded review and exact audio inputs."""

import asyncio
import copy

import pytest

from amplifier_smart_tool_stories import Stories, StoriesError
from amplifier_smart_tool_stories.script_intelligence import prepare
from amplifier_smart_tool_stories.speech import wav

HTML = '<html><body><section class="slide"><h1>A concrete change</h1><aside class="notes" style="display:none">Ask the audience about editing.</aside></section><section class="slide"><h1>Review before delivery</h1></section></body></html>'


def candidate():
    return {
        "throughline": "Make the result inspectable.",
        "slides": [
            {"slide": 1, "text": "A useful result needs room for judgment.", "references": ["slide:1"]},
            {
                "slide": 2,
                "text": "That is where review comes in: inspect the result before delivery.",
                "references": ["slide:2"],
            },
        ],
        "limitations": ["Imported slide claims are not independently verified."],
    }


def setup(tmp_path, **kwargs):
    api = Stories(tmp_path, **kwargs)
    r = api.create_story("Review", HTML, "create")
    return api, r


def test_prepare_refine_retain_and_speech_separation(tmp_path, monkeypatch):
    calls = []

    def write(story, op):
        calls.append(op)
        result = candidate()
        if op.get("base_script"):
            result["slides"][0]["text"] = "Start with the result, and leave room to improve it."
        return result

    api, r = setup(tmp_path, intelligence=write, execution="in_process", provider="anthropic")
    receipt = api.prepare_narration(r["story_id"], r["revision_id"], {}, "prepare")
    assert api.prepare_narration(r["story_id"], r["revision_id"], {}, "prepare") == receipt
    op = api.get_operation(receipt["operation_id"])
    sid = op["result"]["script_id"]
    first = api.get_narration_script(r["story_id"], sid)
    assert first["origin"] == "model" and len(calls) == 1
    assert api.narration_settings()["effective"] is None
    assert api.get_revision(r["story_id"], r["revision_id"])["html"] == HTML
    assert api.get_speaker_notes(r["story_id"], r["revision_id"])["notes"][0].startswith("Ask the audience")
    rec = api.prepare_narration(
        r["story_id"],
        r["revision_id"],
        {},
        "refine",
        guidance="Make the opening direct.",
        base_script_id=sid,
        target_seconds=30,
    )
    refined = api.get_narration_script(
        r["story_id"], api.get_operation(rec["operation_id"])["result"]["script_id"]
    )
    assert refined["base_script_id"] == sid
    assert calls[-1]["provider"]["provider"] == "anthropic"
    assert calls[-1]["base_script"]["sha256"] == first["sha256"]
    assert api.get_narration_script(r["story_id"], sid) == first
    assert len(api.list_narration_scripts(r["story_id"])["scripts"]) == 2
    spoken = []

    async def speak(text, config, timeout):
        spoken.append(text)
        return wav(b"\0\0" * 2400)

    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setattr("amplifier_smart_tool_stories.speech.synthesize", speak)
    api.model_env = True
    api.configure_narration("openai", "speech-config")
    n = api.generate_narration(r["story_id"], r["revision_id"], {}, "speech", script_id=refined["id"])
    retained = api.get_narration(r["story_id"], n["narration_id"])
    assert retained["script_sha256"] == refined["sha256"]
    assert retained["notes_origin"] == "retained_script"
    assert spoken == [s["text"] for s in refined["slides"]]


def test_edits_invalidate_review_and_bad_scope_fails(tmp_path):
    api, r = setup(
        tmp_path,
        intelligence=lambda *_: {**candidate(), "review": {"method": "model_review"}},
        execution="in_process",
    )
    rec = api.prepare_narration(r["story_id"], r["revision_id"], {}, "prepare")
    sid = api.get_operation(rec["operation_id"])["result"]["script_id"]
    saved = api.save_narration_script(
        r["story_id"], r["revision_id"], ["A changed opening.", "A closing."], "edit", base_script_id=sid
    )
    assert api.get_narration_script(r["story_id"], saved["script_id"])["review"]["method"] == "not_performed"
    other = api.create_story("Other", HTML, "other")
    with pytest.raises(StoriesError):
        api.prepare_narration(other["story_id"], other["revision_id"], {}, "wrong", base_script_id=sid)
    with pytest.raises(StoriesError):
        api.generate_narration(
            r["story_id"], r["revision_id"], {}, "ambiguous", notes=["a", "b"], script_id=sid
        )
    with pytest.raises(StoriesError):
        api.save_narration_script(r["story_id"], r["revision_id"], ["Incomplete"], "invalid")


def test_no_authority_cancel_and_late_result(tmp_path):
    api, r = setup(tmp_path, execution="in_process")
    rec = api.prepare_narration(r["story_id"], r["revision_id"], {}, "no-authority")
    assert api.get_operation(rec["operation_id"])["error"]["code"] == "model_access_required"

    def cancelled(story, op):
        api.cancel_operation(op["id"])
        return candidate()

    api.intelligence = cancelled
    rec = api.prepare_narration(r["story_id"], r["revision_id"], {}, "late")
    assert api.get_operation(rec["operation_id"])["state"] == "cancelled"
    assert not api.list_narration_scripts(r["story_id"])["scripts"]


def test_invalid_refs_cannot_commit(tmp_path):
    result = candidate()
    result["slides"][0]["references"] = ["source:invented"]
    api, r = setup(tmp_path, intelligence=lambda *_: result, execution="in_process")
    rec = api.prepare_narration(r["story_id"], r["revision_id"], {}, "invalid")
    assert api.get_operation(rec["operation_id"])["state"] == "failed"
    assert not api.list_narration_scripts(r["story_id"])["scripts"]


def test_bounded_story_review_and_repair(tmp_path):
    api, r = setup(tmp_path)
    with api.store.transaction() as db:
        story = api.store.get(db, "stories", r["story_id"])
    op = {"revision_id": r["revision_id"], "guidance": "Explain why it matters.", "target_seconds": 40}
    calls = []

    async def ask(instruction, payload, schema):
        calls.append((instruction, copy.deepcopy(payload)))
        if len(calls) % 2:
            return candidate()
        return {
            "source_fidelity": {"status": "passed", "findings": []},
            "spoken_story": {
                "status": "failed" if len(calls) == 2 else "passed",
                "findings": ["Opening recites the title."] if len(calls) == 2 else [],
            },
        }

    result = asyncio.run(prepare(story, op, ask))
    assert len(calls) == 4 and result["review"]["method"] == "model_review"
    assert len(result["review"]["attempts"]) == 2
    assert calls[0][1]["slides"][0]["speaker_notes"].startswith("Ask the audience")
    assert "Ask the audience" not in calls[0][1]["slides"][0]["text"]

    async def fail(instruction, payload, schema):
        if "throughline" in schema["properties"]:
            return candidate()
        return {
            "source_fidelity": {"status": "failed", "findings": ["Unsupported outcome."]},
            "spoken_story": {"status": "passed", "findings": []},
        }

    with pytest.raises(StoriesError) as exc:
        asyncio.run(prepare(story, op, fail))
    assert exc.value.code == "script_review_failed" and len(exc.value.candidate["reviews"]) == 2


def test_pending_drafts_and_provider_are_snapshotted(tmp_path):
    captured = []

    def write(story, op):
        captured.append(op)
        return candidate()

    api, r = setup(tmp_path, intelligence=write, provider="anthropic")
    rec = api.prepare_narration(
        r["story_id"], r["revision_id"], {}, "draft", draft_notes=["Use this opening.", ""]
    )
    api.configure_provider("gemini")
    api.run_operation(rec["operation_id"])
    assert captured[0]["draft_notes"] == ["Use this opening.", ""]
    assert captured[0]["provider"]["provider"] == "anthropic"
