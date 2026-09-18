# Storyboard exploration contract — v1 (DRAFT)

**Who builds against this:** People developing visual stories, calling agents and
applications, and maintainers of storyboard generation and review.

## Purpose

Help a person develop an incomplete idea into a useful visual sequence without
requiring storyboarding expertise. Shared skills in audience, narrative, visual
explanation, pacing and evidence serve different media and purposes; no particular
demo, campaign or film structure defines the capability.

This extends [caller interaction](caller-interaction.v1.md),
[grounded storytelling](storytelling.v1.md), [dashboard review](dashboard.v1.md),
[media and delivery](media-delivery.v1.md) and
[internal execution](internal-execution.v1.md). The
[invocation contract](invocation.v1.md) governs every public capability. These are
intended behaviors, not claims that storyboard generation or exports exist today.

## What it looks like

```text
Rough idea and context → provisional brief and open choices
User requests alternative approaches → two meaningful candidate sequences
Compare outlines or visual panels → focus, discuss and explicitly choose
Chosen direction → refined sequence with retained revision history and assets
```

A person can begin with text, supplied visuals or both. They can develop a chosen
direction directly or revisit alternatives. The example is not a mandatory sequence
of approval gates, an API schema or a promise of finished-video production.

## Core (the teeth)

1. **The tool helps develop intent.** Usable rough ideas and explicitly supplied
   conversation context are valid inputs. Stories distinguishes supplied intent,
   assumptions and open choices, and offers concrete possibilities. Focused questions
   address gaps that materially change the work; the person need not complete an
   intake form, name specialists or design the alternatives. The caller retains the
   conversation, with public questions and continuation records rather than private
   runtime transcripts. A completed brief is not a prerequisite to useful exploration.
2. **Alternative exploration follows user intent.** Ordinary creation develops one
   direction. A request to explore different approaches or compare alternatives,
   conveyed naturally through the caller, activates alternative generation; no special
   terminology is required. An incomplete brief or uncertain user may prompt lightweight
   suggestions or an offer to compare, not automatic multi-direction generation.
   Once alternative exploration is requested, the default is two directions under
   the same supplied intent and constraints. Differences concern narrative,
   viewpoint, visual explanation, sequencing or another relevant creative decision;
   styling alone is not misrepresented as a different story approach. Each direction
   makes its approach and tradeoffs inspectable in the sequence itself. Clearly chosen
   direction and explicitly scoped single-direction work do not require forced branching.
3. **Fidelity serves the decision.** Text outlines, partly illustrated sequences and
   visual storyboards are valid declared outcomes. Images are optional per panel.
   Visuals may be supplied, generated, derived or still planned, with those states
   visible under the shared media contract. Missing required visuals are disclosed;
   an outline does not silently fulfill a request for an illustrated deliverable.
   No rigid outline-to-image progression or mandatory image spending is implied.
4. **Structured content survives presentation.** Retain ordered content, stable panel
   identities and exact asset references independently of one viewer layout. Optional
   dialogue, narration, action, motion, camera or timing notes serve the selected
   medium; film terminology and timing are not mandatory for every storyboard.
   Reordering preserves panel identity. Removed or changed material retains historical
   context, and annotation reassociation is shown only when established. The same
   retained content can support different views without regenerating the story.
5. **Alternatives and revisions are distinct.** Each direction has its own revision
   history. Comparing or focusing does not select; selection does not mean acceptance
   or additional execution authority. The other directions remain available. Feedback
   targets identified work and preserves choices outside its scope. Combining parts
   of alternatives records the resulting direction/revision and its source revisions
   without overwriting originals. Shared-intent corrections follow the caller contract's
   update-or-supersede behavior rather than silently changing sibling histories.
6. **Creative proposals are not factual evidence.** Fictional scenes, metaphors and
   imagined possibilities may be created as such. Claims about real people, products,
   measurements or outcomes retain source support and qualifications. A generated
   product-like image cannot establish observed product behavior. Missing factual
   evidence need not block unrelated creative exploration, but cannot be invented.
7. **Review evaluates the requested work.** Findings distinguish structure, source
   fidelity, narrative coherence, useful alternative choice and rendered usability.
   Inspect ordering, visual continuity and the relationship of words and visuals at
   the requested fidelity. Valid panel references do not prove a compelling sequence;
   model judgments do not establish independent audience understanding. Timing notes
   or static previews do not establish actual animation, audio or playback quality.
8. **Completion and delivery are explicit.** A result identifies its brief, direction,
   revision, fidelity, available visuals, missing material and checks. If one of two
   requested directions fails, preserve useful completed work and disclose incomplete
   exploration under documented partial-result semantics. All candidates, images,
   repairs and review share the authorized allowance. Portable delivery preserves
   structured content and assets under the media contract; storyboard completion is
   distinct from producing a finished film, animation, comic or interactive experience.

## Contract checks

Proposed behavioral checks, not claims of implementation or current conformance:

- From rough context, develop one direction without requiring terminology or a completed
  questionnaire. Uncertainty alone does not generate alternatives. Resolve a
  consequential ambiguity through a correlated question and answer.
- When the person requests alternative approaches, produce two substantively different
  outlines unless scoped otherwise. Honor a fixed direction without forcing alternatives.
  Reject cosmetic-only variants
  presented as different narrative approaches; compare against the same requirements.
- Compare text-only, mixed and illustrated boards. Distinguish deliberate missing
  visuals from failed required production, and preserve exact assets on reopening.
- Focus either alternative without selecting it, choose explicitly, retrieve the
  decision through a fresh caller and refine the named revision. Retain the sibling.
- Reorder, revise and delete panels; retain historical annotation targets and accepted
  content. Combine directions with traceable bases rather than overwriting either.
- Correct shared intent and mark affected work updated or superseded without silently
  regenerating it or weakening execution bounds.
- Preserve evidence limits while creating explicitly fictional or conceptual material;
  never treat an illustration as a documented customer outcome or product observation.
- Exercise different purposes and media with independent human review of meaningful
  alternatives and sequencing. Disclose absent audience-comprehension evidence.
- Exhaust a shared allowance or fail a candidate and return an honest incomplete
  outcome. Verify exported structured content, order, notes and required asset bytes.

## What v1 deliberately does NOT freeze

- Public API names, serialization schema, storage layout or identity encoding.
- A taxonomy of specializations, fixed narrative templates or a single visual style.
- Image providers, generation mechanisms, rendering technology or exact export formats.
- Finished video, speech synthesis, animation, branching playback or downstream editor
  integration. These are separate capabilities, not implied by storyboard support.
- Generating alternative documents or presentations. Their comparison views share the
  dashboard model, but alternative generation for those formats remains deferred.

## Changelog

- **2026-09-18** — First behavioral draft for general-purpose storyboard exploration,
  progressive visual detail, meaningful alternatives and retained structured sequences.
