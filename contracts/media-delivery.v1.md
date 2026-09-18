# Shared media and artifact delivery contract — v1 (DRAFT)

**Who builds against this:** Authors supplying or generating media, people reviewing
documents, presentations and storyboards, callers requesting exports and maintainers
implementing asset handling.

## Purpose

Images and clips can carry part of a story's explanation. They must survive creation,
review, revision and delivery without losing their identity or silently changing
quality. This extends [caller interaction](caller-interaction.v1.md),
[dashboard review](dashboard.v1.md), [grounded storytelling](storytelling.v1.md) and
[internal execution](internal-execution.v1.md). The [invocation contract](invocation.v1.md)
continues to govern library/CLI parity, dependencies and external actions.
Image generation is a shared capability across these formats, not a storyboard-only
facility. The [storyboard exploration contract](storyboard-exploration.v1.md) defines
structured sequences and their requested levels of visual detail. These are intended
behaviors; supported providers, operations and exports require implementation evidence.

## Shared image creation and retention

1. **Generation belongs to the shared library boundary.** Documents, presentations
   and storyboards use the same public media capabilities for supported image creation
   and variations. Format-specific composition chooses and places assets without
   hiding a separate generation or configuration workflow inside a viewer.
2. **Image generation has explicit configuration and authority.** Supported providers,
   reference-image inputs, disclosure destinations, prerequisites and work limits are
   documented. Existing explicit authority may cover creation and follow-up; neither
   a planned visual nor access to a text model implicitly grants another provider
   access or spending. Missing support returns a remedy, not a fabricated asset.
3. **Visual states and provenance remain distinguishable.** Supplied, generated,
   derived and planned visuals identify their status and applicable origin,
   attribution, generation inputs and transformations. A prompt or desired scene is
   not an image. Illustrative output is not evidence of a real event, customer outcome
   or product observation. Retained provenance excludes credentials and access secrets.
4. **Reviewed visuals retain actual content.** Store produced image bytes and bind
   exact assets to artifact revisions. Reopening, comparing and exporting retained
   work do not regenerate images. A variation or replacement creates identified new
   content while earlier revisions retain their originals; affected checks become
   stale and human acceptance does not transfer. Generation and repairs remain
   inside the operation's shared allowance under the internal execution contract.

## Media and portable HTML delivery

1. **Media enters explicitly and is retained by identity.** Supported images and
   videos are supplied through the public boundary and retained independently of
   HTML. Revisions identify exact asset content and its attribution; replacing an
   original file does not change an earlier revision. External URLs do not imply
   permission to fetch them. Unavailable assets and unsupported formats are reported.
2. **Assets are usable in the review surface.** Authorized story images and clips
   can load without granting generated HTML arbitrary filesystem, network, settings
   or credential access. Supported video has playback controls, a poster/fallback
   and caption or descriptive context. Supplied caption tracks are retained where
   supported. Blocked or unsupported media is visible as a limitation, not silently
   removed. Viewing retained media requires no model credentials or generation.
3. **Size informs a choice, not a silent transformation.** Substantially large images
   produce an actionable warning using encoded size and dimensions relative to their
   intended display. The caller can retain the original, authorize resizing a copy,
   or use separate export assets. Originals remain retained; derivatives identify
   their source and transformation. No resize, recompression or other quality change
   is implicit in review or export. Existing explicit transformation choices can be
   reused within their scope without repeated approval.
4. **Limits protect operations without defining an arbitrary output ceiling.**
   Parsing, decoded image dimensions, storage and rendering have documented,
   operation-appropriate resource budgets and actionable failures. A fixed small
   total HTML limit must not stand in for media handling. Media bytes are accounted
   for separately from markup; packaging is available when embedding is unsuitable.
   This does not promise unlimited inputs or execution.
5. **Delivery choices are explicit and portable.** Single-file HTML embeds supported
   images and reports expected size. HTML with separate assets uses relative paths;
   a ZIP export includes the entry HTML, required assets and extraction/opening
   instructions. Presentation delivery preserves slide-by-slide navigation outside
   the review workspace; document delivery remains a scrolling document.
   Video remains a separate asset by default. A package advertised as
   offline works after extraction without Stories, its original paths or a local
   server, on the documented supported browsers. External dependencies require an
   explicit choice and disclosure; they cannot masquerade as included assets.
6. **Export binds the complete deliverable to the selected revision.** Results
   identify the HTML, asset set and any authorized derivatives, plus format and
   limitations. Required assets are verified before completion; a ZIP with broken
   references is not a successful portable export. Packaging retained material is
   deterministic and requires no model. Export excludes review annotations and
   credentials and does not publish or overwrite without existing authority.
