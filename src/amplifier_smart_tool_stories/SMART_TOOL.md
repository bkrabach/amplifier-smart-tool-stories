---
smart_tool_format: 1
name: amplifier-smart-tool-stories
version: 0.1.0
description: >-
  Create evidence-based presentations and documents with agent highlights and
  anchored comments. Use for source-backed communication and shared review.
use_cases:
  - Turn supplied evidence into an HTML presentation or structured document
  - Review a story with a person and highlight material that needs attention
  - Answer or act on anchored feedback while preserving the reader's place
platforms:
  - macos
requires:
  - name: model-provider-access
    purpose: Needed for generation and intelligent comment responses; retained review works without it.
    optional: true
    install: https://github.com/robotdad/amplifier-smart-tool-stories/blob/main/docs/USAGE.md
  - name: pango
    purpose: Native text layout for static rendered review of generated and revised artifacts.
    optional: true
    install: https://github.com/robotdad/amplifier-smart-tool-stories/blob/main/docs/USAGE.md
---
# Stories

Create evidence-based HTML stories and review them with a person. The Python
library is the product; the `stories` CLI and optional local dashboard share its
state. It supports HTML presentations, structured documents and anchored review.
Documents export as HTML, Letter PDF or editable Word; PowerPoint and spreadsheets
remain deferred.

## Install and prerequisites

`uv tool install 'amplifier-smart-tool-stories @ git+https://github.com/robotdad/amplifier-smart-tool-stories'`

Python 3.12+. Deterministic operations require no provider. Smart operations use
embedded amplifier-agent from main. The development lockfile records a tested
revision; new Git installs resolve the current main. No Amplifier CLI session or
Anthropic skills checkout is needed.

Before model use, explicitly prepare each selected provider's runtime:
`stories --provider openai prepare-runtime`. Preparation may fetch/install Amplifier
modules and writes to its native cache. Missing preparation produces an actionable
failure; deterministic paths never initialize an agent. If native caches are manually
removed or invalidated, prepare again. Model execution uses the selected provider's
native environment/OAuth credentials and sends the supplied story/source context to it.
No fallback provider or network research occurs.

Artifact production additionally needs Pango (on macOS: `brew install pango`).
WeasyPrint and PDFium are packaged Python dependencies. No browser download or
LibreOffice is required. Missing rendering prerequisites fail the operation; they
are never installed during generation. Imports, reading and answers do not render.

Providers: openai (OPENAI_API_KEY), anthropic (ANTHROPIC_API_KEY), gemini
(GOOGLE_API_KEY or GEMINI_API_KEY), chatgpt (Amplifier's existing OAuth device-login
cache), copilot (COPILOT_AGENT_TOKEN, COPILOT_GITHUB_TOKEN, GH_TOKEN or GITHUB_TOKEN).
Aliases openai-chatgpt and github-copilot are accepted. Stories does not perform
interactive login during a call. For Copilot, use `provider-login` or dashboard Sign in with installed GitHub CLI;
subscription/model access is required. Sign-in supplies the current process with a
token. For later CLI processes, export a token from `gh auth token` into GH_TOKEN. For ChatGPT, use `provider-login` or dashboard Sign in. `provider-settings` gives redacted readiness; it
is not proof that the account can use a model. `test-provider` explicitly checks it.

## Calling it

Global options precede the capability: `--store PATH`, `--model-env`, `--provider NAME`,
`--model ID`, `--execution queued|background|in_process`. Default execution is queued.
Default provider is openai; STORIES_PROVIDER/STORIES_MODEL provide environment defaults.
Settings affect future calls and authorized feedback in this instance, never already-queued work.
`configure-provider` is process-local: a CLI call does not save settings for the next
CLI process. Pass --provider/--model on each invocation or set STORIES_PROVIDER/STORIES_MODEL. Dashboard Settings provides the same session-local selection, model discovery, connection test, explicit runtime preparation and native ChatGPT/Copilot sign-in. Keys never belong in request JSON or retained state.

