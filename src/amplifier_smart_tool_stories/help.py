"""Packaged, provider-free operating skills for the CLI."""

import inspect
import json
import shlex
from importlib.resources import files

from .lib import Stories

# Examples are valid JSON inputs; retained identities must come from earlier receipts.
VALUES = {
    "title": "Release brief",
    "html": '<html><body><section class="slide"><h1>Release brief</h1></section></body></html>',
    "request_id": "brief-1",
    "purpose": "Explain the supplied release",
    "audience": "Team leads",
    "sources": [{"id": "s1", "name": "Release note", "content": "Version 2 adds offline reading."}],
    "document": {
        "title": "Release brief",
        "subtitle": "",
        "blocks": [
            {
                "id": "intro",
                "kind": "paragraph",
                "text": "Version 2 adds offline reading.",
                "items": [],
                "rows": [],
                "evidence_ids": [],
            }
        ],
    },
    "story_id": "STORY_ID",
    "revision_id": "REVISION_ID",
    "annotation_id": "ANNOTATION_ID",
    "operation_id": "OPERATION_ID",
    "service_id": "SERVICE_ID",
    "draft_id": "editor-1",
    "sequence": 1,
    "text": "Please clarify this point.",
    "provider": "anthropic",
    "grant": {"max_operations": 1, "timeout_seconds": 180, "max_output_tokens": 12000},
    "output_path": "/tmp/stories-brief.html",
}

