# Storytelling coverage

Stories selects writing expertise from the caller's purpose, audience, supplied
sources and latest comment. Use `generate` with `kind="document"` or
`kind="presentation"`; no specialist agent name is required. Read
`storytelling-capabilities` for the same catalog through the library or CLI.

Evidence planning chooses one or two allowlisted approaches. Only their detailed
resources load for composition, source/rendered review and any bounded repair.
The operation's `result.provenance.expertise` records selected IDs, guidance hashes
and upstream paths; `provenance.plan` records the narrative plan. Selection adds no
extra model call. A provenance record proves what was used, not that its output is
correct. Every generated artifact still receives source and rendered review.

## Reference-bundle mapping

Source: `microsoft/amplifier-bundle-stories` at
`8cadef768e61bda01bc5ead7d30ecc90b290f3e6`. Resources below live in
`src/amplifier_smart_tool_stories/resources/expertise/`; the JSON catalog contains
exact upstream paths. The upstream MIT notice ships with the package.

| Reference expertise | Delivered behavior | Resource | Live scenario |
|---|---|---|---|
| storyteller | Grounded narrative and coordinated evidence → composition → review → bounded repair | `general.md`, shared narrative/design guidance, `intelligence.py` | Shared pipeline across scenarios |
| story-researcher | Extract qualified claims from supplied source excerpts before writing; retain exact quote/source identity | `artifacts.py`, evidence stage, `narrative.md` | Every sourced scenario |
| content-strategist | Compare audience-relevant story angles and evidence gaps; produce an editorial plan when requested | `strategy.md` | `strategy` |
| case-study-writer | Challenge, approach, supported outcomes and transferable lessons; feature journeys without a forced success arc | `case-study.md` | `case-study` |
| release-manager | Supplied change descriptions grouped into release/development notes; explain documented migration and missing details | `release.md` | `release` |
| technical-writer | Architecture, responsibilities, mechanisms, constraints and failure modes from supplied material | `technical.md` | `technical` |
| marketing-writer | Accessible feature articles, announcements, newsletter or social-copy drafts with qualified benefits | `marketing.md` | `marketing` |
| community-manager | Contributor-centered spotlights or supplied-update digests; accurate credit and reporting limits | `community.md` | `community` |
| executive-briefer | Concise decision, evidence, trade-offs and next questions without invented ROI | `executive.md` | `executive` |
| content-adapter | Change vocabulary, emphasis and depth while retaining core claims and caveats | `adaptation.md` | `adaptation` |
| data-analyst | Explain measurements with units, baselines, missing values and comparison limits | `data.md` | `data` |
| evaluation-visualizer | Preserve evaluation precision, scenario context, unfavorable results and uncertainty in narrative reports | `data.md` | Data guidance; no dedicated interactive-dashboard scenario |

The six source archetypes are represented as guidance: problem/solution/impact in
general narrative, feature journey in case study, technical deep dive in technical,
release announcement in release, community showcase in community, and velocity
metrics in data. They are not mandatory page templates or fixed success stories.

## Recipe intent and deliberate differences

| Original recipe | What is available | What is not carried over |
|---|---|---|
| `blog-post-generator` | Draft an accessible article from supplied feature material | Repository mining, site publishing and automatic application opening |
| `git-tag-to-changelog` | Draft development/release notes from supplied changes | Git-tag triggers, automatic history access, release creation, commits and PRs |
| `weekly-digest` | Summarize supplied updates and a known reporting interval | Cross-repository discovery, session analysis, scheduling and distribution |
| `session-to-case-study` | Generic case-study writing from supplied project notes | The session scanner, session-specific data interpretation and recipe wiring are excluded |

## Output and validation boundaries

All approaches use existing HTML presentations or structured documents. Documents
can export to HTML, PDF or Word under their documented layout limits. These are not
new native Markdown, email, social-network, spreadsheet or interactive evaluation
dashboard formats. A social thread can be drafted as document sections; this does
not prove platform character limits or perform publication.

Technical explanations currently use headings, prose, lists, quotes and tables in
documents. They are not a full API-reference generator or a code execution/verification
service. The tool does not inspect live APIs, verify external links or execute examples.
Release migration details and code commands require supplied evidence; a version
number alone does not prove compatibility or a breaking change.

Audience adaptation can use source text in a new generation request or a comment
on retained work. Comment revisions retain the artifact kind. Changing kinds requires
a separate generation request with explicit content and target kind. This is not
arbitrary DOCX/PDF/PPTX import or fidelity-preserving conversion.

Spreadsheet creation/calculation and faithful PowerPoint export remain deferred.
Evaluation interpretation is supported guidance; interactive evaluation dashboards,
data-file crawling and sibling data exports are not implemented by this pass.
Network research/source intake remains a separate feature area. Sessions and stale
Context Intelligence integrations are deliberately excluded, not future prerequisites.

`tests/evaluate_storytelling.py` runs nine opt-in source-to-document scenarios using
historical bundle assets. It checks selected expertise, a few requested details and
the recorded source/render review. These assets contain self-reported and conflicting
claims; they are test inputs, not truth oracles. Human examination of the output is
still necessary. Unit tests additionally check allowlisted loading, selective prompt
propagation through composition/review/repair and public catalog availability.