Every capability accepts `--input '{...}'`, `--input @file.json`, or `--input -`.
File input loads the exact JSON content; HTML/source contents are explicit strings,
not implicitly resolved filesystem paths or URLs. `stories CAPABILITY --help` gives
its operating skill: inputs, worked invocation, results, execution and sharp edges. Results are JSON on stdout; failure is nonzero with a
code and remedy. `stories manifest` is a provider-free smoke check. `-h` and `--help`
print this complete operating guide.

```python
from amplifier_smart_tool_stories import Stories

api = Stories("/chosen/state")
receipt = api.create_story(
    title="Overview",
    html=html_string,
    sources=[{"id": "s1", "name": "Source", "content": "Source text"}],
    request_id="import-1",
)
story_id, revision_id = receipt["story_id"], receipt["revision_id"]
# Inspect revision-local element IDs and exact text before choosing an anchor.
preview = api.get_preview(story_id, revision_id)
api.add_comment(
    story_id, revision_id, "Please check this claim.", "highlight-1", anchor={"kind": "story"}, author="agent"
)
viewer = api.start_dashboard(story_id, revision_id)
```

Open the returned private loopback URL only when authorized. No browser is opened
implicitly. It is a bearer capability for this story; do not share it. The opaque
iframe suppresses source scripts, forms and external resources. It displays static
HTML/CSS with review-owned navigation for `.slide` sections. It is an approximate
static preview when the original relies on scripts; exact original HTML is retained
for export. Browser annotations and drafts never modify exported bytes.

Use `get-preview` to discover anchors. Text anchors contain kind=text, element,
start/end (Unicode character offsets within that element), and exact quote. Element
anchors contain kind=element and element. Whole-story anchors contain kind=story.
Anchors never silently migrate to another revision. Person text selection and element
clicking use the same public validation. Comments open in a floating overlay and
must not alter material geometry. Agent highlights never initiate model work.

For direct comment handling, authorize a bounded number of future operations:
```python
api = Stories("/chosen/state", model_env=True, provider="anthropic", execution="background")
api.grant_feedback(story_id, {"max_operations": 5, "timeout_seconds": 180}, "grant-1")
viewer = api.start_dashboard(story_id, revision_id)
```
Each user comment consumes one operation allowance when queued. Typing/saving drafts
never spends. A grant expires after one hour by default, at most 24 hours, and limits
operations, time per operation and output tokens per call. Each operation uses at most
five presentation model calls, or eleven for documents reviewed in batches of up to
three pages: evidence/planning, composition, source/page review, and at most one repair
with fresh review. Answers and clarifications use at most two. It can answer,
revise or ask for clarification. Clarifications are visible `needs_input` outcomes; use `respond` for comment questions
and `answer-question` for initial generation. They are not automatically resumed. Grants are not dollar limits. No automatic retries occur.

To generate a new story, call `generate` with title, purpose, audience, source objects,
grant and request_id. Optional kind is presentation (default) or document. The receipt identifies story and operation. Call `run-operation`
explicitly for queued execution, or choose background/in_process at submission.
Background workers survive caller exit; read operations never start workers.
Provider preparation requires explicit setup. Model access requires `--model-env`.
Sources remain identifiable by hash and evidence quotes are verified against supplied
text. New and revised artifacts require model review against sources and images of
every static rendered page (maximum 12, 1280x720 presentations or Letter documents). Mechanical findings cannot
be overridden by a model pass. Records identify exact HTML and rendered-page hashes;
an edit invalidates the old review. Rendering is bounded to 40 seconds per attempt
within the operation deadline, with external/file resource fetching disabled.
Persistent review failure retains an unaccepted candidate on the failed operation,
not a selected revision. Imports keep semantic/visual review as not_performed.
Static WeasyPrint rendering approximates browser layout; model review is neither
human approval nor independent factual verification. Generated outputs remain drafts.

## Capabilities

All exist as methods on Stories (hyphens become underscores):

- `answer-question`: answer a pending initial-generation question with an explicit grant.
- `accept-revision`: record person acceptance of an exact revision separately from model review.

