import asyncio
import copy

import pytest

from amplifier_smart_tool_stories import Stories, StoriesError
from amplifier_smart_tool_stories.artifacts import preview, validate_anchor
from amplifier_smart_tool_stories.documents import checked, render_document
from amplifier_smart_tool_stories.quality import render


def document():
    return {
        "title": "A bounded conclusion",
        "subtitle": "Historical source review",
        "blocks": [
            {
                "id": "finding",
                "kind": "heading",
                "text": "What the source supports",
                "items": [],
                "rows": [],
                "evidence_ids": [],
            },
            {
                "id": "evidence",
                "kind": "paragraph",
                "text": "An estimate is not a measurement. 🧭 Retain the limitation.",
                "items": [],
                "rows": [],
                "evidence_ids": [],
            },
            {
                "id": "comparison",
                "kind": "table",
                "text": "Evidence comparison",
                "items": [],
                "rows": [["Claim", "Status"], ["Time saved", "Estimated"]],
                "evidence_ids": [],
            },
        ],
    }


def test_document_renders_text_and_pages_without_controls():
    html = render_document(document())
    result = asyncio.run(render(html, 30))
    assert result["page_count"] == 1
    assert not result["findings"]
    assert "estimate" in result["rendered_text"]
    assert "Comment" not in html


def test_document_ids_survive_insertions_and_unicode_ranges_are_exact():
    doc = document()
    html = render_document(doc)
    _, anchors = preview(html)
    text = next(x["text"] for x in anchors if x["element"] == "d-evidence")
    start = text.index("🧭")
    target = {"kind": "text", "element": "d-evidence", "start": start, "end": start + 1, "quote": "🧭"}
    assert validate_anchor(html, target) == target
    doc["blocks"].insert(0, {**doc["blocks"][0], "id": "new"})
    assert validate_anchor(render_document(doc), target) == target
    target["quote"] = "Changed"
    with pytest.raises(StoriesError):
        validate_anchor(html, target)


def test_document_rejects_unsafe_ids_unavailable_evidence_and_large_blocks():
    for change in ({"id": '" onclick="bad'}, {"evidence_ids": ["invented"]}, {"text": "x" * 1401}):
        doc = document()
        doc["blocks"][0].update(change)
        with pytest.raises(StoriesError):
            checked(doc, [])
    doc = document()
    doc["blocks"][1]["text"] = '<script>alert("x")</script>'
    assert "<script>" not in render_document(doc)


def test_document_revision_retains_structure_and_annotation_base(tmp_path):
    doc = document()
    revised = copy.deepcopy(doc)
    revised["blocks"][1]["text"] = "An estimate needs validation."

    def adapter(story, operation):
        return {
            "changes": {
                "summary": "Requested change",
                "material_changes": [],
                "omissions": [],
                "assumptions": [],
            },
            "calculations": [],
            "action": "revise",
            "message": "Clarified the limitation.",
            "document": revised,
            "html": render_document(revised),
            "evidence": [],
        }

    api = Stories(tmp_path, intelligence=adapter)
    receipt = api.create_story("Brief", "", "import", document=doc)
    sid, rid = receipt["story_id"], receipt["revision_id"]
    api.grant_feedback(sid, {}, "grant")
    note = api.add_comment(
        sid, rid, "Clarify the limitation", "comment", {"kind": "element", "element": "d-evidence"}
    )
    api.save_draft(sid, rid, "draft", 1, "Keep this unsent", {"kind": "story"})
    op = api.run_operation(note["operation_id"])
    assert op["state"] == "succeeded"
    assert api.get_revision(sid, op["result"]["revision_id"])["document"] == revised
    story = api.get_story(sid)
    assert story["selected_revision"] == rid
    assert story["drafts"]["draft"]["text"] == "Keep this unsent"
    assert story["annotations"][0]["revision_id"] == rid
    assert api.get_preview(sid, rid)["kind"] == "document"


def test_generate_document_kind_rejects_wrong_artifact(tmp_path):
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
            "action": "revise",
            "message": "Wrong",
            "html": render_document(document()),
            "evidence": [],
        },
    )
    r = api.generate(
        "Brief", "Explain", "Reader", [{"id": "a", "content": "A fact"}], {}, "generate", kind="document"
    )
    op = api.run_operation(r["operation_id"])
    assert op["state"] == "failed"
    assert not api.get_story(r["story_id"])["revisions"]


