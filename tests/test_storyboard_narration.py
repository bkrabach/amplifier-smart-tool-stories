"""Offline panel-native speech: exact bytes, provenance, bounds and failure semantics."""

import asyncio
import base64
import copy
import hashlib
import io
import json
import math
import struct
import threading
import wave
import zipfile

import pytest

from amplifier_smart_tool_stories import Stories, StoriesError
from amplifier_smart_tool_stories.quality import render
from amplifier_smart_tool_stories.speech import wav
from amplifier_smart_tool_stories.storyboards import BOARD, checked


def board(count=3):
    return {
        "name": "Panel speech fixture",
        "approach": "An explicitly fictional sequence for offline checks.",
        "tradeoff": "No live voice quality evidence.",
        "panels": [
            {
                "id": f"beat-{i:02}",
                "title": f"Unique title {i:02}",
                "action": f"Not spoken action {i:02}.",
                "visual": "Planned visual",
                "asset_id": "",
                "narration": f"  Exact panel {i:02}: café & <literal>.\nNext line.  ",
                "notes": f"Not spoken production notes {i:02}.",
                "evidence_ids": [],
                "production_requirements": [],
            }
            for i in range(1, count + 1)
        ],
    }


def audio_bytes(text):
    hz = 220 + int(hashlib.sha256(text.encode()).hexdigest()[:4], 16) % 1200
    pcm = b"".join(
        struct.pack("<h", int(10000 * math.sin(2 * math.pi * hz * i / 24000))) for i in range(2400)
    )
    return wav(pcm)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "offline-fixture-not-a-real-key")
    api = Stories(tmp_path / "store", model_env=True, execution="in_process")
    api.configure_narration("openai", "config")
    calls = []

    async def speak(text, config, timeout):
        calls.append((text, config.copy()))
        # Deliberately finish the opening last; clip order must still follow panels.
        await asyncio.sleep(0.025 if "panel 01" in text else 0)
        return audio_bytes(text)

    monkeypatch.setattr("amplifier_smart_tool_stories.speech.synthesize", speak)
    return api, calls, speak


def generate(api, rev, request_id="speech", grant=None, **kwargs):
    return api.generate_narration(
        rev["story_id"],
        rev["revision_id"],
        {} if grant is None else grant,
        request_id,
        source="storyboard_panels",
        **kwargs,
    )


def test_exact_panel_audio_not_sections_and_provenance(setup, tmp_path):
    api, calls, _ = setup
    value = board(9)
    rev = api.create_storyboard("Nine panels", value, "create")
    before = api.get_revision(rev["story_id"], rev["revision_id"])
    receipt = generate(api, rev)
    op = api.get_operation(receipt["operation_id"])
    nar = api.get_narration(rev["story_id"], receipt["narration_id"])
    assert op["state"] == "succeeded" and op["requests_used"] == 9
    assert op["progress"] == {"completed_panels": 9, "total_panels": 9}
    assert nar["source"] == nar["notes_origin"] == "storyboard_panels"
    assert nar["revision_id"] == rev["revision_id"]
    assert nar["source_sha256"] == before["sha256"]
    assert nar["direction_id"] == rev["direction_id"]
    assert nar["panel_ids"] == [p["id"] for p in value["panels"]]
    assert nar["notes"] == [p["narration"] for p in value["panels"]]
    assert sorted(t for t, _ in calls) == sorted(nar["notes"])
    hashes = []
    for position, panel in enumerate(value["panels"], 1):
        result = api.get_narration_audio(rev["story_id"], nar["id"], panel_id=panel["id"])
        data = base64.b64decode(result["data_base64"])
        assert data == audio_bytes(panel["narration"])
        digest = hashlib.sha256(data).hexdigest()
        hashes.append(digest)
        assert result["audio"]["sha256"] == result["clip"]["sha256"] == digest
        assert result["audio"]["text"] == panel["narration"]
        assert result["source_sha256"] == before["sha256"]
        assert result["revision_id"] == rev["revision_id"]
        assert result["clip"]["panel_id"] == panel["id"]
        assert result["clip"]["position"] == position and "slide" not in result["clip"]
        with wave.open(io.BytesIO(data)) as w:
            assert (w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()) == (
                24000,
                1,
                2,
                2400,
            )
            assert len(w.readframes(w.getnframes())) == 4800
        assert result["audio"]["duration_seconds"] == 0.1
        (tmp_path / f"{panel['id']}.wav").write_bytes(data)
    assert len(set(hashes)) == 9
    (tmp_path / "narration-evidence.json").write_text(
        json.dumps({"narration": nar, "wav_hashes": hashes}, indent=2)
    )
    assert api.get_revision(rev["story_id"], rev["revision_id"]) == before
    assert generate(api, rev) == receipt and len(calls) == 9
    with pytest.raises(StoriesError, match="panel_id"):
        api.get_narration_audio(rev["story_id"], nar["id"], slide=1)
    with pytest.raises(StoriesError):
        api.get_narration_audio(rev["story_id"], nar["id"], panel_id="unknown")
    with pytest.raises(StoriesError, match="presentation narration"):
        api.export_video(
            rev["story_id"], rev["revision_id"], str(tmp_path / "not-a-deck.mp4"), narration_id=nar["id"]
        )
    assert not (tmp_path / "not-a-deck.mp4").exists()


