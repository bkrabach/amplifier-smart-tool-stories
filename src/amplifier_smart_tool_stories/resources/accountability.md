## Source status and transformation disclosure

Sources and evidence carry kind/source_kind and attribution. `source` means supplied
source text, never proof it is true. `summary` is a caller-supplied summary: do not
claim its underlying original was inspected. `hypothesis` is unverified context.
`preference` guides presentation, not factual support. Preserve attribution and
consequential uncertainty visibly in the artifact. Questions and answers in
continuation are caller context, not new original evidence.

Every submission includes changes {summary, material_changes, omissions, assumptions}
and calculations (empty arrays when none). Compare a revision to its supplied base.
Name material omissions and changed assumptions; preserve unrelated content and
choices. The reviewer must check this comparison, not accept the declaration alone.
Initial generation can use an empty change summary and list relevant assumptions.
Answers and clarifications also provide these fields, with empty arrays if applicable.

Every newly calculated numeric claim must have a calculations entry: id, operation,
inputs [{evidence_id, value}], result, decimal_places, unit. Values/results are plain
decimal strings. Inputs must appear numerically in their cited exact evidence quotes.
Operations: sum (1–20 inputs), difference (first minus second), product (two inputs),
ratio (first divided by second), percent_change (old then new: (new-old)/old*100).
Use decimal_places 0–12, round half up. Preserve inputs and explain the derivation in
reader-facing text when needed to interpret the claim. Do not invent units or treat
arithmetic as proof of causal impact. Unsupported calculations must be omitted with
an explicit limitation or returned as a clarification; do not silently approximate.
Review must fail any derived number missing its calculation, incorrect attribution,
unsupported interpretation, or undisclosed material change/omission.

After a repair, changes must still compare the FINAL artifact to request.base, not
to an intermediate repair candidate. Include the whole requested revision, including
removals made before the repair. Omission disclosure in changes is sufficient unless
the omission changes how readers should interpret a surviving claim. Do not force
internal revision bookkeeping into the artifact. Review must fail a change summary
that only describes the last repair instead of the complete change from the base.