def test_exports_are_explicit_identified_and_exclude_review(tmp_path):
    import base64
    import io
    import zipfile

    import pypdfium2

    api = Stories(tmp_path / "store")
    r = api.create_document("Brief", document(), "create")
    sid, rid = r["story_id"], r["revision_id"]
    api.add_comment(sid, rid, "PRIVATE REVIEW NOTE", "note", author="agent")
    pdf = api.get_export(sid, rid, "pdf")
    doc = pypdfium2.PdfDocument(base64.b64decode(pdf["data_base64"]))
    text = doc[0].get_textpage().get_text_range()
    assert "bounded conclusion" in text and "PRIVATE REVIEW" not in text
    assert pdf["source_sha256"] == api.get_revision(sid, rid)["sha256"]
    assert pdf["checks"]["visual"] == "not_performed"
    word = api.get_export(sid, rid, "docx")
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(word["data_base64"]))) as package:
        xml = package.read("word/document.xml").decode()
        assert "bounded conclusion" in xml and "PRIVATE REVIEW" not in xml
        assert not any("comments" in x for x in package.namelist())
    assert word["limitations"]
    output = tmp_path / "brief.docx"
    api.export(sid, rid, output, format="docx")
    with pytest.raises(StoriesError) as exc:
        api.export(sid, rid, output, format="docx")
    assert exc.value.code == "output_exists"
    with pytest.raises(StoriesError):
        api.get_export(sid, rid, "pptx")


def test_revision_keeps_existing_citation_meanings_when_extraction_order_changes():
    from amplifier_smart_tool_stories.artifacts import revision_evidence

    base = [
        {"id": "fact1", "source_id": "s", "quote": "Eleven agents", "claim": "Reported eleven"},
        {"id": "fact2", "source_id": "s", "quote": "Four formats", "claim": "Reported four"},
    ]
    extracted = [
        {"id": "fact1", "source_id": "s", "quote": "Four formats", "claim": "Reported four"},
        {"id": "fact2", "source_id": "s", "quote": "Five elsewhere", "claim": "Conflicting five"},
    ]
    result = revision_evidence(base, extracted)
    assert result[:2] == base
    assert result[2]["id"] == "fact3"
    assert result[2]["quote"] == "Five elsewhere"
    assert extracted[1]["id"] == "fact2"


def test_inline_marks_exports_and_unicode_anchors(tmp_path):
    import base64
    import io
    import zipfile

    from bs4 import BeautifulSoup
    from lxml import etree

    doc = document()
    block = doc["blocks"][1]
    block["text"] = "🧭 Visit Stories & explore."
    block["marks"] = [{"start": 8, "end": 15, "bold": True, "href": "https://example.com/stories?a=1&b=2"}]
    html = render_document(doc)
    soup = BeautifulSoup(html, "html.parser")
    assert soup.select_one("a strong").text == "Stories"
    assert soup.select_one("#evidence").get_text() == block["text"]
    safe, anchors = preview(html)
    assert "data-stories-link" in safe
    assert (
        validate_anchor(
            html, {"kind": "text", "element": "d-evidence", "start": 8, "end": 15, "quote": "Stories"}
        )["quote"]
        == "Stories"
    )
    api = Stories(tmp_path)
    r = api.create_document("Formatted", doc, "rich")
    sid, rid = r["story_id"], r["revision_id"]
    assert api.get_preview(sid, rid)["kind"] == "document"
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(api.get_export(sid, rid, "docx")["data_base64"]))) as z:
        xml = etree.fromstring(z.read("word/document.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        assert xml.xpath("//w:hyperlink/w:r/w:rPr/w:b", namespaces=ns)
        assert "https://example.com/stories?a=1&amp;b=2" in z.read("word/_rels/document.xml.rels").decode()
    import pypdfium2

    pdf = pypdfium2.PdfDocument(base64.b64decode(api.get_export(sid, rid, "pdf")["data_base64"]))
    assert "Stories" in pdf[0].get_textpage().get_text_range()
    import ctypes

    position = ctypes.c_int(0)
    link = pypdfium2.raw.FPDF_LINK()
    page = pdf[0]
    assert pypdfium2.raw.FPDFLink_Enumerate(page, ctypes.byref(position), ctypes.byref(link))
    action = pypdfium2.raw.FPDFLink_GetAction(link)
    size = pypdfium2.raw.FPDFAction_GetURIPath(pdf, action, None, 0)
    uri = ctypes.create_string_buffer(size)
    pypdfium2.raw.FPDFAction_GetURIPath(pdf, action, uri, size)
    assert uri.value.decode() == "https://example.com/stories?a=1&b=2"


@pytest.mark.parametrize(
    "mark",
    [
        {"start": 0, "end": 999, "bold": True, "href": ""},
        {"start": True, "end": 3, "bold": True, "href": ""},
        {"start": 0, "end": 3, "bold": True, "href": "javascript:alert(1)"},
        {"start": 0, "end": 3, "bold": True, "href": "https://user:pass@example.com"},
        {"start": 0, "end": 3, "bold": True, "href": "https://example.com\n"},
    ],
)
def test_rejects_invalid_inline_marks(mark):
    doc = document()
    doc["blocks"][1]["marks"] = [mark]
    with pytest.raises(StoriesError):
        checked(doc)


def test_rejects_overlapping_marks_and_spoofed_preview_link():
    doc = document()
    doc["blocks"][1]["marks"] = [
        {"start": 0, "end": 5, "bold": True, "href": ""},
        {"start": 4, "end": 7, "bold": True, "href": ""},
    ]
    with pytest.raises(StoriesError):
        checked(doc)
    html = '<html><body><p><a href="javascript:bad()" data-stories-link="https://example.com">unsafe</a></p></body></html>'
    assert "data-stories-link" not in preview(html)[0]
