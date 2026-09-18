# Stories — Vision (DRAFT)

*The intended experience; specific promises live in `contracts/`.*

## What Stories is

Stories turns source material into clear, useful communication without asking the
caller to become a researcher, writer, designer and tool integrator. A person states
the purpose, audience and desired output. An application or agent supplies the same
request as data and receives artifacts it can use.

The expertise travels with the tool. Research, narrative planning, technical and
public writing, executive communication, case studies, community stories, data
presentations and adaptation are parts of one storytelling capability. Presentations,
documents and data-backed outputs serve different audiences; the product is not
defined by a single rendering format.
Stories brings together writing, images, and video to create communication people
can read, present, or watch.

Stories is a Smart Tool: a reusable library with a thin command-line interface and
its own model-backed execution. Its callers use `stories` or import its Python
library without adopting a particular agent environment or supplying specialist
instructions of their own.

The caller retains control of sources, permitted actions and output destinations.
The result identifies the created artifacts, their supporting evidence, missing
information and checks performed. The same documented promises govern the library,
the CLI and any other adapter.

Stories includes a built-in dashboard for reviewing and refining stories with a
calling agent. A person can inspect the actual artifact, give feedback on an
identified revision, explore its sources and review findings, return to earlier
versions, and export the result they reviewed. Supported formats provide appropriate
previews and make preview limitations visible. Provider/model settings and output
preferences use the same public capabilities as the library and CLI.

The dashboard is part of the product and optional to use. A caller may work headlessly,
select the built-in dashboard, or provide its own presentation surface. Work begun
headlessly can open in the dashboard without regeneration or conversation replay.
The person and calling agent share the same story state: submitted feedback,
answers and changes are observable to the caller; unsubmitted drafts remain distinct
from instructions. Recording an action does not promise to wake the calling agent.
Existing valid authority can cover requested refinement without repeated approval.

The material fills the review surface; review controls stay secondary. Opening a
comment never moves or resizes the material. An optional review overlay lets the
person select text or an element directly and leave a comment,
or comment on the story overall. The caller can also highlight material and attach
questions or explanations for the person. These annotations belong to shared review
state, not the document, and are absent from artifact exports. Stories' internal
intelligence interprets submitted comments in context and can answer, refine or ask
for clarification within existing authority without a round trip through the caller.
The person can keep reviewing while work proceeds; updates preserve their position,
selection, open comment and unfinished typing. A new revision is quietly made
available without forcing a disruptive refresh. The caller can observe the resulting
comments, actions and revisions later.

## Principles

### 1. **Evidence sets the limits of the story.**

Numbers, attribution and impact claims stay tied to sources. Missing evidence remains
visible; a persuasive narrative does not turn estimates into measurements.

### 2. **The expertise lives inside the tool.**

The caller specifies an outcome rather than rehearsing specialist prompts or routing
agents. Stories owns the research-to-artifact workflow and discloses its limits.

### 3. **The library is the product.**

Every capability is callable without the command line or dashboard. Both adapt
inputs and outputs rather than owning hidden functionality. Human participation
and agent-driven work operate on the same identified stories and revisions.

### 4. **Model use is deliberate.**

Smart operations use the embedded agent runtime. Deterministic operations need no
model credentials. Missing configuration produces a remedy, not a disguised fallback.

### 5. **Creation does not imply publication.**

Making a story does not implicitly open applications, start a service, modify unrelated
repositories, install software or send content to an audience. An explicitly selected
dashboard can start or update within granted presentation scope; opening a viewer
remains a separate choice. Network research and model use have explicit scope;
publication is a distinct decision.

### 6. **Quality claims name their evidence.**

A file existing is not the same as a useful story. Structural checks, source review
and visual review answer different questions and remain distinguishable.

### 7. **Portability preserves capability, not host assumptions.**

Stories works without assumptions about a caller's local paths, session layout
or deployment site. Unsupported outcomes fail explicitly.

### 8. **Review continues the same work.**

Feedback targets what the person saw. Refinement preserves unaffected choices and
earlier revisions, and export identifies the delivered version. Viewing retained
artifacts requires no model credentials. Closing the viewer does not erase work
or imply that execution has stopped; stopping releases owned live resources while
preserving retained results for a later return.

## What this deliberately resists

- A bag of converters presented as storytelling — synthesis is part of the product.
- A tool that only works inside one configured agent environment.
- Invented metrics, unsupported impact claims and misleading validation badges.
- Automatic deployment, PR creation or runtime installation hidden in generation.
- Universal file conversion or support for every platform without verification.
- Building a general-purpose agent platform instead of a storytelling tool.
- Requiring a full document or slide editor before people can review and refine work.

## How you can tell it is working

- A caller obtains a usable artifact in their own environment without importing
  Stories expertise into their own prompts.
- A reader can trace factual claims to sources and see what remains unknown.
- An application consumes the result without extracting paths from conversational prose.
- An operator can inspect and check supported artifacts without model credentials.
- A maintainer can distinguish verified support from planned capabilities.
- A person reviews an artifact in the dashboard, submits targeted feedback, and the
  calling agent continues from that exact revision without screen scraping.
- A person returns to earlier work and exports the reviewed version without losing
  revisions or accidentally applying an unsubmitted draft.

## Changelog

- **2026-09-16** — Added the optional built-in review workspace, shared caller state,
  provider settings, revision continuity and explicit presentation lifecycle.
- **2026-09-09** — First draft; no lock or implementation claim.
