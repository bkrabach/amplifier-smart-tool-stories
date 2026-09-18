"""Durable review navigation, independent from choosing or accepting material."""

import copy

from .artifacts import parse_html, validate_anchor
from .errors import require


class ReviewViewLibrary:
    @staticmethod
    def _review_view(story, view_id):
        require(
            isinstance(view_id, str) and 0 < len(view_id) <= 100, "Use a review view ID of 1–100 characters."
        )
        state = copy.deepcopy(
            story.get("review_views", {}).get(view_id)
            or {
                "view_id": view_id,
                "version": 0,
                "revision_id": story.get("selected_revision") or story.get("latest_revision"),
                "slide": 1,
                "comparison_revision": None,
                "panel_open": False,
                "anchor": {"kind": "story"},
                "export_format": "html",
                "sections": [],
            }
        )

        # A panel may be opened before any revision exists. Its first material
        # should become visible even though that navigation state is already saved.
        if state["revision_id"] is None:
            state["revision_id"] = story.get("selected_revision") or story.get("latest_revision")
        return state

    def get_review_view(self, story_id, view_id="shared"):
        """Read durable revision focus, one-based slide, comparison, selection and panel state; no authority."""
        with self.store.transaction() as db:
            return self._review_view(self.store.get(db, "stories", story_id), view_id)

    def update_review_view(
        self,
        story_id,
        expected_version,
        request_id,
        view_id="shared",
        revision_id=None,
        slide=None,
        comparison_revision=None,
        panel_open=None,
        anchor=None,
        export_format=None,
        sections=None,
    ):
        """Update shared review navigation at an exact version; viewing never chooses, accepts or runs work.

        Read get_review_view first. Stale versions conflict; retry identical input with the same request_id.
        Empty comparison_revision clears comparison. Slides are one-based. Omitted fields stay unchanged.
        """
        require(
            type(expected_version) is int and expected_version >= 0, "expected_version must be nonnegative."
        )
        payload = [
            story_id,
            view_id,
            expected_version,
            revision_id,
            slide,
            comparison_revision,
            panel_open,
            anchor,
            export_format,
            sections,
        ]

        def action(db):
            story = self.store.get(db, "stories", story_id)
            state = self._review_view(story, view_id)
            require(
                state["version"] == expected_version,
                "Review view changed. Read get_review_view and reconcile before updating.",
                "view_conflict",
            )
            if revision_id is not None and revision_id != state["revision_id"]:
                self._revision(story, revision_id)
                state.update(revision_id=revision_id, slide=1, anchor={"kind": "story"})
            rev = self._revision(story, state["revision_id"]) if state["revision_id"] else None
            if slide is not None:
                require(
                    type(slide) is int
                    and 1 <= slide <= max(1, len(parse_html(rev["html"]).select(".slide")) if rev else 1),
                    "Slide is outside this exact revision.",
                )
                state["slide"] = slide
            if comparison_revision is not None:
                if comparison_revision:
                    self._revision(story, comparison_revision)
                state["comparison_revision"] = comparison_revision or None
            if panel_open is not None:
                require(type(panel_open) is bool, "panel_open must be a boolean.")
                state["panel_open"] = panel_open
            if anchor is not None:
                require(rev is not None, "A revision is required for a review target.")
                state["anchor"] = validate_anchor(rev["html"], anchor, rev.get("assets", []))
            if export_format is not None:
                require(export_format in {"html", "zip", "pdf", "docx"}, "Unknown export format.")
                state["export_format"] = export_format
            if sections is not None:
                require(
                    isinstance(sections, list)
                    and len(sections) <= 4
                    and all(
                        isinstance(s, str) and s in {"sources", "grant", "export", "work"} for s in sections
                    ),
                    "Unknown review panel section.",
                )
                state["sections"] = sorted(set(sections))
            state["version"] += 1
            story.setdefault("review_views", {})[view_id] = state
            self.store.put(db, "stories", story)
            self.store.event(db, story_id, "review_view_changed", view_id=view_id, version=state["version"])
            return copy.deepcopy(state)

        return self._mutation(request_id, "update_review_view", payload, action)