def test_reorder_edit_reopen_cache_and_settings_snapshot(setup, monkeypatch):
    api, calls, _ = setup
    value = board()
    rev = api.create_storyboard("Stable IDs", value, "create")
    first = generate(api, rev)
    original = api.get_narration(rev["story_id"], first["narration_id"])
    reordered = copy.deepcopy(value)
    reordered["panels"].reverse()
    next_rev = api.revise_storyboard(rev["story_id"], rev["revision_id"], reordered, "reorder")
    reopened = Stories(api.store.path, execution="in_process", model_env=False)
    monkeypatch.delenv("OPENAI_API_KEY")
    second = generate(reopened, next_rev, "reordered")
    nar = reopened.get_narration(rev["story_id"], second["narration_id"])
    assert reopened.get_operation(second["operation_id"])["requests_used"] == 0
    assert [c["panel_id"] for c in nar["clips"]] == list(reversed(original["panel_ids"]))
    assert [c["position"] for c in nar["clips"]] == [1, 2, 3]
    assert {c["panel_id"]: c["audio_id"] for c in nar["clips"]} == {
        c["panel_id"]: c["audio_id"] for c in original["clips"]
    }
    assert nar["revision_id"] == next_rev["revision_id"] and nar["source_sha256"] != original["source_sha256"]
    assert reopened.get_narration(rev["story_id"], first["narration_id"]) == original
    monkeypatch.setenv("OPENAI_API_KEY", "offline")
    reordered["panels"][1]["narration"] = "Changed exact text."
    edited = api.revise_storyboard(rev["story_id"], next_rev["revision_id"], reordered, "edit")
    api.execution = "queued"
    third = generate(api, edited, "changed", grant={"max_requests": 1})
    api.configure_narration("openai", "voice", model="saved-custom-model", voice="cedar")
    api.run_operation(third["operation_id"])
    assert len(calls) == 4 and calls[-1][0] == "Changed exact text."
    assert calls[-1][1]["model"] == "gpt-4o-mini-tts" and calls[-1][1]["voice"] == "marin"
    api.execution = "in_process"
    fourth = generate(api, edited, "voice-changed")
    assert api.get_operation(fourth["operation_id"])["requests_used"] == 3
    assert calls[-1][1]["model"] == "saved-custom-model" and calls[-1][1]["voice"] == "cedar"


@pytest.mark.parametrize("invalid", ["empty", "whitespace", "notes", "script", "source", "grant"])
def test_invalid_panel_speech_fails_before_spending(setup, invalid):
    api, calls, _ = setup
    value = board()
    if invalid in {"empty", "whitespace"}:
        value["panels"][1]["narration"] = "" if invalid == "empty" else " \n "
    rev = api.create_storyboard("Validation", value, "create")
    kwargs = (
        {"notes": ["override"] * 3}
        if invalid == "notes"
        else {"script_id": "unknown"}
        if invalid == "script"
        else {}
    )
    with pytest.raises(StoriesError) as error:
        if invalid == "source":
            api.generate_narration(rev["story_id"], rev["revision_id"], {}, "wrong-source")
        else:
            generate(api, rev, grant={"max_requests": 1} if invalid == "grant" else None, **kwargs)
    if invalid in {"empty", "whitespace"}:
        assert "beat-02" in str(error.value)
    assert not calls and not api.list_narrations(rev["story_id"])["narrations"]