- `manifest`: structured capability names, signatures and model-use classifications.
- `create-story`: import supplied HTML with title, optional sources, purpose and audience.
- `create-document`: import uncited title/subtitle/blocks structure without model use.
- `generate`: queue a presentation or document from supplied sources with a finite grant.
- `list-stories`, `get-story`: retained identities, sources, revisions, drafts and annotations.
- `get-revision`: exact immutable artifact, evidence, hash, limitations and check statuses.
- `get-preview`: isolated static HTML and revision-local element/text anchor catalog.
- `select-revision`: explicitly change the shared selected version; no approval implied.
- `grant-feedback`: bounded future user-comment authority; no spending on grant creation.
- `add-comment`: submit a user comment or caller-authored highlight, with revision and anchor.
- `respond`: user follow-up on an existing annotation's exact target; prior related comments supplied.
- `save-draft`: monotonically ordered draft save, no model use.
- `read-changes`: ordered events and next cursor; no model use or notification guarantee.
- `get-operation`: status/result/error; no worker restart. An elapsed running operation is
  reported interrupted/uncertain; cancel it before explicitly creating replacement work.
- `run-operation`: claim and execute one queued operation exactly once.
- `cancel-operation`: prevent late commits and cooperatively stop active model work.
- `export`: write a named revision to a new output_path; format html (default), pdf or docx.
- `get-export`: base64 bytes, MIME type, revision and source/output hashes, checks and limits.
  PDF/Word support structured documents only; no arbitrary HTML conversion.
- `storytelling-capabilities`: provider-free writing approaches and upstream mapping.
- `provider-models`: discover native model IDs; access and compatibility are not guaranteed.
- `provider-login`: explicit ChatGPT/Copilot native sign-in or API-key setup guidance.
- `provider-settings`: redacted effective settings and credential readiness.
- `configure-provider`: process-local future settings; no credential storage or spending.
- `prepare-runtime`: explicit dependency preparation, network/package/cache writes.
- `test-provider`: one small live model request, with explicit model-env.
- `start-dashboard`: owned loopback service for a named story, no automatic browser opening.
- `stop-dashboard`: release owned service, cancel its comment operations, retain all data.
- `skill`: CLI convenience printing these instructions; package resource accessible in Python.

## Continuity and limitations

Mutating submissions use caller request_id; identical retries return the original
receipt, changed payloads conflict. Request IDs are global to the selected store.
A retry receipt does not rerun failed or interrupted work. Saved operations snapshot
provider/model and grants. Cancelling prevents late commits but a provider request
already in flight may have consumed tokens. Uncertain spending is never retried silently.
A revision branches from the specified base; viewing does not implicitly advance to a
new result. The dashboard shows a quiet new-version button, preserving view, comment and
draft until explicit switching. Draft IDs should be unique per editor/session; sequence
numbers prevent older saves overwriting newer ones. Browser local draft recovery is a
convenience, while acknowledged saves are available through the library.

State and events are retained without automatic expiration in the chosen local store
(default ~/.local/share/stories). Single-host SQLite; not a multi-user hosted service.
No automatic publication, notification, caller wake-up, repository access, commits or pushes.
Only supplied content is available to intelligence. HTML with external assets or source
scripts may preview differently; exported originals may contain their original active
content. Independent semantic/visual grading, production brand systems, images/equations,
general conversion remain outside this slice.


## Structured documents

Generate with `kind="document"`. The retained `get-revision` result includes `document`:
`{title, subtitle, blocks}`. Each block has `{id, kind, text, items, rows, evidence_ids}`;
kinds are heading, paragraph, quote, list, table. IDs are unique safe identifiers and
remain stable on unaffected blocks. Unused arrays are empty. Paragraphs/quotes have
at most 1400 characters; lists eight items (300 characters each); tables eight equal
rows, five columns, 160-character cells and 1600 characters total. Maximum 100 blocks.
The library validates evidence references and renders self-contained HTML. Sources,
uncertainty and citations remain visible. Direct import accepts uncited structure;
it does not claim factual review. Inspect the current signature with capability help.

