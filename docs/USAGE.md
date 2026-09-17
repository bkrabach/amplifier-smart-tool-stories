# Using Stories

Stories supports HTML presentations and structured documents with shared review.
The [installed operating guide](../src/amplifier_smart_tool_stories/SMART_TOOL.md)
is the complete CLI/library reference. The broader contracts remain the product
requirements; this release does not claim full conformance to all of them.

## Development

```sh
uv sync --extra dev
uv run stories --help
uv run pytest
uv run ruff check src tests
```

The Amplifier Agent dependency tracks `main`. `uv.lock` records the revision used
for a development environment; use `uv lock --upgrade-package amplifier-agent`
and rerun validation when advancing it. New Git installs resolve main. No fixed
local checkout or external skills directory is used.

## Import a story and open review

```python
from pathlib import Path
from amplifier_smart_tool_stories import Stories

api = Stories('/chosen/stories-state')
created = api.create_story(
    title='Quarterly update', html=Path('/chosen/update.html').read_text(),
    request_id='quarterly-import-1',
    sources=[{'id':'quarter', 'name':'Quarterly notes', 'content':'Supplied evidence'}],
)
story, revision = created['story_id'], created['revision_id']
preview = api.get_preview(story, revision)
# Inspect preview['elements'] for IDs and exact text. Never guess an anchor.
api.add_comment(story, revision, 'Please check the supporting evidence.',
    request_id='highlight-1', author='agent', anchor={'kind':'story'})
viewer = api.start_dashboard(story, revision)
print(viewer['url'])  # Private bearer URL; open it only for the intended reviewer.
```

Import preserves exact HTML bytes for export. The viewer disables source scripts,
forms and external resources and supplies navigation for `.slide` sections. It
labels that static-preview limitation. Model-generated HTML is self-contained static
HTML/CSS. HTML that depends on JavaScript or remote assets may preview differently.

The approved interaction is material-first: the document occupies the viewport,
agent highlights reveal context, selecting text or an element offers a comment, and
the composer floats without reserving space or resizing the document. Annotations
are review state, not part of the export. The person chooses when to view a new
revision; background updates do not replace the displayed document.

## Connect intelligence

Prepare a provider once, explicitly allowing runtime module setup:

```sh
stories --provider openai prepare-runtime
stories --provider anthropic prepare-runtime
stories --provider gemini prepare-runtime
stories --model-env --provider openai test-provider
```

Use OpenAI, Anthropic and Gemini environment keys. `provider-settings` reveals only
credential readiness and variable names. ChatGPT (`chatgpt`/`openai-chatgpt`) uses
Amplifier's OAuth token cache; complete its device login before invoking Stories.
Copilot (`copilot`/`github-copilot`) uses its native token environment; a `gh` login
alone is not enough for this adapter unless its token is explicitly exported.
Stories never starts interactive authentication from a background worker.

```python
api = Stories('/chosen/stories-state', model_env=True,
              provider='anthropic', execution='background')
api.grant_feedback(story, {'max_operations':5, 'timeout_seconds':180}, 'review-grant-1')
viewer = api.start_dashboard(story, revision)
```

Submitted comments queue bounded model responses automatically. Answers and
clarifications use at most two calls. Artifact production adds review against sources
and rendered images, with at most one repair and fresh review: five calls for presentations. Documents review batches of up to three pages, with
at most eleven calls including one repair.
All stages share the operation's time allowance. User drafts and caller highlights
never execute a model. Model settings are captured at operation creation; changing
settings later does not reroute existing work. No credentials are written to story
state. Provider modules own their normal OAuth and rate-limit caches.

For generation, pass explicit source strings, purpose, audience and a grant to
`generate`. Its receipt names an operation and story. `run-operation` drives queued
work; `--execution background` starts an owned worker immediately. Status reads
never restart work. A failed or interrupted operation needs explicit new intent to
spend again; an identical request_id returns its old receipt. A new revision remains
tied to its base, and the user's selected revision does not silently advance.

## Artifact quality review

Install Pango for static text layout (`brew install pango` on macOS). WeasyPrint and
PDFium are package dependencies. Rendering needs no browser download or LibreOffice;
missing prerequisites produce an actionable failure instead of installing anything.
Standard Homebrew library locations are detected on macOS; a custom installation can
set `DYLD_FALLBACK_LIBRARY_PATH` explicitly.

Narrative and design guidance adapts the bundle's audience mapping, evidence discipline,
visual hierarchy and readability guidance. The reviewer sees source texts, the request,
the exact proposed HTML and images of every rendered page. Code checks text bounds,
minimum type size, page counts and blocked resource dependencies. A model cannot
override mechanical failures. Each review records the artifact hash, rendered image
hashes, provider/model, findings and limits. Review is performed again after a repair.