def test_partial_failure_duplicate_text_and_explicit_uncertain_retry(setup, monkeypatch):
    api, calls, good = setup
    value = board(4)
    value["panels"][3]["narration"] = value["panels"][0]["narration"]
    rev = api.create_storyboard("Partial", value, "create")

    async def fail(text, config, timeout):
        if "panel 02" in text:
            raise RuntimeError("private-key-must-not-leak")
        return await good(text, config, timeout)

    monkeypatch.setattr("amplifier_smart_tool_stories.speech.synthesize", fail)
    rec = generate(api, rev)
    op = api.get_operation(rec["operation_id"])
    nar = api.get_narration(rev["story_id"], rec["narration_id"])
    assert op["state"] == "failed" and op["requests_used"] == 3
    assert op["error"]["code"] == "speech_completion_uncertain"
    assert op["panel_errors"][0]["panel_ids"] == ["beat-02"]
    assert "private-key" not in json.dumps(op)
    assert [c["position"] for c in nar["clips"]] == [1, 3, 4]
    assert [c["panel_id"] for c in nar["clips"]] == ["beat-01", "beat-03", "beat-04"]
    assert nar["clips"][0]["audio_id"] == nar["clips"][2]["audio_id"]
    assert generate(api, rev) == rec and len(calls) == 2
    with pytest.raises(StoriesError, match="not available"):
        api.get_narration_audio(rev["story_id"], nar["id"], panel_id="beat-02")
    monkeypatch.setattr("amplifier_smart_tool_stories.speech.synthesize", good)
    blocked = generate(api, rev, "no-blind-retry")
    assert api.get_operation(blocked["operation_id"])["error"]["code"] == "speech_completion_uncertain"
    recovered = generate(api, rev, "explicit-retry", retry_uncertain=True)
    assert api.get_operation(recovered["operation_id"])["state"] == "succeeded"
    assert api.get_operation(recovered["operation_id"])["requests_used"] == 1
    assert len(calls) == 3


def test_panel_cancel_fences_late_commits_and_exact_retry(setup, monkeypatch):
    api, calls, _ = setup
    rev = api.create_storyboard("Cancel", board(2), "create")
    api.execution = "queued"
    rec = generate(api, rev)
    ready = threading.Event()
    active = stopped = 0

    async def blocked(*args):
        nonlocal active, stopped
        active += 1
        if active == 2:
            ready.set()
        try:
            await asyncio.sleep(60)
        finally:
            stopped += 1

    monkeypatch.setattr("amplifier_smart_tool_stories.speech.synthesize", blocked)
    thread = threading.Thread(target=api.run_operation, args=(rec["operation_id"],))
    thread.start()
    assert ready.wait(3)
    api.cancel_operation(rec["operation_id"])
    thread.join(3)
    assert not thread.is_alive() and stopped == 2
    assert api.get_operation(rec["operation_id"])["state"] == "cancelled"
    assert api.get_narration(rev["story_id"], rec["narration_id"])["clips"] == []
    assert generate(api, rev) == rec
    assert active == 2 and not calls


@pytest.mark.parametrize("failure", ["missing", "corrupt"])
def test_missing_or_corrupt_retained_panel_audio_is_not_success(setup, failure):
    api, _, _ = setup
    rev = api.create_storyboard("Integrity", board(1), "create")
    rec = generate(api, rev)
    nar = api.get_narration(rev["story_id"], rec["narration_id"])
    with api.store.transaction() as db:
        key = nar["clips"][0]["audio_id"]
        if failure == "missing":
            db.execute("DELETE FROM speech_audio WHERE id=?", (key,))
        else:
            db.execute("UPDATE speech_audio SET content=? WHERE id=?", (b"corrupt", key))
    with pytest.raises(StoriesError) as error:
        api.get_narration_audio(rev["story_id"], nar["id"], panel_id="beat-01")
    assert error.value.code == ("missing_asset" if failure == "missing" else "invalid_audio")


@pytest.mark.parametrize("bad", [b"not audio", wav(b"\0\0" * 2400)[:-100]])
def test_invalid_speech_bytes_never_commit_a_panel_clip(setup, monkeypatch, bad):
    api, _, good = setup
    rev = api.create_storyboard("Invalid provider bytes", board(2), "create")

    async def speak(text, config, timeout):
        return bad if "panel 02" in text else await good(text, config, timeout)

    monkeypatch.setattr("amplifier_smart_tool_stories.speech.synthesize", speak)
    rec = generate(api, rev)
    assert api.get_operation(rec["operation_id"])["state"] == "failed"
    nar = api.get_narration(rev["story_id"], rec["narration_id"])
    assert [c["panel_id"] for c in nar["clips"]] == ["beat-01"]
    with pytest.raises(StoriesError):
        api.get_narration_audio(rev["story_id"], nar["id"], panel_id="beat-02")