Review defaults to continuous flow, with paginated view and zoom/fit width behind a
small hover/click/focus reveal tab. User and agent comment navigation shares the same
state. Comments anchor in available whitespace or float; never change material width.
View changes preserve the reading passage and drafts. An offscreen anchored composer
closes without discarding its draft. New revisions remain explicitly selected.

PDF exports use the retained HTML and checked Letter layout. Word exports use native
editable paragraphs, lists and tables; python-docx is packaged. No LibreOffice or
external skill checkout is a product dependency. Browser pagination is approximate;
Word line/page breaks vary with renderer/fonts. Export limitations and unperformed
visual checks are explicit. Inspect the actual target before delivery, rather than
assuming HTML review certifies another format. Annotations never enter exports.

## Provider discovery and sign-in

`provider-models(provider=None, timeout_seconds=60)` reads native model IDs from a
prepared provider without generation. Catalog presence does not guarantee access or
image/tool compatibility. `provider-login(provider=None, timeout_seconds=300)` starts
explicit ChatGPT/Copilot login; API-key providers return setup guidance. Both require
`--model-env`. Login may fetch runtime modules; device authorization remains with the
person. CLI progress goes to stderr; library hosts may pass `on_progress(text)`.
Credentials stay in native environment/provider caches, never story records.

In Dashboard Settings, testing/discovery/login do not apply the selection. Apply
changes future work in that session, preserving existing operations and grant limits.
Setup runs asynchronously; close Settings to keep reading. Sending comments waits
for setup to finish while drafts remain saved. Stop the viewer to cancel owned setup.

## Storytelling expertise

`storytelling-capabilities` lists the supported writing approaches and upstream
mapping without model access. `generate` still takes purpose, audience, sources and
kind; callers need not choose a specialist. Evidence planning selects one or two
allowlisted approaches, then composition, review and repair load that guidance.
The operation result's `provenance.expertise` records IDs, guidance hashes and
upstream resource paths; `provenance.plan` records the audience/narrative plan.
Comments can change the selected approach (for example, a leadership adaptation)
without changing the artifact kind or losing the existing revision.

Approaches: grounded narrative, case study/feature journey, release notes/migration
explanation, technical explanation, public feature communication, community
spotlight/digest, executive brief, audience adaptation, editorial planning, and
metrics/evaluation explanation. These are writing capabilities over supplied text,
not repository scanners, executable code verification, platform publishing,
spreadsheet calculation or arbitrary file conversion. All use the existing supported
presentation/document outputs and quality review, within the existing call allowance.

## Questions, source status and acceptance

`answer-question` takes operation_id, text, grant and request_id to answer a pending
initial-generation question. It creates a correlated bounded continuation in the
same story with the original provider/model and retained question/answer history.
The answered operation becomes `continued` and exposes `answered_by`; its question
is retained, while the child operation carries execution status.
Supply a new finite grant explicitly; no extra spending is inferred from the old
question. A question accepts one answer; identical request retries return the same
receipt. Default execution is queued. Comment questions still use `respond`.

Source objects accept optional `kind` (source, summary, hypothesis, preference;
default source) and `attribution` text. A source is supplied material, not certified
truth. Summary originals are not implicitly inspected. Classification and attribution
travel with the extracted evidence; preferences and hypotheses are not original
observations. Existing sources without these fields retain the source default.

Generated results and revisions expose `changes` with summary, material_changes,
omissions and assumptions, plus `calculations`. Revision review compares the base
and proposed content and checks disclosures. Calculation entries identify quoted
inputs, operation, result, decimal_places and unit. Decimal arithmetic is verified;
semantic relevance, coverage and units still require model/human review. Supported
operations are sum, difference, product, ratio and percent_change (old then new).
Rounding is half up at 0–12 decimal places. Unsupported derivations must be omitted
with a limitation or clarified. Story details exposes these records alongside sources.

`accept-revision` takes story_id, revision_id and request_id. Call only to record a
person's explicitly conveyed acceptance of that exact version. The dashboard offers
Accept this revision in Story details. Acceptance records timestamp and artifact hash,
and appears in shared story state/events. It does not change model checks, select a
version, accept later revisions, modify exports, authorize work or grant publication.
