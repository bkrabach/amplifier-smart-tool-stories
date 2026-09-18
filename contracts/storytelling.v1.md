# Grounded storytelling contract — v1 (DRAFT)

**Who builds against this:** Authors providing source material, readers relying on
the story's claims, and applications consuming generated artifacts and evidence.
The Stories bundle is the expertise source, not an unverified promise of parity.

## What it looks like

A source includes a measurement and its limits; the output retains both.
This synthetic pair illustrates the distinction and is not execution evidence:

```text
Source: "In this benchmark, median duration fell from 10 seconds to 8 seconds."
Right: "20% lower median duration in this benchmark", citing the supplied source.
Wrong: "All customers are 20% more productive", citing that same source.
```

## Purpose

Stories helps people communicate without making the evidence stronger than it is.
It delivers an artifact suitable for the requested audience and supported format.
Its result makes factual support, omissions and review limits inspectable.
The [caller-interaction contract](caller-interaction.v1.md) defines how callers
request and revise that result. The
[internal execution contract](internal-execution.v1.md) defines how production,
evidence and checks remain tied to the submitted artifact.

The [media and delivery contract](media-delivery.v1.md) applies these
requirements to images, clips, speaker notes and narrated presentation exports.

## Core (the teeth)

1. **A request describes the communication goal and audience.** Stories accepts
   source content rather than requiring callers to supply specialist prompts or
   understand the source bundle's agent names.
2. **Factual generation follows evidence extraction.** Before writing, the workflow
   identifies supported facts, source references and missing information.
   A missing required input produces a clear failure or a documented partial outcome.
3. **Factual claims preserve their support and limits.** Numbers, dates, attribution,
   quotes and impact claims trace to source evidence; estimates retain qualifiers.
   Unsupported measurements or conclusions are omitted or identified as unknown,
   not substituted with impressive-sounding qualitative claims.
4. **The result exposes provenance.** A caller can connect factual claims to the
   supplied or explicitly gathered sources and distinguish original evidence from
   model interpretation; a citation's existence alone is not proof of support.
5. **Supported requests produce the requested kind of artifact.** The tool checks
   that the artifact exists, is nonempty and matches its declared format, and reports
   its location. Unsupported formats or workflows fail explicitly rather than
   silently returning another format or a prose description of a nonexistent file.
6. **Review states what it actually checked.** Structural validity, evidence support
   and rendered usability are separate findings. Unperformed review is disclosed;
   no structural pass is presented as proof of truth, readability or visual quality.
7. **Completion is explicit.** A partial outcome is valid only when the capability
   documents it and lists successful and missing parts; otherwise it is failure.
   Broken, empty or missing requested artifacts do not count as completed work.
8. **Support is advertised from evidence, not inventory.** A published capability
   lists its supported outcomes, source inputs, dependencies and known limits.
   Copying an agent prompt, template or converter does not establish feature parity.

## What v1 deliberately does NOT freeze

- Initial output format or release breadth — promote when the owner approves a
  capability slice and its format-specific acceptance examples.
- Exact source/claim schema and artifact bundle layout — promote when a real
  consumer demonstrates the fields needed for traceability.
- Brand styles and narrative templates — promote when a chosen output requires a
  specific visual or editorial contract.
- Automated semantic or visual grading thresholds — promote when representative
  fixtures and a human-approved oracle distinguish right from wrong.

## Stories acceptance checks

These check Stories-specific evidence and artifact behavior. They supplement the
upstream Smart Tools conformance kit rather than describing what that kit proves.

- Clauses 1–2: a goal, audience and source payload reach evidence extraction before
  generation; missing required evidence follows documented failure behavior.
- Clauses 3–4: a reviewer compares every test claim to its referenced source and
  rejects the wrong example above even though its reference resolves.
- Clauses 5 and 7: malformed, empty, absent and wrong-format artifacts never pass
  as completed requested outputs; partial results list what is missing.
- Clause 6: omitted checks remain visibly unperformed in the result.
- Clause 8: advertised capabilities have matching accepted scenario evidence.

Source-fidelity review needs recorded reviewer judgments; layout needs rendered
evidence. Neither is replaced by schema checks or a model grading its own output.
