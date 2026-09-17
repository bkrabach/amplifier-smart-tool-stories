# Using Stories

This is the first implementation slice: HTML generation/import and shared review.
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

Submitted comments now queue bounded model responses automatically. There are two
calls per operation at most: evidence extraction with exact source-quote validation,
then contextual answer/clarification/revision. User drafts and caller highlights
never execute a model. Model settings are captured at operation creation; changing
settings later does not reroute existing work. No credentials are written to story
state. Provider modules own their normal OAuth and rate-limit caches.

For generation, pass explicit source strings, purpose, audience and a grant to
`generate`. Its receipt names an operation and story. `run-operation` drives queued
work; `--execution background` starts an owned worker immediately. Status reads
never restart work. A failed or interrupted operation needs explicit new intent to
spend again; an identical request_id returns its old receipt. A new revision remains
tied to its base, and the user's selected revision does not silently advance.

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

- HTML only; other formats and conversion are not yet implemented.
- Review sources are supplied text; no repository/session/network research connectors.
- Static previews suppress active content and external assets. Native text anchors
  are Unicode character offsets, scoped to an exact revision. No automatic anchor
  reassociation between revisions.
- Semantic and rendered-quality review of generated stories are explicitly
  `not_performed`; quote/reference integrity checks are narrower guarantees.
- `needs_input` is a visible clarification outcome. Reply on the same target with
  the missing context to create a new operation; no implicit model continuation.
- One local host and a private loopback viewer; no remote multi-user service.
- Settings and login UI deferred. Library/CLI provider selection is implemented.
- macOS is the validated platform. Other platforms are not advertised yet.
