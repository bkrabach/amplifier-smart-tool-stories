# Internal execution contract — v1 (DRAFT)

**Who builds against this:** Maintainers implementing Stories' library, embedded
intelligence, source access, artifact production and review mechanisms.

## What it looks like

The intelligence layer works through library-controlled capabilities to inspect
permitted material, compose artifacts and obtain review evidence. The library
validates proposed results before reporting completion to the caller. This example
defines obligations, not internal tool names or a fixed sequence of specialists:

```text
Authorized request → permitted evidence → composition → rendered artifact → review
Model proposal → library validation → public outcome
Artifact changes → affected review becomes stale → applicable checks run again
```

Right: a review identifies the exact artifact revision it inspected.
Wrong: a model edits a slide after rendering and submits the old visual review as
proof that the changed slide was checked.

## Purpose

Make the public [caller-interaction](caller-interaction.v1.md),
[invocation](invocation.v1.md) and [storytelling](storytelling.v1.md) promises
enforceable without freezing an internal tool catalog or adopting a bundle's host
assumptions. Internal tools are implementation interfaces, not automatically public
commands. Externally useful domain capabilities remain library-accessible.

The [media and delivery contract](media-delivery.v1.md) extends these
obligations to retained assets, rendering budgets, packaging and timed exports.
The [storyboard exploration contract](storyboard-exploration.v1.md) extends them to
alternative directions and structured visual sequences.

## Core (the teeth)

1. **The library owns execution authority.** The embedded runtime receives only
   capabilities and material permitted for the operation. Library-controlled
   boundaries enforce source access, destinations, provider disclosure and work
   limits; prompts alone are not enforcement. Instructions embedded in sources or
   generated artifacts are data, not authority. Internal specialists and subprocesses
   inherit the same restrictions and cannot widen them or multiply the work allowance.
2. **Intelligence has the means to do and inspect its work.** Supported workflows
   provide appropriate access to source evidence, composition and revision,
   rendering, inspection and structured submission or limitation reporting. The
   implementation may combine or split these capabilities. It must not require the
   caller to fill in internal production steps or accept final prose as a substitute
   for a requested artifact. General shell or filesystem access is not implied by
   embedding an agent; any execution mechanism must preserve the same enforced scope.
3. **Evidence is identifiable and traceable.** Inspected material receives stable
   references to source identity, relevant content or location, and applicable
   version information. Supplied context, source observations, derived calculations
   and model interpretation remain distinguishable. Before factual composition, the
   workflow identifies supporting evidence and missing information; further research
   can extend that record within scope. Claimed observations must correspond to
   material actually made available to the responsible execution step. Fabricated,
   inaccessible or mismatched references cannot pass as observed evidence.
4. **Provenance survives transformation.** Claims retain their supporting references
   and qualifiers through synthesis, revision and format adaptation. Calculated
   figures retain their inputs and derivation. Conflicts and unsupported conclusions
   remain visible rather than becoming stronger claims through rewriting. Changed
   source material is detected where it affects reuse: the workflow either uses an
   identified retained version or reports the need to refresh evidence and affected
   checks. A resolving citation is not proof that its content supports the claim.
5. **Artifact identity binds production and review.** Drafts, rendered artifacts and
   accepted revisions are distinguishable. Checks identify their exact inputs and
   applicable artifact version; edits invalidate affected checks. Conversion cannot
   inherit a visual pass from another format without checking its own rendering.
   Unaffected evidence may be reused when its applicability is established. Earlier
   accepted revisions are not silently overwritten by internal editing.
6. **Completion is validated outside model prose.** A structured submission identifies
   produced artifacts, evidence, checks and limitations. Library code verifies the
   declared outcome, required fields, reference integrity, output scope, artifact
   existence, nonempty content and format before publishing a completed result.
   Required checks must concern the submitted revision. Missing or invalid artifacts
   cannot become success because the model says they are done. Documented partial
   outcomes enumerate completed and missing parts; other incomplete work fails.
   Storyboard validation includes panel identities, ordering, asset references and
   the targeted direction/revision. A planned visual is not a produced asset; an
   intentionally unillustrated panel is valid only at a fidelity that permits it.
   One completed direction is not a completed two-direction comparison. Preserve
   useful completed work while identifying missing candidates and failed checks.