The renderer runs in a cancellable subprocess, at most 40 seconds per attempt, and
cannot fetch external or local resources. It supports at most 12 static pages on a
1280x720 presentation canvas or Letter document pages. It approximates browser layout; it does not certify every viewport.
Model review is labeled as such and is not independent verification or human approval.
The selected model must support native tool submissions and image input for artifact
review. Text-only models can still answer comments but cannot complete artifact production.
If the repair still fails, the operation retains `candidate.html` and `candidate.reviews`
for inspection without committing a revision. Imported artifacts remain unreviewed.

## Export and cleanup

```python
api.export(story, revision, '/chosen/new-output.html')
api.stop_dashboard(viewer['service_id'])
```

Export refuses overwrites and contains the exact chosen artifact without annotations.
Stopping the dashboard cancels comment work it accepted, closes only its own server,
and preserves revisions, comments and drafts. Closing a browser tab does not stop the
service. CLI/API cancellation prevents late commits; a request already sent to a
provider may still be billed. There is no automatic publication or caller wake-up.

## Current limits

- HTML presentations and structured documents. Document PDF and editable Word exports
  are separate outputs with explicit layout limits. PowerPoint and spreadsheet work remain deferred.
- Review sources are supplied text; no repository/session/network research connectors.
- Static previews suppress active content and external assets. Native text anchors
  are Unicode character offsets, scoped to an exact revision. No automatic anchor
  reassociation between revisions.
- Semantic and static rendered-quality review are model judgments with recorded
  limits. Imported artifacts still report these as `not_performed`.
- `needs_input` is a visible clarification outcome. Reply on the same target with
  the missing context to create a new operation; no implicit model continuation.
- One local host and a private loopback viewer; no remote multi-user service.
- Settings and login UI deferred. Library/CLI provider selection is implemented.
- macOS is the validated platform. Other platforms are not advertised yet.

## Live quality evaluation

`uv run python tests/evaluate_quality.py --allow-model --provider openai --store
.work/evaluation --run-id unique-run` runs the historical bundle case study and metrics
scenario. Prepare the selected provider first. This spends model tokens and can take
up to ten minutes; it is separate from normal tests. Use a new run ID for new intent.
Its report separates narrow deterministic checks (requested slide count and retained
historical date/count) from the model's source and image review. A model pass alone is
not a general quality benchmark. Raw results and review artifacts belong in `.work/`.

## Documents

Pass `kind="document"` to `generate` (the default remains `presentation`). The model
submits content rather than CSS: title, subtitle and ordered blocks with stable IDs.
Supported block kinds are heading, paragraph, quote, list and table. Each has `id`,
`kind`, `text`, `items`, `rows`, and `evidence_ids`; unused arrays are empty. Citations
refer to the extracted evidence, with source references included in generated HTML.
Use `create-document` to import uncited structure deterministically. `get-revision`
returns the structure alongside exact HTML; `get-story` returns revision summaries.

Documents have at most 100 blocks and 12 rendered pages. Text blocks are limited to
1400 characters; lists to eight short items; tables to eight rows, five columns and
1600 characters total. Split dense material into smaller blocks. These boundaries
keep the first document renderer predictable; images, equations, inline rich text,
custom branding and arbitrary Word import are not supported.

```python
receipt = api.generate(
    title="Adoption brief", purpose="Explain the evidence and recommended next steps",
    audience="Engineering leaders", sources=source_objects,
    grant={"timeout_seconds": 600, "max_output_tokens": 12000},
    request_id="document-1", kind="document",
)
```

The document viewer defaults to continuous flow. The small **View & comments** tab
reveals controls on hover, click or keyboard focus. It offers paginated view, zoom,
fit width and navigation across both user and agent comments. Comments use existing
margin space when it is sufficient and otherwise float over the page. They never
reserve space or change document geometry. Page/zoom changes preserve the logical
passage and saved drafts. Moving away from an anchored comment closes its composer;
return through comment navigation to reopen it. Whole-story comments remain available.
Native text selection (including a range across blocks) targets exact revision-local
Unicode offsets. Stable block IDs aid position continuity; comments never silently
retarget a new revision, even when IDs remain the same.

### Document export

HTML is the exact retained artifact. `export(..., format="pdf")` produces a Letter
PDF from that HTML using the same static renderer, with text-coverage and bounds
checks. `format="docx"` produces editable paragraphs, lists and tables from the
retained structure using python-docx; no LibreOffice or skill checkout is required.
`get-export` returns base64 bytes, MIME type, revision/source/output hashes, checks
and limitations for adapters. The dashboard provides the same three download choices.
Exports do not include review annotations, and output paths are never overwritten.

Browser pagination approximates print layout. Word may wrap or paginate differently
because its renderer and available fonts differ. Inspect the exported target before
delivery: HTML model review is not advertised as Word visual review. Per-export
visual checks are explicitly `not_performed`; the PDF also reports its mechanical
checks. These are document exports, not general HTML-to-Office conversion.