@pytest.mark.parametrize("count", [1, 8, 9, 33, 70])
def test_panel_count_schema_preview_export_and_speech(setup, count, tmp_path):
    import jsonschema

    api, calls, _ = setup
    value = board(count)
    assert "maxItems" not in BOARD["properties"]["panels"]
    jsonschema.validate(value, BOARD)
    assert checked(value) == value
    rev = api.create_storyboard("Bounded board", value, "create")
    sid, rid = rev["story_id"], rev["revision_id"]
    if count > 12:
        with pytest.raises(StoriesError, match="exceeds"):
            generate(api, rev, "default-grant-too-small", grant={})
        assert not calls
    rec = generate(api, rev, grant={"max_requests": count})
    assert api.get_operation(rec["operation_id"])["state"] == "succeeded"
    assert len(calls) == count
    assert generate(api, rev, grant={"max_requests": count}) == rec
    assert len(calls) == count
    narration = api.get_narration(sid, rec["narration_id"])
    assert narration["panel_ids"] == [p["id"] for p in value["panels"]]
    assert len(narration["clips"]) == count
    for panel in value["panels"]:
        audio = api.get_narration_audio(sid, rec["narration_id"], panel_id=panel["id"])
        assert base64.b64decode(audio["data_base64"]) == audio_bytes(panel["narration"])
    preview = api.get_preview(sid, rid)
    assert api.get_comparison(sid, [rid])["items"][0]["preview"] == preview
    for panel in value["panels"]:
        assert panel["title"] in preview["html"]
        assert any(e["text"] == panel["title"] for e in preview["elements"])
    anchor = {"kind": "element", "element": f"d-panel-beat-{count:02}-title"}
    view = api.get_review_view(sid)
    selected = api.update_review_view(sid, view["version"], "last-panel-review", anchor=anchor)
    assert selected["anchor"]["element"] == anchor["element"]
    assert selected["anchor"]["quote"] == value["panels"][-1]["title"]
    exported = api.get_export(sid, rid, "zip")
    data = base64.b64decode(exported["data_base64"])
    (tmp_path / f"board-{count}.zip").write_bytes(data)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert json.loads(z.read("storyboard.json"))["storyboard"] == value
        html = z.read("index.html").decode()
        assert html.count('class="storyboard-panel"') == count
        for panel in value["panels"]:
            assert panel["title"] in html
    # The public render/review subprocess must inspect all sheets, not just eight.
    if count > 32:
        rendered = asyncio.run(render(api.get_revision(sid, rid)["html"], 40, include_pdf=True))
        assert rendered["page_count"] == len(rendered["images"]) == count + 1
        assert not rendered["findings"]
        for panel in value["panels"]:
            assert panel["title"] in rendered["rendered_text"]
        (tmp_path / f"{count}-panel-review.pdf").write_bytes(base64.b64decode(rendered["pdf"]))
        (tmp_path / "narration-evidence.json").write_text(json.dumps(narration, indent=2))
        (tmp_path / "render-evidence.json").write_text(
            json.dumps(
                {
                    "page_count": rendered["page_count"],
                    "findings": rendered["findings"],
                    "page_hashes": [image["sha256"] for image in rendered["images"]],
                    "rendered_text": rendered["rendered_text"],
                },
                indent=2,
            )
        )


def test_empty_panels_rejected(tmp_path):
    import jsonschema

    value = board(0)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(value, BOARD)
    with pytest.raises(StoriesError, match="at least one"):
        Stories(tmp_path).create_storyboard("Invalid count", value, "create")


def test_speech_grant_is_not_a_panel_count_ceiling(setup):
    api, calls, _ = setup
    value = board(130)
    text = value["panels"][0]["narration"]
    for panel in value["panels"]:
        panel["narration"] = text
    rev = api.create_storyboard("More panels than maximum request grant", value, "create")
    rec = generate(api, rev, grant={"max_requests": 1})
    op = api.get_operation(rec["operation_id"])
    nar = api.get_narration(rev["story_id"], rec["narration_id"])
    assert op["state"] == "succeeded" and op["requests_used"] == 1
    assert len(calls) == 1 and len(nar["clips"]) == 130
    assert [c["panel_id"] for c in nar["clips"]] == [p["id"] for p in value["panels"]]
    assert len({c["audio_id"] for c in nar["clips"]}) == 1