GUIDANCE = {
    "answer_question": (
        "Continue initial generation after a question.",
        "Queued receipt with story_id, operation_id and question_operation_id.",
        "Use a needs_input generation operation ID, answer text and a new finite grant. The original provider and story are retained. The parent becomes continued with answered_by pointing to the new operation. Each question accepts one answer; identical request_id retries reuse the receipt. Use --model-env for execution; queued work needs run-operation.",
    ),
    "accept_revision": (
        "Record a person's explicitly conveyed acceptance.",
        "status and acceptance with exact revision ID, artifact hash and timestamp.",
        "Only call when the person has accepted this revision. Does not change selection, model checks, later revisions or publication authority. No model use.",
    ),
    "manifest": (
        "Discover the callable surface before composing an integration.",
        "Manifest metadata, body and capability signatures.",
        "No store or provider is opened.",
    ),
    "create_story": (
        "Import existing HTML for review.",
        "status, story_id and revision_id.",
        "HTML is literal content, not a path. Import does not fact-check. External assets and scripts are suppressed in preview.",
    ),
    "create_document": (
        "Import existing structured writing for review.",
        "status, story_id and revision_id.",
        "Use title, subtitle and blocks with id/kind/text/items/rows/evidence_ids. Import accepts uncited structure; it does not certify facts.",
    ),
    "generate": (
        "Create source-backed material for a specified audience.",
        "Queued receipt with story_id and operation_id; inspect get-operation for the accepted revision or failure.",
        "kind is presentation or document. Sources require id/content with literal text; optional name, kind (source/summary/hypothesis/preference) and attribution preserve source status. grant bounds operations, timeout_seconds and max_output_tokens; optional expires_at is a Unix timestamp within 24 hours. Prepare the provider runtime first. Default queued execution needs run-operation; background and in_process execute on submission. Source context is sent to the selected provider; rendering needs Pango. No network research or fallback provider.",
    ),
    "list_stories": (
        "Find retained work to resume.",
        "Array of IDs, titles, selected_revision and latest_revision.",
        "Use returned IDs in subsequent calls.",
    ),
    "get_story": (
        "Resume review and inspect feedback outcomes.",
        "Shared story state, revision summaries, annotations, saved drafts, authority and revision-specific human acceptances.",
        "Read-only; does not start pending work. Use get-revision for artifact contents.",
    ),
    "get_revision": (
        "Inspect the exact artifact and its checks.",
        "Immutable revision including HTML, document where applicable, evidence, checks, changes and verified calculations.",
        "Name the revision explicitly; a newer revision does not replace this one.",
    ),
    "get_preview": (
        "Discover valid targets before adding an anchored comment.",
        "revision_id, static html, elements, kind and limitations.",
        "Use returned element IDs. Text anchors use Unicode start/end offsets and the exact quote; IDs belong to this revision.",
    ),
    "select_revision": (
        "Choose which existing version shared review selects.",
        "status and revision_id.",
        "Selection does not imply approval, regenerate content or move annotations.",
    ),
    "grant_feedback": (
        "Authorize bounded future responses to person comments.",
        "status and retained grant.",
        "grant supports max_operations (1–100), timeout_seconds (1–900), max_output_tokens (128–24000), expires_at within 24 hours. Defaults: 1 operation, 180 seconds, 12000 tokens, one hour. No model spending now; prepare runtime and use --model-env when executing responses.",
    ),
    "add_comment": (
        "Leave a caller highlight or submit person feedback.",
        "status, annotation_id and optional operation_id.",
        "author=agent highlights never start model work. Default author=user uses existing feedback authority, or returns awaiting_authority. anchor defaults to {kind: story}; element anchors add element, text anchors add element/start/end/quote. Discover targets with get-preview. Comments stay outside exports.",
    ),
    "respond": (
        "Follow up on a clarification or existing annotation.",
        "status, new annotation_id and optional operation_id.",
        "Uses the original target and thread context as a user comment. Existing feedback authority is required for model work; it does not restart the old operation.",
    ),
    "save_draft": (
        "Retain unfinished feedback without submitting it.",
        "saved status and sequence, or stale status and existing draft.",
        "Choose draft_id per editor/session; increase sequence monotonically. No model use. Anchor syntax is described by add-comment --help.",
    ),
    "read_changes": (
        "Observe updates since the last read.",
        "changes, cursor and history_gap.",
        "Pass the previous cursor as after. Up to 500 events per read; no worker start or caller notification is promised.",
    ),
    "get_operation": (
        "Poll submitted work without executing it.",
        "Operation state, result and error when present; results include changes and calculations. An answered generation question becomes continued with answered_by identifying its continuation.",
        "Queued is not completion. Inspect failure and needs_input outcomes. Interrupted or uncertain work is never retried automatically.",
    ),
    "run_operation": (
        "Execute one previously queued operation.",
        "Operation state with result or error.",
        "Requires prepared runtime and --model-env. Uses the retained provider/model and grant. Claims once; never use polling to retry uncertain spending.",
    ),
    "cancel_operation": (
        "Stop pending work or prevent an active operation committing late results.",
        "Updated operation record.",
        "Cancellation is cooperative; an in-flight provider request may already have consumed tokens.",
    ),
    "export": (
        "Write the named artifact to an explicit destination.",
        "status, path, format metadata, hashes, checks and limitations.",
        "format is html, pdf or docx. PDF/Word require structured documents; no PPTX or arbitrary HTML conversion. Parent directory must exist; never overwrites. Annotations are excluded. Word pagination may differ.",
    ),
    "get_export": (
        "Obtain artifact bytes without writing a file.",
        "data_base64, MIME type, revision/source/output hashes, checks and limits.",
        "format is html, pdf or docx. PDF/Word require structured documents. Decode data_base64; annotations are excluded. Inspect format-specific limitations.",
    ),
    "storytelling_capabilities": (
        "Learn supported writing approaches and source mapping.",
        "approaches, outputs, selection and limits.",
        "Generation chooses expertise internally; describe purpose and audience. No model use.",
    ),
    "provider_settings": (
        "Check redacted setup readiness.",
        "Effective provider/model, readiness and setup instructions.",
        "Readiness is not proof of model access. Keys remain in native environments/caches.",
    ),
    "configure_provider": (
        "Set future provider/model in a persistent library or dashboard instance.",
        "Redacted provider configuration.",
        "CLI processes are short-lived: this does not persist settings for the next invocation. Use global --provider and --model on each CLI call. Existing queued operations stay fixed.",
    ),
    "prepare_runtime": (
        "Explicitly install the selected provider runtime before model use.",
        "Runtime preparation receipt.",
        "May use network and install packages into native caches. Does not generate a story or sign in.",
    ),
    "test_provider": (
        "Verify access with one small live model request.",
        "Connection test receipt.",
        "Requires --model-env and prepared runtime; spends provider tokens. timeout_seconds defaults to 60.",
    ),
    "provider_models": (
        "Discover model IDs for the selected provider.",
        "Provider model catalog.",
        "Requires --model-env and prepared runtime. Discovery may use network but does not generate; catalog presence is not proof of image/tool compatibility or account access.",
    ),
    "provider_login": (
        "Start explicit native ChatGPT/Copilot authentication.",
        "Login result or API-key setup instructions.",
        "Requires --model-env. May fetch runtime modules. Person completes device authorization; progress goes to stderr. Credentials stay in native caches. on_progress is library-only, not a JSON argument.",
    ),
    "start_dashboard": (
        "Present retained work for shared review.",
        "Owned service receipt with private loopback URL.",
        "Does not open a browser. Treat the URL as a bearer credential. Model responses require explicit feedback authority and model access. Save service_id for stop-dashboard.",
    ),
    "stop_dashboard": (
        "Release an owned review service.",
        "Service stop receipt.",
        "Cancels owned comment work and setup while retaining stories, revisions and drafts.",
    ),
}


