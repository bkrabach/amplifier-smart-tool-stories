"""Native document reading and explicit link navigation in the real browser."""

import threading

import pytest

from amplifier_smart_tool_stories import Stories
from amplifier_smart_tool_stories.dashboard import Dashboard


def test_document_links_open_separately_without_slide_controls(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    api = Stories(tmp_path)
    doc = {
        "title": "Document links",
        "subtitle": "",
        "blocks": [
            {
                "id": "body",
                "kind": "paragraph",
                "text": "Visit Stories to continue.",
                "items": [],
                "rows": [],
                "evidence_ids": [],
                "marks": [{"start": 6, "end": 13, "bold": True, "href": "https://example.com/stories"}],
            }
        ],
    }
    r = api.create_document("Document links", doc, "create")
    server = Dashboard(api, r["story_id"])
    thread = threading.Thread(target=server.serve)
    thread.start()
    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            # Block external loading while verifying the browser navigation request.
            page.context.route("https://example.com/**", lambda route: route.fulfill(body="Link destination"))
            page.goto(f"http://127.0.0.1:{server.server.server_port}/#{server.token}")
            page.wait_for_selector("body.document-review", state="attached")
            assert not page.locator("#previous").is_visible()
            assert not page.locator("#next").is_visible()
            link = page.frame_locator("iframe").locator("a[data-stories-link]")
            assert link.locator("strong").inner_text() == "Stories"
            with page.expect_popup() as popup:
                link.click()
            target = popup.value
            target.wait_for_load_state()
            assert target.url == "https://example.com/stories"
            assert page.locator("body.document-review").count() == 1
            target.close()
            link.focus()
            with page.expect_popup() as popup:
                page.keyboard.press("Enter")
            popup.value.close()
            browser.close()
    finally:
        server.server.shutdown()
        thread.join(5)