def test_existing_eight_panel_import_and_revision_retries_survive(setup):
    api, calls, _ = setup
    value = board(8)
    # Older boards omit optional production requirements; no shape migration.
    for panel in value["panels"]:
        panel.pop("production_requirements")
    rev = api.create_storyboard("Old outline", value, "old-create")
    first = api.get_revision(rev["story_id"], rev["revision_id"])
    reordered = copy.deepcopy(value)
    reordered["panels"].reverse()
    edited = api.revise_storyboard(rev["story_id"], rev["revision_id"], reordered, "old-edit")
    reopened = Stories(api.store.path)
    assert reopened.create_storyboard("Old outline", value, "old-create") == rev
    assert reopened.revise_storyboard(rev["story_id"], rev["revision_id"], reordered, "old-edit") == edited
    assert reopened.get_revision(rev["story_id"], rev["revision_id"]) == first
    assert not calls


def test_storyboard_render_resource_budget_fails_without_partial_sheets(monkeypatch):
    from amplifier_smart_tool_stories import render_worker
    from amplifier_smart_tool_stories.storyboards import render_storyboard

    html = render_storyboard(board(1))
    # A one-panel board can exceed a byte budget: the limit is not panel count.
    monkeypatch.setattr(render_worker, "MAX_STORYBOARD_RENDER_BYTES", 1)
    with pytest.raises(StoriesError) as error:
        render_worker.render(html)
    assert error.value.code == "render_resource_limit"
    assert "PDF/JPEG" in error.value.message and "HTML/ZIP" in error.value.remedy
    assert "truncated or merged" in error.value.remedy


def test_storyboard_render_timeout_is_actionable():
    from amplifier_smart_tool_stories.storyboards import render_storyboard

    with pytest.raises(StoriesError) as error:
        asyncio.run(render(render_storyboard(board(1)), 0.001))
    assert error.value.code == "render_timeout"
    assert "wall-time" in error.value.message
    assert "no panels were truncated or merged" in error.value.remedy


@pytest.mark.parametrize("code", ["render_resource_limit", "render_timeout"])
def test_render_exhaustion_preserves_candidate_without_spending_on_rewrite(tmp_path, monkeypatch, code):
    import time

    from test_storyboards import candidate, result

    from amplifier_smart_tool_stories import storyboard_intelligence

    api = Stories(tmp_path)
    receipt = api.generate_storyboard("Content-led", "Explain each beat", "Readers", {}, "generate")
    with api.store.transaction() as db:
        story = api.store.get(db, "stories", receipt["story_id"])
    operation = api.get_operation(receipt["operation_id"])
    operation["deadline"] = time.time() + 60
    proposed = result()
    proposed["candidates"] = [candidate(board(70))]
    answers = [{"evidence": [], "plan": "Keep all beats", "expertise": ["general"]}, proposed]
    calls = []

    async def ask(*args, **kwargs):
        calls.append({"provider": "scripted"})
        return copy.deepcopy(answers.pop(0))

    async def fail(*args, **kwargs):
        raise StoriesError(code, "Resource budget exhausted", "Review retained HTML/ZIP.")

    monkeypatch.setattr(storyboard_intelligence, "render", fail)
    outcome = asyncio.run(storyboard_intelligence.compose(story, operation, ask, calls))
    assert len(calls) == 2 and not answers  # No provider repair to merge/omit panels.
    assert outcome["candidates"] == []
    assert outcome["failures"][0]["code"] == code
    assert outcome["failures"][0]["submission"]["storyboard"] == board(70)
    api.intelligence = lambda story, op: outcome
    assert api.run_operation(operation["id"])["state"] == "failed"
    assert not api.get_story(receipt["story_id"])["revisions"]


