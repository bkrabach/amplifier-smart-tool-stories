import json
import threading
import urllib.error
import urllib.request

import pytest

from amplifier_smart_tool_stories import Stories
from amplifier_smart_tool_stories.dashboard import Dashboard


@pytest.fixture
def server(tmp_path):
    api = Stories(tmp_path)
    r = api.create_story("Test", "<html><body><p>Hello world</p></body></html>", "s")
    other = api.create_story("Other", "<html><body><p>Private</p></body></html>", "o")
    api.grant_feedback(other["story_id"], {}, "g")
    op = api.add_comment(other["story_id"], other["revision_id"], "Private", "c")["operation_id"]
    server = Dashboard(api, r["story_id"])
    thread = threading.Thread(target=server.serve)
    thread.start()
    yield server, r, op
    server.server.shutdown()
    thread.join(5)


def post(server, name, data, token=None, origin=None):
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + (token or server.token)}
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(
        f"http://127.0.0.1:{server.server.server_port}/api/{name}",
        data=json.dumps(data).encode(),
        headers=headers,
    )
    return urllib.request.urlopen(req)


def test_auth_origin_scope_and_no_arbitrary_capabilities(server):
    s, r, other_op = server
    for name, data, token, origin in [
        ("get-story", {}, "bad", None),
        ("get-story", {}, None, "null"),
        ("get-story", {}, None, "https://evil.test"),
        ("export", {"output_path": "/tmp/no"}, None, None),
        ("get-operation", {"operation_id": other_op}, None, None),
    ]:
        with pytest.raises(urllib.error.HTTPError):
            post(s, name, data, token, origin)
    with post(s, "get-story", {}) as response:
        assert json.load(response)["id"] == r["story_id"]


def test_dashboard_library_parity(server):
    s, r, _ = server
    with post(
        s, "add-comment", {"revision_id": r["revision_id"], "text": "Question", "request_id": "review"}
    ) as response:
        result = json.load(response)
    story = s.api.get_story(r["story_id"])
    assert story["annotations"][0]["id"] == result["annotation_id"]
    assert story["annotations"][0]["author"] == "user"
    with post(s, "download", {"revision_id": r["revision_id"]}) as response:
        assert response.read().decode() == "<html><body><p>Hello world</p></body></html>"


def test_owned_process_lifecycle_and_retention(tmp_path):
    api = Stories(tmp_path)
    created = api.create_story("Owned viewer", "<html><body><p>Retain me</p></body></html>", "create")
    viewer = api.start_dashboard(created["story_id"], created["revision_id"])
    assert viewer["url"].startswith("http://127.0.0.1:") and "#" in viewer["url"]
    assert api.stop_dashboard(viewer["service_id"])["status"] == "stopped"
    assert api.get_revision(created["story_id"], created["revision_id"])["html"].endswith("</html>")


def test_document_binary_downloads_use_exact_format_and_scope(tmp_path):
    import io
    import zipfile

    api = Stories(tmp_path)
    document = {
        "title": "Portable brief",
        "subtitle": "",
        "blocks": [
            {
                "id": "body",
                "kind": "paragraph",
                "text": "Retain this text.",
                "items": [],
                "rows": [],
                "evidence_ids": [],
            }
        ],
    }
    r = api.create_document("Brief", document, "doc")
    server = Dashboard(api, r["story_id"])
    thread = threading.Thread(target=server.serve)
    thread.start()
    try:
        with post(server, "download", {"revision_id": r["revision_id"], "format": "docx"}) as response:
            assert "story.docx" in response.headers["Content-Disposition"]
            assert "wordprocessingml" in response.headers["Content-Type"]
            with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
                assert b"Retain this text" in archive.read("word/document.xml")
        with post(server, "download", {"revision_id": r["revision_id"], "format": "pdf"}) as response:
            assert response.read().startswith(b"%PDF")
            assert "story.pdf" in response.headers["Content-Disposition"]
        with pytest.raises(urllib.error.HTTPError):
            post(server, "download", {"revision_id": r["revision_id"], "format": "pptx"})
    finally:
        server.server.shutdown()
        thread.join(5)


def test_dashboard_control_bindings_have_unique_elements():
    import re
    from importlib.resources import files

    from bs4 import BeautifulSoup

    resources = files("amplifier_smart_tool_stories").joinpath("resources")
    html = BeautifulSoup(resources.joinpath("dashboard.html").read_text(), "html.parser")
    ids = [n["id"] for n in html.select("[id]")]
    assert len(ids) == len(set(ids))
    required = set(re.findall(r'\$\("([^"\n]+)"\)', resources.joinpath("dashboard.js").read_text()))
    assert required <= set(ids), required - set(ids)