FIELD_HELP = {
    "title": "Short display title",
    "purpose": "Desired communication outcome",
    "audience": "Intended readers",
    "html": "Literal HTML content",
    "sources": "List of source objects: required id/content; optional name, kind (source/summary/hypothesis/preference), attribution",
    "document": "Structured title, subtitle and blocks object",
    "request_id": "Caller-chosen unique mutation identity",
    "story_id": "Retained story ID",
    "revision_id": "Exact retained revision ID",
    "operation_id": "Operation ID returned by submission",
    "annotation_id": "Existing annotation ID",
    "service_id": "Owned dashboard service ID",
    "grant": "Finite execution authority object",
    "anchor": "Revision-local story, element or text target",
    "author": "user for feedback; agent for a non-spending highlight",
    "text": "Comment or draft text",
    "draft_id": "Unique editor/session draft identity",
    "sequence": "Nonnegative increasing draft version",
    "after": "Previous event cursor, or zero",
    "kind": "presentation or document",
    "format": "html, pdf or docx",
    "output_path": "New destination file in an existing directory",
    "provider": "Provider alias; null uses current selection where accepted",
    "model": "Provider model ID; null uses its default",
    "timeout_seconds": "Maximum time allowed for the provider operation",
}


def example(name):
    parameters = inspect.signature(getattr(Stories, name)).parameters
    data = {
        key: VALUES[key]
        for key, parameter in parameters.items()
        if key != "self" and parameter.default is inspect.Parameter.empty
    }
    if name == "add_comment":
        data["author"] = "agent"
    return data


def skill_help(name=None):
    root = files("amplifier_smart_tool_stories")
    if name is None or name == "skill":
        body = root.joinpath("SMART_TOOL.md").read_text().split("---", 2)[2].strip()
        label = "stories"
    else:
        label = "stories-" + name.replace("_", "-")
        purpose, result, limits = GUIDANCE[name]
        params = inspect.signature(getattr(Stories, name)).parameters
        fields = []
        for key, param in params.items():
            if key in {"self", "on_progress"}:
                continue
            required = (
                "required"
                if param.default is inspect.Parameter.empty
                else "optional; default " + json.dumps(param.default)
            )
            fields.append(f"- `{key}` — {FIELD_HELP[key]}; {required}.")
        flags = (
            " --model-env"
            if name
            in {
                "generate",
                "answer_question",
                "run_operation",
                "test_provider",
                "provider_models",
                "provider_login",
            }
            else ""
        )
        invocation = f"stories --store /tmp/stories-review{flags} {name.replace('_', '-')} --input {shlex.quote(json.dumps(example(name)))}"
        body = f"""# {label}

## When to use

{purpose}

{getattr(Stories, name).__doc__}

## Inputs and invocation

Global options precede the command: --store PATH, --model-env, --provider NAME,
--model ID, --execution queued|background|in_process (default queued).
Provider choices: openai, anthropic, gemini, chatgpt, copilot.
Pass a JSON object with --input '{{...}}', --input @file.json, or --input - for stdin.
Replace uppercase identity placeholders with IDs from earlier receipts.

{chr(10).join(fields) or "No JSON fields; omit --input or use an empty object."}

```bash
{invocation}
```

## Result and next steps

{result}

## Execution and sharp edges

{limits}

Required request_id values identify mutations across the store: reuse only for an
identical retry; changed payloads conflict. A retry does not rerun failed work.

## Failures

Results and structured errors go to stdout as JSON. Provider login progress goes to
stderr. Exit 0 means the invocation succeeded, not that queued model work finished.
Exit 1 reports a named failure; exit 2 reports invalid input (parser diagnostics go
to stderr). Inspect error.code, message and remedy; never silently retry uncertain
model spending. Read stories --help for the complete workflow and prerequisites.
"""
    return (
        f'<skill_content name="{label}">\nSkill directory: {root}\n'
        "Relative resource paths are relative to this installed package.\n\n"
        f"{body}\n\n<skill_resources>\n  <file>SMART_TOOL.md</file>\n"
        "  <file>lib.py</file>\n</skill_resources>\n</skill_content>"
    )