def test_real_markup_budget_stops_after_composition_and_retains_full_candidate(tmp_path):
    from test_storyboards import candidate, result

    from amplifier_smart_tool_stories.artifacts import MAX_HTML
    from amplifier_smart_tool_stories.storyboard_intelligence import compose
    from amplifier_smart_tool_stories.storyboards import render_storyboard

    value = board(1400)
    for panel in value["panels"]:
        for field in ("action", "visual", "narration", "notes"):
            panel[field] = "&" * 1200
        panel["production_requirements"] = ["&" * 500] * 4
    assert checked(value) == value
    html = render_storyboard(value)
    markup_bytes = len(html.encode())
    assert MAX_HTML == 32 * 1024 * 1024 and markup_bytes > MAX_HTML
    proposed = result()
    proposed["candidates"] = [candidate(value)]
    answers = [{"evidence": [], "plan": "Retain every beat", "expertise": ["general"]}, proposed]
    calls = []

    async def ask(*args, **kwargs):
        calls.append({"provider": "scripted"})
        assert len(calls) <= 2, "Markup resource exhaustion must not spend on model repair."
        return copy.deepcopy(answers.pop(0))

    # No parser/render/budget mocking: compose -> quality.render -> parse_html
    # must stop at the actual UTF-8 byte threshold before starting the renderer.
    api = Stories(
        tmp_path / "store",
        execution="in_process",
        intelligence=lambda story, op: asyncio.run(compose(story, op, ask, calls)),
    )
    receipt = api.generate_storyboard("Oversized valid sequence", "Keep all beats", "Readers", {}, "generate")
    op = api.get_operation(receipt["operation_id"])
    assert len(calls) == 2 and not answers
    assert op["state"] == "failed", op
    failure = op["result"]["failures"][0]
    assert failure["code"] == "markup_resource_limit"
    assert failure["submission"]["storyboard"] == value
    assert failure["submission"]["html"] == html
    assert "quality_review_failed" not in json.dumps(op)
    reopened = Stories(api.store.path)
    assert reopened.get_operation(op["id"])["result"]["failures"][0] == failure
    assert not reopened.get_story(receipt["story_id"])["revisions"]
    (tmp_path / "markup-budget-evidence.json").write_text(
        json.dumps(
            {
                "panel_count": len(value["panels"]),
                "markup_bytes": markup_bytes,
                "budget_bytes": MAX_HTML,
                "model_calls": len(calls),
                "state": op["state"],
                "failure_code": failure["code"],
                "operation_id": op["id"],
                "sequence_sha256": hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest(),
                "markup_sha256": hashlib.sha256(html.encode()).hexdigest(),
                "retained_sequence_matches": True,
            },
            indent=2,
        )
    )


@pytest.mark.parametrize("value", [None, "", 17, "<html><body></body></html>"])
def test_invalid_markup_is_not_a_resource_failure(value):
    from amplifier_smart_tool_stories.artifacts import parse_html

    with pytest.raises(StoriesError) as error:
        parse_html(value)
    assert error.value.code == "invalid_input"


def test_content_led_generation_reviews_every_panel_and_retains_complete_revision(tmp_path):
    from test_storyboards import candidate, result

    from amplifier_smart_tool_stories.storyboard_intelligence import compose

    proposed = result()
    proposed["candidates"] = [candidate(board(70))]
    answers = [
        {"evidence": [], "plan": "Keep all needed beats", "expertise": ["general"]},
        proposed,
        {
            "semantic": {"status": "passed", "findings": []},
            "visual": {"status": "passed", "findings": []},
            "warnings": [],
        },
    ]
    calls = []

    async def ask(instruction, payload, images=None, schema=None):
        calls.append({"provider": "scripted"})
        if len(calls) == 2:
            panel_schema = schema["properties"]["candidates"]["items"]["properties"]["storyboard"][
                "properties"
            ]["panels"]
            assert panel_schema["minItems"] == 1 and "maxItems" not in panel_schema
        if images:
            assert len(images) == 71
            assert len(payload["candidate"]["storyboard"]["panels"]) == 70
            for panel in board(70)["panels"]:
                assert panel["title"] in payload["rendered_text"]
        return copy.deepcopy(answers.pop(0))

    api = Stories(
        tmp_path,
        execution="in_process",
        intelligence=lambda story, op: asyncio.run(compose(story, op, ask, calls)),
    )
    receipt = api.generate_storyboard("Content-led", "Explain every beat", "Readers", {}, "generate")
    op = api.get_operation(receipt["operation_id"])
    assert op["state"] == "succeeded", op
    assert len(calls) == 3 and not answers
    rev = api.get_revision(receipt["story_id"], op["result"]["revision_id"])
    assert rev["storyboard"] == board(70)
    assert len(rev["quality_review"]["pages"]) == 71
    assert rev["quality_review"]["method"] == "model_review"