7. **Review distinguishes layout, playback and meaning.** A static poster review
   does not establish successful playback, audio, caption synchronization or an
   understanding of the clip. Findings identify what was actually inspected.
   Claims about media content require inspected evidence, not merely a filename or
   supplied description. Static output formats use a disclosed poster/caption/link
   fallback where supported, never an implied playable video. Asset changes
   invalidate affected checks and do not inherit human acceptance.

## Structured storyboard delivery

Portable storyboard delivery identifies the selected direction and revision and
preserves ordered structured content, panel identities, relevant production notes
and required assets. An HTML view or flattened image is not a substitute for the
retained structured source. Supported review-only exports declare that limitation.
Exact serialization, package layout and review formats remain open; advertised
offline packages must work without the original store or implicit asset retrieval.
Missing required assets prevent successful complete delivery. Deliberately unillustrated
panels remain valid when permitted by the requested fidelity. Review annotations stay
outside artifact content. A storyboard export does not imply finished animation,
narration, clip playback or presentation-to-video production.

## Presentation-to-video export

This is an optional export of a selected presentation revision, not a requirement
for making or reviewing decks and not a general-purpose video editor.

1. **Notes and timing belong to the selected revision.** Speaker notes remain
   distinct from review comments. Narrated export uses the identified notes or an
   explicitly selected adaptation; it does not silently rewrite them for duration.
   The retained timing plan maps slides to narration and clip segments. Actual speech
   duration, pauses, transitions and intended clip playback determine timing.
   Conflicting fixed durations require a choice rather than truncated speech,
   silently accelerated narration or omitted clip content. Silent export uses
   explicit pacing; any notes-based duration estimate is labeled as an estimate.
2. **Included clips and narration have deliberate audio behavior.** The selected
   plan states how original clip audio and narration interact and avoids accidental
   overlap. Playback segments and transitions remain synchronized throughout the
   exported video; a static screenshot pass cannot establish this.
3. **Speech is an explicit capability with its own configuration.** Provider and
   voice selection, prerequisites, disclosure destinations and any spending are
   documented before synthesis. Stories does not assume the calling agent's model
   access includes speech, or silently use another service. Missing speech support
   returns a remedy rather than substituting silent output for requested narration.
   Reusing retained audio or deterministic video encoding does not require fresh
   synthesis. Retry and cancellation follow the existing execution contracts.
4. **Video is a derived artifact with its own checks.** Export identifies its base
   revision, notes, assets, audio and timing choices. Completion checks the actual
   encoded output and reports playback, timing and audio checks separately from
   semantic review. It does not inherit a visual pass or acceptance from the deck.

## Contract checks

- Use shared image creation for a document, presentation and storyboard. Preserve
  actual image bytes and provenance on reopening/export without new model calls;
  generated conceptual imagery remains distinct from inspected factual evidence.
- Fail missing image configuration or exhausted authority honestly; planned imagery
  never appears as a produced asset. Retain original content when creating a variation.
- Deliver a structured storyboard with mixed visual states and verify ordering,
  identities, notes and exact assets. Missing required media fails completion while
  permitted text-only panels survive; review-only exports disclose lost structure.
- Review a supplied image and clip, revise unrelated text and reopen the earlier
  revision after changing the original files. Each revision retains its own media.
- Keep a large image unchanged, then explicitly request a resized copy. Preserve
  the original, disclose the derivative and produce the selected export in each case.
- Extract a ZIP in an unrelated directory with Stories stopped and network disabled.
  Open its HTML and play supported media; missing assets fail export validation.
- Permit identified story assets while rejecting unrelated file/network requests
  and attempts to reach workspace controls. Resource exhaustion gives a remedy.
- Report static-only inspection honestly; an unplayed clip cannot receive a playback
  pass. Static fallbacks and unsupported formats remain distinguishable.
- For video export, use short and long notes, pauses and an included clip with
  audio. Verify the encoded timeline, complete narration and selected audio behavior.
  A conflicting duration or unavailable speech provider cannot silently alter intent.

## What v1 deliberately does NOT freeze

- Speech provider, renderer or encoder.
- Image providers, generation/variation mechanisms, structured storyboard serialization
  and package or review-export formats.
- Asset schemas, supported codecs, size thresholds or timing controls.

## Changelog

- **2026-09-18** — Added shared image generation across formats and structured
  storyboard delivery, preserving visual provenance and exact reviewed content.
- **2026-09-18** — Defined supplied media, portable HTML delivery and notes-aware
  presentation-to-video export.