7. **Review reports its actual strength.** Structural checks, source-fidelity review
   and rendered usability are separate findings. Records identify what was inspected,
   the method used, its result and limits; skipped, failed and stale checks are not
   passes. Model review is labeled as model review, never human approval or independent
   proof of correctness. Mechanical reference checks do not certify semantic support.
   Capability-specific acceptance criteria determine which checks are required;
   absent optional review remains disclosed.
8. **Work is bounded and stoppable.** Execution enforces documented finite limits
   appropriate to model use, source inspection, tools and rendering. Retries, repairs
   and internal delegation share the operation's allowance. Exhaustion, interruption
   and cancellation produce explicit outcomes and preserve valid completed work.
   Late results cannot commit into a cancelled or superseded operation. Recovery
   distinguishes already committed work from uncertain external calls and requires
   valid authority before new spending; a checkpoint is not permission to restart.
   Alternative generation, image generation, review and repairs share the authorized
   operation allowance. Independent candidates cannot multiply that allowance.
9. **Resources and publication remain controlled.** Imports and deterministic paths
   do not boot intelligence. Credentials remain outside source records and artifacts.
   Temporary work, retained state and requested outputs use their designated locations;
   cleanup releases owned resources without deleting caller material or committed
   results. Runtime work does not implicitly install dependencies, open applications,
   change unrelated repositories, start services or publish content. Missing
   prerequisites return a remedy under the invocation contract.
   The internal model does not gain presentation authority by generating content.
   A caller-selected dashboard service is managed outside its tool scope under the
   [dashboard contract](dashboard.v1.md); generated artifacts remain isolated from
   workspace credentials and controls.

## Stories acceptance checks

These are proposed contract checks, not work items or claims of conformance:

- Source text and model tool arguments attempting to expand access, disclosure or
  destinations are rejected by executable boundaries, independent of prompt compliance.
- Unsupported evidence IDs, source-version mismatches and invented observations
  cannot be accepted as valid provenance. Valid references to misleading evidence
  still fail the independent source-fidelity acceptance scenario.
- A derived figure retains its inputs and calculation; revision and conversion
  preserve required qualifiers and disclose material omissions.
- Editing an artifact after inspection prevents its earlier affected checks from
  being reported as current. A new-format artifact does not inherit visual approval.
- Empty, missing, malformed, wrong-format and out-of-scope outputs fail submission;
  a model's successful final message cannot bypass those checks.
- Unperformed review is disclosed, model review is labeled, and human approval
  cannot be invented by an internal submission.
- Retry or specialist fan-out cannot increase a shared allowance. Cancellation
  prevents late commits, and recovery does not silently repeat uncertain spending.
- Fail an alternative or image-generation step and report incomplete requested work
  without discarding valid candidates or treating a prompt as an image. Verify exact
  panel, asset and direction/revision targets independently of model prose.
- Provider-free deterministic paths work without runtime initialization; failures
  clean up owned temporary resources and preserve committed and caller-owned data.

Scripted models can test enforcement and failure paths; they cannot establish
story quality. Source fidelity and rendered usability need independently reviewed
examples as required by the storytelling contract.

## What v1 deliberately does NOT freeze

- Internal tool names, schemas, prompts, specialist roles or orchestration topology.
- Renderers, evidence storage, checkpoint mechanisms or artifact-version encoding.
- Exact budget units, provider configuration or runtime integration details.
- Format-specific review thresholds and supported breadth; these require concrete
  capability acceptance evidence before being advertised.

## Changelog

- **2026-09-18** — Extended validation and shared bounds to storyboard alternatives
  and image generation; partial comparisons remain explicitly incomplete.
- **2026-09-16** — First draft of internal execution obligations. No tool catalog,
  implementation choice or bundle parity claim is frozen.