def test_model_access_credentials_and_queued_cancellation(setup, monkeypatch):
    api, calls, _ = setup
    rev = api.create_storyboard("Authority", board(1), "create")
    api.model_env = False
    rec = generate(api, rev)
    assert api.get_operation(rec["operation_id"])["error"]["code"] == "model_access_required"
    api.model_env = True
    monkeypatch.delenv("OPENAI_API_KEY")
    rec = generate(api, rev, "no-key")
    assert api.get_operation(rec["operation_id"])["error"]["code"] == "speech_unavailable"
    api.execution = "queued"
    rec = generate(api, rev, "queued-cancel")
    api.cancel_operation(rec["operation_id"])
    api.run_operation(rec["operation_id"])
    assert api.get_operation(rec["operation_id"])["state"] == "cancelled"
    assert not calls


def test_mcp_panel_source_schema_and_exact_audio_resource(setup):
    pytest.importorskip("mcp")
    import anyio
    from mcp import Client

    from amplifier_smart_tool_stories.mcp import create_server

    api, calls, _ = setup
    rev = api.create_storyboard("MCP panels", board(2), "create")

    async def run():
        async with Client(create_server(api)) as client:
            tools = {t.name: t for t in (await client.list_tools()).tools}
            schema = tools["stories_generate_narration"].input_schema
            assert schema["properties"]["source"]["enum"] == ["presentation", "storyboard_panels"]
            args = {
                "story_id": rev["story_id"],
                "revision_id": rev["revision_id"],
                "source": "storyboard_panels",
                "grant": {},
                "request_id": "mcp-speech",
            }
            response = await client.call_tool("stories_generate_narration", args)
            assert not response.is_error
            rec = response.structured_content["result"]
            assert api.get_operation(rec["operation_id"])["state"] == "succeeded"
            again = await client.call_tool("stories_generate_narration", args)
            assert again.structured_content == response.structured_content and len(calls) == 2
            fetched = await client.call_tool(
                "stories_get_narration_audio",
                {
                    "story_id": rev["story_id"],
                    "narration_id": rec["narration_id"],
                    "panel_id": "beat-02",
                },
            )
            assert not fetched.is_error
            payload = fetched.structured_content["result"]
            assert payload["revision_id"] == rev["revision_id"]
            assert payload["resource_uri"].startswith("stories://panel-audio/")
            resource = (await client.read_resource(payload["resource_uri"])).contents[0]
            assert base64.b64decode(resource.blob) == audio_bytes(board(2)["panels"][1]["narration"])

    anyio.run(run)


def test_cli_panel_route_and_packaged_help(setup):
    import subprocess
    import sys

    api, calls, _ = setup
    rev = api.create_storyboard("CLI panels", board(2), "create")
    rec = generate(api, rev)  # Scripted backend only. CLI verifies reuse without provider access.

    def cli(command, args=None):
        command_line = [sys.executable, "-m", "amplifier_smart_tool_stories", "--store", str(api.store.path)]
        command_line += [command, "--help"] if args is None else [command, "--input", json.dumps(args)]
        result = subprocess.run(command_line, text=True, capture_output=True, check=True)
        return result.stdout if args is None else json.loads(result.stdout)

    assert "storyboard_panels" in cli("generate-narration")
    assert "panel_id" in cli("get-narration-audio")
    assert "no fixed panel-count cap" in cli("create-storyboard")
    reused = cli(
        "generate-narration",
        {
            "story_id": rev["story_id"],
            "revision_id": rev["revision_id"],
            "source": "storyboard_panels",
            "grant": {},
            "request_id": "cli-reuse",
        },
    )
    # Default CLI execution is queued: run explicitly, still without model-env.
    completed = cli("run-operation", {"operation_id": reused["operation_id"]})
    assert completed["state"] == "succeeded" and completed["requests_used"] == 0
    result = cli(
        "get-narration-audio",
        {
            "story_id": rev["story_id"],
            "narration_id": reused["narration_id"],
            "panel_id": "beat-02",
        },
    )
    assert base64.b64decode(result["data_base64"]) == audio_bytes(board(2)["panels"][1]["narration"])
    assert len(calls) == 2
    assert rec["narration_id"] != reused["narration_id"]
