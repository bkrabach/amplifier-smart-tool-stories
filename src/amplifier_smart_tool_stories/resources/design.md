Design for reading, not decoration. Prefer one main point per slide, generous whitespace,
clear hierarchy and a consistent restrained accent. Use comparison layouts for comparisons,
a visible baseline beside metrics, and short labeled examples for mechanisms. Avoid a
repetitive wall of cards, meaningless icons, gratuitous charts and presentation chrome.

For new decks use 3–8 section.slide elements unless the request needs another length;
12 is the rendered-review maximum. Use self-contained CSS with explicit px sizes:
1280x720 review canvas, border-box slides, 48–64px padding, 40–60px headings, 24–30px
body and at least 18px source notes. Use flex or block flow, solid backgrounds, local
sans-serif fonts and naturally wrapping text. Avoid viewport units, clamp(), CSS grid,
absolute positioning and clipping: the static review renderer does not reliably support
them. Use explicit line-height. Shorten or split dense slides rather than shrinking text.
Keep content within the canvas. Do not add scripts, external assets, SVG, forms, navigation
or comments. Never make low-opacity text, tiny citations or color alone carry meaning.

Use high contrast text on each immediate background. Make cards and labels readable
without subtle shadows or a dark-room display. Sources and caveats must be legible.
For narrow revisions preserve the existing style and unrelated content; do not rebuild
an imported deck just to adopt these generation defaults. Static rendered review is an
approximation, not proof of browser, projector or every-device appearance.

Keep executive slides concise: target 60–90 words including sources, at most two
supporting panels or four short metrics, and a heading under 12 words. Source details
remain available in the review tool; do not duplicate the entire evidence ledger on
slides. Never pack every extracted fact into the deck. Preserve the most important
conflict, qualifier and decision implication when choosing what to omit.
When a review reports clipping, overlap or extra rendered pages, cut content and
simplify the layout substantially before changing font size. Do not simply nudge
margins or make the same dense layout smaller. Keep source citations as normal-sized
inline text rather than shrinking them with superscript styling.
