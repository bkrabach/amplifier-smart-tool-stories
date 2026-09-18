"""An actual MCP App in an unrelated AppBridge host, using no provider."""

import asyncio
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("mcp")
pytest.importorskip("playwright")
from mcp import Client
from playwright.async_api import async_playwright, expect
from test_mcp import fixture
from test_stories import HTML, SOURCE

from amplifier_smart_tool_stories import Stories
from amplifier_smart_tool_stories.mcp import create_server

ROOT = Path(__file__).parents[1]


def test_portable_review_drafts_comparison_media_and_nested_isolation(tmp_path):
    node = ROOT / "mcp-app" / "node_modules"
    if not node.exists():
        pytest.skip("Run npm ci --prefix mcp-app for the independent browser fixture.")
    script = subprocess.run(
        [
            str(node / ".bin/esbuild"),
            str(ROOT / "mcp-app/test-host.js"),
            "--bundle",
            "--format=iife",
            "--log-level=error",
        ],
        check=True,
        text=True,
        capture_output=True,
    ).stdout

    async def run():
        ids = fixture.seed(tmp_path)
        api = Stories(tmp_path)
        api.model_env = True
        deck = api.create_story(
            "Portable slide navigation",
            '<html><body><section class="slide"><h1>First · Café — 日本語 🧭</h1><img src="asset:'
            + ids["asset_id"]
            + '"></section><section class="slide"><h1>Second</h1></section></body></html>',
            "browser-slide-deck",
            sources=[],
            asset_ids=[ids["asset_id"]],
        )
        async with Client(create_server(api)) as client, async_playwright() as pw:
            browser = await pw.chromium.launch()
            page = await browser.new_page(viewport={"width": 1100, "height": 900})
            errors, calls, authorization_attempts = [], [], []
            delays = {}
            lose_authorization_ack = True
            page.on("pageerror", lambda error: errors.append(str(error)))

            async def tool(args):
                nonlocal lose_authorization_ack
                calls.append(args["name"])
                if args["name"] in delays:
                    started, release = delays[args["name"]]
                    started.set()
                    await release.wait()
                result = (await client.call_tool(args["name"], args.get("arguments", {}))).model_dump(
                    by_alias=True, exclude_none=True
                )
                if args["name"] == "stories_grant_feedback":
                    authorization_attempts.append(args["arguments"])
                    if lose_authorization_ack:
                        lose_authorization_ack = False
                        raise RuntimeError("Authorization acknowledgement was lost")
                return result

            async def read(args):
                return (await client.read_resource(args["uri"])).model_dump(by_alias=True, exclude_none=True)

            await page.expose_function("hostCall", tool)
            await page.expose_function("hostRead", read)
            await page.goto("about:blank")
            await page.add_script_tag(content=script)
            initial = await client.call_tool("stories_get_story", {"story_id": ids["story_id"]})
            html = (ROOT / "src/amplifier_smart_tool_stories/resources/mcp_app.html").read_text()
            await page.evaluate(
                "([html,result])=>mountStories(html,result)",
                [html, initial.model_dump(by_alias=True, exclude_none=True)],
            )
            frame = page.frame_locator("#app")
            await expect(frame.locator("#notice")).to_contain_text("Ready", timeout=15000)
            await frame.locator("#revisions").select_option(ids["revision_id"])
            await expect(frame.locator("#preview")).to_be_visible()
            await frame.get_by_role("button", name="Review", exact=True).click()
            await frame.locator("#grant summary").click()
            await frame.locator("#operations").fill("1")
            await frame.get_by_role("button", name="Authorize feedback", exact=True).click()
            await expect(frame.locator("#notice")).to_contain_text("acknowledgement was lost")
            assert len(authorization_attempts) == 1
            consumed = api.add_comment(
                ids["story_id"],
                ids["revision_id"],
                "Another reviewer submitted feedback",
                "consume-lost-grant",
            )
            assert consumed["status"] == "queued"
            assert api.get_story(ids["story_id"])["feedback_grant"]["used"] == 1
            # Changed values cannot silently replace an uncertain authorization.
            await frame.locator("#operations").fill("2")
            await frame.get_by_role("button", name="Authorize feedback", exact=True).click()
            await expect(frame.locator("#notice")).to_contain_text(
                "previous authorization may have been accepted"
            )
            assert len(authorization_attempts) == 1
            await frame.locator("#operations").fill("1")
            await frame.get_by_role("button", name="Authorize feedback", exact=True).click()
            await expect(frame.locator("#notice")).to_have_text(
                "Finite feedback allowance recorded; no work started."
            )
            assert authorization_attempts[1] == authorization_attempts[0]
            assert api.get_story(ids["story_id"])["feedback_grant"]["used"] == 1
            # A distinct control makes replacing a grant a new, explicit intent.
            await frame.locator("#operations").fill("2")
            await frame.get_by_role("button", name="Authorize new feedback", exact=True).click()
            await expect(frame.locator("#notice")).to_have_text(
                "Finite feedback allowance recorded; no work started."
            )
            assert (
                authorization_attempts[2]["request_id"] != authorization_attempts[0]["request_id"]
                and authorization_attempts[2]["grant"]["max_operations"] == 2
            )
            artifact = frame.frame_locator("#preview")
            await expect(artifact.locator("img").first).to_be_visible()
            await expect(artifact.locator("img").first).to_have_js_property("naturalWidth", 360)
            await frame.get_by_role("button", name="Review", exact=True).click()
            await frame.locator("#feedback").fill("Preserve the handoff context")
            await expect(frame.locator("#saved")).to_contain_text("Draft saved")
            assert "Preserve the handoff context" in str(api.get_story(ids["story_id"])["drafts"])
            # Switching revision immediately after save must use the acknowledged draft.
            await frame.locator("#revisions").select_option(ids["comparison_revision"])
            await frame.locator("#revisions").select_option(ids["revision_id"])
            await expect(frame.locator("#feedback")).to_have_value("Preserve the handoff context")
            bounds = await frame.locator("#preview").bounding_box()
            await frame.locator("#close").click()
            assert await frame.locator("#preview").bounding_box() == bounds
            await frame.locator("#comparisonSelect").select_option(ids["comparison_revision"])
            await expect(frame.locator("#comparison")).to_be_visible()
            assert api.get_story(ids["story_id"])["selected_direction"] is None
            await frame.locator("#select").click()
            await expect(frame.locator("#notice")).to_have_text("Direction choice recorded.")
            assert api.get_story(ids["story_id"])["selected_revision"] == ids["revision_id"]
            await frame.locator("#review").click()
            await expect(frame.locator("#feedback")).to_have_value("Preserve the handoff context")
            started, release = asyncio.Event(), asyncio.Event()
            delays["stories_add_comment"] = (started, release)
            await frame.locator("#send").click()
            await asyncio.wait_for(started.wait(), 5)
            await frame.locator("#feedback").fill("A newer unfinished thought")
            release.set()
            await expect(frame.locator("#notice")).to_contain_text("Comment recorded")
            notes = api.get_story(ids["story_id"])["annotations"]
            assert (
                len(notes) == 2
                and notes[-1]["status"] == "queued"
                and notes[-1]["revision_id"] == ids["revision_id"]
            )
            await expect(frame.locator("#feedback")).to_have_value("A newer unfinished thought")
            await expect(frame.locator("#saved")).to_contain_text("Draft saved")
            assert "A newer unfinished thought" in str(api.get_story(ids["story_id"])["drafts"])
            # Export identity survives a format change while the host is responding.
            await frame.locator('details[data-section="export"] summary').click()
            started, release = asyncio.Event(), asyncio.Event()
            delays["stories_get_export"] = (started, release)
            await frame.locator("#export").click()
            await asyncio.wait_for(started.wait(), 5)
            await frame.locator("#format").select_option("zip")
            release.set()
            await expect(frame.locator("#exportLinks a")).to_have_attribute(
                "download", "story-" + ids["revision_id"] + ".html"
            )
            # Agent navigation uses the same durable operation, then polling applies it.
            await frame.locator("#stories").select_option(deck["story_id"])
            await expect(frame.locator("#notice")).to_contain_text("Ready")
            await expect(frame.frame_locator("#preview").locator("h1").first).to_have_text(
                "First · Café — 日本語 🧭"
            )
            assert (
                await frame.frame_locator("#preview")
                .locator("html")
                .evaluate("element => element.ownerDocument.characterSet")
                == "UTF-8"
            )
            current = api.get_review_view(deck["story_id"])
            await client.call_tool(
                "stories_update_review_view",
                {
                    "story_id": deck["story_id"],
                    "expected_version": current["version"],
                    "request_id": "agent-navigate",
                    "slide": 2,
                    "panel_open": False,
                    "comparison_revision": "",
                    "sections": ["sources"],
                    "export_format": "zip",
                },
            )
            await expect(frame.locator("#position")).to_have_text("2 / 2", timeout=10000)
            await expect(frame.locator("#panel")).to_be_hidden()
            await frame.locator("#previous").click()
            await expect(frame.locator("#position")).to_have_text("1 / 2")
            assert api.get_review_view(deck["story_id"])["slide"] == 1
            # Reopen preserves the shared focus; concurrent input/result notifications deduplicate.
            initial = await client.call_tool("stories_get_story", {"story_id": deck["story_id"]})
            await page.evaluate(
                "([html,result])=>mountStories(html,result)",
                [html, initial.model_dump(by_alias=True, exclude_none=True)],
            )
            await expect(frame.locator("#notice")).to_contain_text("Ready", timeout=15000)
            assert await frame.locator("#revisions").input_value() == deck["revision_id"]
            assert await frame.locator("#format").input_value() == "zip"
            await expect(frame.frame_locator("#preview").locator("img").first).to_have_js_property(
                "naturalWidth", 360
            )
            # The nested artifact can neither read the App DOM nor invoke MCP.
            child = next(f for f in page.frames if f.url.startswith("blob:"))
            assert (
                await child.evaluate(
                    "(()=>{try{return parent.document.body.innerText}catch{return 'isolated'}})()"
                )
                == "isolated"
            )
            before = len(calls)
            await child.evaluate(
                "parent.postMessage({jsonrpc:'2.0',id:999,method:'tools/call',params:{name:'stories_cancel_operation',arguments:{operation_id:'forged'}}},'*')"
            )
            await page.wait_for_timeout(100)
            assert "stories_cancel_operation" not in calls[before:]
            # A first revision arriving after opening pending work must appear without reopen.
            pending = api.generate("Pending story", "Explain", "Team", [SOURCE], {}, "pending-create")
            initial = await client.call_tool("stories_get_story", {"story_id": pending["story_id"]})
            await page.evaluate(
                "([html,result])=>mountStories(html,result)",
                [html, initial.model_dump(by_alias=True, exclude_none=True)],
            )
            await expect(frame.locator("#notice")).to_contain_text("no revision yet")
            await frame.locator("#review").click()
            await expect(frame.locator("#panel")).to_be_visible()
            assert api.get_review_view(pending["story_id"])["version"] > 0
            api.intelligence = lambda *_: {
                "action": "revise",
                "message": "Retained fixture",
                "html": HTML,
                "evidence": [
                    {
                        "id": "fact",
                        "source_id": "s1",
                        "quote": SOURCE["content"],
                        "claim": "The source reports a limited benchmark.",
                    }
                ],
                "changes": {
                    "summary": "Imported deterministic fixture",
                    "material_changes": [],
                    "omissions": [],
                    "assumptions": [],
                },
                "calculations": [],
            }
            assert api.run_operation(pending["operation_id"])["state"] == "succeeded"
            await expect(frame.frame_locator("#preview").locator("h1")).to_have_text(
                "Evidence", timeout=10000
            )
            await expect(frame.locator("#notice")).to_contain_text("Ready")
            assert not errors, errors
            await page.screenshot(path=str(tmp_path / "portable-stories.png"))
            await browser.close()

    asyncio.run(run())
