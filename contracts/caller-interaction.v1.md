# Calling agent interaction contract — v1 (DRAFT)

**Who builds against this:** Calling agents, Python applications, CLI adapters,
and people creating and revising stories through them.

## What it looks like

The caller owns the conversation and selects presentation for the person. Stories owns
research within permitted scope, synthesis, artifact production and review.
The caller requests an outcome without managing internal specialists or sessions.
This illustrates behavior, not command names or a published schema:

```text
Caller → purpose + audience + sources + constraints + authority
Stories → identified artifact revision + evidence + review findings + limitations
Caller → “shorten this for executives,” targeting that revision
Stories → new revision, preserving supported claims and identifying material changes
Dashboard → submitted feedback on an identified revision → caller-visible receipt
```

Right: return a focused question when two supplied figures conflict and the choice
matters to the requested story. Wrong: silently choose the more persuasive figure.
Right: continue from the reviewed revision. Wrong: require the caller to recover an
internal Agent transcript or silently revise a different artifact.

## Purpose

An independent caller can discover, request, inspect and revise supported outcomes
through the public library and CLI. This contract extends the
[invocation contract](invocation.v1.md); artifact and evidence quality remain governed
by the [storytelling contract](storytelling.v1.md). Internal execution obligations
live in [internal execution](internal-execution.v1.md). The built-in review workspace
and its lifecycle are defined in the [dashboard contract](dashboard.v1.md).

Supplied media, asset choices and portable delivery extend this boundary under the
[media and delivery contract](media-delivery.v1.md).

## Core (the teeth)

1. **Requests describe communication outcomes.** Supported capabilities document
   their required inputs, available outputs, constraints, prerequisites and model
   use. The caller supplies purpose, audience and source material, with optional
   context such as tone, length, brand guidance and desired emphasis. It need not
   name specialists, provide workflow prompts or orchestrate production stages.
   Stories reports unsupported requirements rather than silently substituting them.
2. **Context crosses the boundary explicitly.** Stories assumes no access to the
   caller's conversation, filesystem or model session. It accepts source content
   and, where supported, explicitly scoped references. Caller summaries, hypotheses
   and preferences are useful context but remain distinguishable from original
   evidence. Unavailable underlying sources and consequential assumptions stay
   visible; a supplied summary does not establish that its cited originals were read.
3. **Authority belongs to the caller.** Source access, research scope, output and
   retained-state destinations, model configuration, permitted disclosure and work
   limits are supplied or explicitly selected through documented configuration.
   Existing valid authority can cover creation and follow-up without repeated human
   approval. Source content, model suggestions and retained state cannot expand it.
   A missing prerequisite or insufficient authority produces an actionable result.
4. **Results are usable without private state.** Public results identify the request,
   operation, artifact revision and completion outcome, and expose accessible artifact
   references, supporting evidence, material assumptions, limitations and review
   findings. Callers can retrieve the supported review material through public
   capabilities. Internal reasoning and Agent session identifiers are not required
   to interpret, present or continue the work. Returning a preview does not imply
   that a person saw or approved it.
5. **Unresolved outcomes identify the next useful action.** Missing input, conflicting
   evidence, unsupported requests, missing access, exhausted resources and execution
   failure are distinguishable. A question identifies the affected operation or
   revision, explains what is needed and accepts a correlated answer through the
   public interface. No inaccessible interactive prompt is required. Work dependent
   on an answer pauses; safe independent work may continue within existing authority.
   A limited search establishes only what was found within the inspected scope.
6. **Revisions preserve their targets and unaffected choices.** Feedback names its
   base revision; ambiguous references return a question and stale references never
   silently target newer work. Refinement produces an identified new revision,
   preserves earlier accepted revisions for the documented retention period, and
   preserves choices outside the requested change. Adaptation to another format or
   audience retains evidence and qualifiers and discloses material omissions or
   changed assumptions. An intended omission is distinguishable from lost content.
7. **Continuation does not require conversation replay.** Public retained context
   includes enough intent, choices, evidence and revision relationships to continue
   supported work with a fresh caller. Retention and unavailable or expired context
   are documented. An answer continues the identified need; a new refinement is a
   distinct operation. Request identity and documented retry behavior distinguish
   exact retries from new intent: acknowledged retries do not silently repeat model
   spending or artifact creation, and conflicting reuse is reported. An interrupted
   call with uncertain completion reports that uncertainty before further work.
8. **Execution and observation are distinct.** Reading status, artifacts or review
   findings does not initiate generation. Long-running work exposes status and
   cancellation through the public boundary; cancellation acknowledgement is distinct
   from completed cleanup. Completed artifacts and retained revisions survive
   cancellation under the documented retention policy. Only owned live resources are
   released. A pending question or saved operation does not imply a background worker,
   caller notification or automatic restart; any such support is explicitly documented.
9. **Adapters preserve public semantics.** The library owns every externally useful
   capability and the CLI exposes it without exclusive business logic. The built-in
   dashboard and host presentation adapters use the same revision, question and decision semantics;
   decisions it accepts are observable through the public boundary. Deterministic
   reads and supported deterministic edits or exports require no model session.
   Creation, approval and publication remain separate actions.
