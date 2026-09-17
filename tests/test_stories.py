import concurrent.futures
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from amplifier_smart_tool_stories import Stories, StoriesError

HTML = '<html><head><style>p{color:red}</style></head><body><section class="slide"><h1>Evidence</h1><p>Median duration fell from 10 seconds to 8 seconds.</p></section><section class="slide"><h2>Limits</h2><p>One benchmark only.</p></section></body></html>'
SOURCE = {"id": "s1", "content": "Median duration fell from 10 seconds to 8 seconds. One benchmark only."}


@pytest.fixture
def api(tmp_path):
    return Stories(tmp_path / "state")


def imported(api):
    return api.create_story("Evidence", HTML, "import", [SOURCE])


def test_import_anchor_export_and_retry(api, tmp_path):
    r = imported(api)
    assert imported(api) == r
    with pytest.raises(StoriesError, match="different input"):
        api.create_story("changed", HTML, "import")
    sid, rid = r["story_id"], r["revision_id"]
    element = next(e for e in api.get_preview(sid, rid)["elements"] if e["tag"] == "p")
    text = element["text"]
    anchor = {"kind": "text", "element": element["element"], "start": 0, "end": 15, "quote": text[:15]}
    note = api.add_comment(sid, rid, "Check benchmark scope", "note", anchor, "agent")
    assert note["operation_id"] is None
    with pytest.raises(StoriesError, match="quote"):
        api.add_comment(sid, rid, "bad", "bad", {**anchor, "quote": "invented"})
    output = tmp_path / "export.html"
    api.export(sid, rid, str(output))
    assert output.read_text() == HTML
    with pytest.raises(StoriesError):
        api.export(sid, rid, str(output))
    assert api.get_story(sid)["annotations"][0]["anchor"] == anchor
    assert api.read_changes(sid)["changes"]


def test_drafts_never_execute_and_order(api):
    r = imported(api)
    args = (r["story_id"], r["revision_id"], "editor1")
    assert api.save_draft(*args, 2, "new")["status"] == "saved"
    assert api.save_draft(*args, 1, "old")["status"] == "stale"
    assert api.get_story(r["story_id"])["drafts"]["editor1"]["text"] == "new"
    assert api.get_story(r["story_id"])["annotations"] == []


def test_model_free_comment_and_bounded_authority(api):
    r = imported(api)
    sid, rid = r["story_id"], r["revision_id"]
    assert api.add_comment(sid, rid, "Question", "q")["status"] == "awaiting_authority"
    api.grant_feedback(sid, {"max_operations": 1}, "grant")
    receipt = api.add_comment(sid, rid, "What changed?", "q2")
    assert receipt == api.add_comment(sid, rid, "What changed?", "q2")
    assert api.add_comment(sid, rid, "Another?", "q3")["status"] == "awaiting_authority"
    result = api.run_operation(receipt["operation_id"])
    assert result["state"] == "failed"
    assert result["error"]["code"] == "model_access_required"
    assert api.run_operation(receipt["operation_id"]) == result


def test_concurrent_retries_only_one_operation(api):
    r = imported(api)
    sid, rid = r["story_id"], r["revision_id"]
    api.grant_feedback(sid, {"max_operations": 4}, "grant")
    with concurrent.futures.ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: api.add_comment(sid, rid, "Why?", "same"), range(8)))
    assert len({x["operation_id"] for x in results}) == 1
    assert api.get_story(sid)["feedback_grant"]["used"] == 1


def test_revision_from_exact_base_and_honest_checks(api):
    r = imported(api)
    sid, rid = r["story_id"], r["revision_id"]
    api.grant_feedback(sid, {}, "grant")
    note = api.add_comment(sid, rid, "Shorten title", "edit")
    api.intelligence = lambda story, op: {
        "changes": {
            "summary": "Requested change",
            "material_changes": [],
            "omissions": [],
            "assumptions": [],
        },
        "calculations": [],
        "action": "revise",
        "message": "Shortened title",
        "html": HTML.replace("Evidence", "Result"),
        "evidence": [
            {
                "id": "f1",
                "source_id": "s1",
                "quote": "One benchmark only.",
                "claim": "Limited to one benchmark",
            }
        ],
    }
    result = api.run_operation(note["operation_id"])
    assert result["state"] == "succeeded"
    new = result["result"]["revision_id"]
    assert new != rid
    assert api.get_revision(sid, new)["base_revision"] == rid
    assert api.get_revision(sid, new)["review"]["visual"] == "not_performed"
    assert api.get_story(sid)["selected_revision"] == rid
    assert api.get_story(sid)["annotations"][0]["result_revision"] == new


def test_bad_submission_cannot_publish(api):
    r = imported(api)
    sid, rid = r["story_id"], r["revision_id"]
    api.grant_feedback(sid, {}, "grant")
    note = api.add_comment(sid, rid, "Edit", "edit")
    api.intelligence = lambda *_: {
        "changes": {
            "summary": "Requested change",
            "material_changes": [],
            "omissions": [],
            "assumptions": [],
        },
        "calculations": [],
        "action": "revise",
        "message": "Done",
        "html": "<p>Not a document</p>",
    }
    assert api.run_operation(note["operation_id"])["state"] == "failed"
    assert len(api.get_story(sid)["revisions"]) == 1


def test_cancel_blocks_late_revision(api):
    r = imported(api)
    sid, rid = r["story_id"], r["revision_id"]
    api.grant_feedback(sid, {}, "grant")
    note = api.add_comment(sid, rid, "Edit", "edit")
    started, finish = threading.Event(), threading.Event()

    def model(*_):
        started.set()
        finish.wait(5)
        return {
            "changes": {
                "summary": "Requested change",
                "material_changes": [],
                "omissions": [],
                "assumptions": [],
            },
            "calculations": [],
            "action": "answer",
            "message": "Late answer",
        }

    api.intelligence = model
    worker = threading.Thread(target=api.run_operation, args=(note["operation_id"],))
    worker.start()
    assert started.wait(5)
    api.cancel_operation(note["operation_id"])
    finish.set()
    worker.join(5)
    assert api.get_operation(note["operation_id"])["state"] == "cancelled"
    assert api.get_story(sid)["annotations"][0]["responses"] == []


def test_source_quotes_reject_fabrication(api):
    r = imported(api)
    sid, rid = r["story_id"], r["revision_id"]
    api.grant_feedback(sid, {}, "grant")
    n = api.add_comment(sid, rid, "Edit", "edit")
    api.intelligence = lambda *_: {
        "changes": {
            "summary": "Requested change",
            "material_changes": [],
            "omissions": [],
            "assumptions": [],
        },
        "calculations": [],
        "action": "revise",
        "message": "Done",
        "html": HTML,
        "evidence": [{"id": "f", "source_id": "s1", "quote": "Revenue doubled", "claim": "Revenue doubled"}],
    }
    assert api.run_operation(n["operation_id"])["state"] == "failed"
    assert len(api.get_story(sid)["revisions"]) == 1


def test_real_bundle_fixture_isolated_and_export_exact(api, tmp_path):
    source = Path(__file__).parent / "fixtures/stories-bundle-overview.html"
    r = api.create_story("Sample", source.read_text(), "sample")
    p = api.get_preview(r["story_id"], r["revision_id"])
    assert "<script" not in p["html"].lower()
    assert len(p["elements"]) > 50
    out = tmp_path / "sample.html"
    api.export(r["story_id"], r["revision_id"], str(out))
    assert out.read_bytes() == source.read_bytes()