10. **Dashboard handoff continues the same story.** Headless work can be opened in
    the built-in dashboard by public story/revision identity, without regeneration.
    A caller can read current intent, selected revision, submitted feedback, pending
    questions, operation status and export references through public capabilities.
    The dashboard shows the same state. Replacing a presenter or caller preserves
    accepted actions; no browser session or internal Agent transcript is required.
11. **Drafts, submissions and execution are distinguishable.** Saved unsubmitted
    feedback is labeled as draft context and never initiates refinement. Public review
    state exposes saved drafts and their targets so a caller can avoid conflicting
    changes; it does not imply access to keystrokes not yet saved. An accepted
    submission returns an identified receipt and reports whether it started work
    within existing authority, is waiting for input/access, or awaits caller action.
    Reading or redelivering that receipt never repeats generation. Callers can retrieve
    meaningful changes since their last observation, with ordered identities and
    explicit history gaps; a current snapshot retains pending needs. Acceptance,
    execution completion, notification delivery and caller wake-up remain distinct.
12. **Settings changes have explicit scope.** Provider/model and supported output
    preferences are available through library, CLI and dashboard. The caller can
    inspect redacted effective settings and whether changes are process-local or
    persistent. Changes apply to identified future operations and do not silently
    alter running work or previous artifacts. Settings changes neither grant new
    source/disclosure authority nor initiate model spending. Login and connection
    tests are explicit operations, with model use and limitations documented.
13. **Review annotations flow both ways.** The caller can create highlights and
    comments for the person, and retrieve comments and replies entered through the
    dashboard. Annotations identify their author, story, reviewed revision and
    selected material or whole-story target. They remain separate from artifact
    content. Submitted user comments can be handled directly by Stories' internal
    intelligence within existing authority, without caller mediation or a separate
    change-request action. Meaning comes from the comment and supplied context:
    answer, explanation, refinement or clarification. Caller highlights do not by
    themselves authorize model work or count as human feedback. Public state connects
    comments to responses, operations and resulting revisions so a returning caller
    can see what occurred and avoid repeating it.

## Stories acceptance checks

These are proposed contract checks, not work items or claims of conformance:

- A caller using only public documentation creates, inspects and revises a supported
  artifact through both library and CLI without internal prompts or session access.
- A caller summary with an inaccessible original remains labeled as supplied context;
  the result never claims to have inspected that original.
- Conflicting source figures produce a focused question or an explicitly qualified
  outcome; a correlated answer continues the affected work with stdin closed.
- Revising an older identified artifact either intentionally branches from it or
  reports a conflict; it never silently changes the latest revision instead.
- A fresh caller continues from public retained context. An exact acknowledged retry
  reuses its outcome; changed input with the same identity reports a conflict.
- Existing valid authority permits covered follow-up. Expired authority, exhausted
  resources and interrupted execution produce distinct actionable outcomes.
- Cancellation reports actual cleanup while preserving committed results and
  caller-owned resources; reading status never launches or resumes model work.
- A headless result opens in the dashboard with the same revision and evidence;
  submitted feedback is retrievable by a fresh caller without screen scraping.
- Saved drafts remain visible as drafts and survive refresh without triggering work.
  Submission, retry and observation each preserve the actual target and do not
  duplicate generation; a history gap does not hide an outstanding question.
- Provider/output settings changed through either adapter have the same documented
  scope, preserve running work and drafts, and reveal no credential values.
- A caller-created highlight appears on the identified material. A user comment
  receives an answer or refinement without another caller invocation when covered
  by existing authority; the caller later retrieves the comment and actual outcome.
  Re-reading annotations does not execute them or imply human approval.

These checks supplement the invocation and storytelling checks, not replace them.

## What v1 deliberately does NOT freeze

- Capability names, signatures, schemas, identity encoding or storage layout.
- Retention duration, retry window, polling versus events or background execution.
- Dashboard layout/framework, notification mechanism, remote service or additional adapter.
- Initial formats and revision granularity; each advertised capability must define
  its supported round trip and limitations before release.

## Changelog

- **2026-09-16** — Added built-in dashboard handoff, draft/submission distinctions,
  observable actions and shared settings semantics; concrete APIs remain open.
- **2026-09-16** — First behavioral draft separating caller ownership and continuity
  from internal intelligence. No interface lock or implementation claim.

## Implemented continuation and acceptance semantics

Initial-generation questions use `answer_question(operation_id, text, grant, request_id)`.
A new bounded operation retains the same story, original provider and correlated
question/answer history. Explicit fresh authority covers the continuation; one answer
is accepted per question, and exact retries never dispatch again. Comment questions
continue through `respond`. Both preserve the pending question's target/context.

Sources carry kind and attribution through extracted evidence. Revision submissions
include change summaries, material changes, omissions and assumptions; source/rendered
review compares them to the base. Arithmetic derivations retain quoted inputs and
verified decimal results. Model review of coverage and interpretation remains fallible.

`accept_revision` records explicitly conveyed person acceptance of a revision/hash
without changing selection, review results, artifact bytes or future authority.