def test_import_does_not_boot_agent(tmp_path):
    code = "import sys; from amplifier_smart_tool_stories import Stories; Stories.manifest(); assert 'amplifier_agent_lib' not in sys.modules"
    subprocess.run([sys.executable, "-c", code], check=True, cwd=tmp_path)
    p = subprocess.run(
        [sys.executable, "-m", "amplifier_smart_tool_stories", "manifest"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(p.stdout)["name"] == "amplifier-smart-tool-stories"


def test_cli_invalid_and_empty_stdin(tmp_path):
    for data in ["[]", "{bad"]:
        p = subprocess.run(
            [
                sys.executable,
                "-m",
                "amplifier_smart_tool_stories",
                "--store",
                str(tmp_path),
                "create-story",
                "--input",
                data,
            ],
            capture_output=True,
            text=True,
        )
        assert p.returncode != 0 and json.loads(p.stdout)["status"] == "failed"
    p = subprocess.run(
        [sys.executable, "-m", "amplifier_smart_tool_stories", "create-story", "--input", "-"],
        input="",
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert p.returncode != 0


def test_clarification_and_explicit_followup(api):
    r = imported(api)
    sid, rid = r["story_id"], r["revision_id"]
    api.grant_feedback(sid, {"max_operations": 2}, "grant")
    n = api.add_comment(sid, rid, "Use the other number", "ambiguous")
    api.intelligence = lambda *_: {
        "changes": {
            "summary": "Requested change",
            "material_changes": [],
            "omissions": [],
            "assumptions": [],
        },
        "calculations": [],
        "action": "clarify",
        "message": "Which figure should replace which?",
    }
    result = api.run_operation(n["operation_id"])
    assert result["state"] == "needs_input"
    followup = api.respond(sid, n["annotation_id"], "Keep the measured 8 seconds; change no facts.", "answer")
    api.intelligence = lambda story, op: {
        "changes": {
            "summary": "Requested change",
            "material_changes": [],
            "omissions": [],
            "assumptions": [],
        },
        "calculations": [],
        "action": "answer",
        "message": "The measured 8 seconds is already retained.",
    }
    assert api.run_operation(followup["operation_id"])["state"] == "succeeded"
    assert len(api.get_story(sid)["revisions"]) == 1


def test_answer_evidence_remains_inspectable(api):
    r = imported(api)
    sid, rid = r["story_id"], r["revision_id"]
    api.grant_feedback(sid, {}, "grant")
    note = api.add_comment(sid, rid, "Scope?", "question")
    evidence = [{"id": "f1", "source_id": "s1", "quote": "One benchmark only.", "claim": "One benchmark"}]
    api.intelligence = lambda *_: {
        "changes": {
            "summary": "Requested change",
            "material_changes": [],
            "omissions": [],
            "assumptions": [],
        },
        "calculations": [],
        "action": "answer",
        "message": "One benchmark [f1].",
        "evidence": evidence,
    }
    result = api.run_operation(note["operation_id"])
    assert result["result"]["evidence"] == evidence
    assert api.get_story(sid)["annotations"][0]["responses"][0]["evidence"] == evidence


def test_unsafe_preview_content_is_inert(api):
    html = """<html><head><base href="https://evil.test"><meta http-equiv="refresh" content="0;url=https://evil.test"></head><body><p onclick="fetch('/api/stop')">Safe text</p><script>fetch('/api/stop')</script><iframe src="file:///etc/passwd"></iframe><img src="https://evil.test/beacon" onerror="alert(1)"><svg onload="alert(1)"></svg></body></html>"""
    r = api.create_story("Untrusted", html, "untrusted")
    p = api.get_preview(r["story_id"], r["revision_id"])["html"]
    for bad in ["<script", "<iframe", "<base", "<meta", "onclick", "onerror", "<svg", "https://evil.test"]:
        assert bad not in p
    assert api.get_revision(r["story_id"], r["revision_id"])["html"] == html


def test_unicode_range_uses_characters_not_utf16(api):
    html = "<html><body><p>A 😀 benchmark</p></body></html>"
    r = api.create_story("Unicode", html, "u")
    e = api.get_preview(r["story_id"], r["revision_id"])["elements"][0]
    note = api.add_comment(
        r["story_id"],
        r["revision_id"],
        "Emoji range",
        "u-note",
        {"kind": "text", "element": e["element"], "start": 2, "end": 3, "quote": "😀"},
    )
    assert note["status"] == "awaiting_authority"
