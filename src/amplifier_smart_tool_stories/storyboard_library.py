"""Storyboard operations over the shared story store and execution lifecycle."""

import copy

from .errors import require
from .media import select
from .store import identity, now
from .storyboards import checked, checked_brief, render_storyboard, text


class StoryboardLibrary:
    def _storyboard_story(self, title, idea, audience, sources, assets, fidelity):
        text(title, "title", 300, True)
        text(idea, "idea", 10000, True)
        text(audience, "audience", 1000, True)
        require(fidelity in {"outline", "mixed", "illustrated"}, "Choose outline, mixed or illustrated.")
        brief = {"id": identity("brief"), "intent": idea, "assumptions": [], "open_questions": []}
        return {
            "id": identity("story"),
            "title": title,
            "kind": "storyboard",
            "purpose": idea,
            "audience": audience,
            "created_at": now(),
            "sources": sources,
            "assets": assets,
            "revisions": [],
            "annotations": [],
            "drafts": {},
            "selected_revision": None,
            "latest_revision": None,
            "feedback_grant": None,
            "directions": [],
            "selected_direction": None,
            "briefs": [brief],
            "brief_id": brief["id"],
            "fidelity": fidelity,
        }

    def _board_revision(
        self,
        story,
        board,
        base=None,
        evidence=None,
        assets=None,
        origin="imported",
        limitations=None,
        new_direction=False,
    ):
        previous = self._revision(story, base) if base else None
        assets = assets if assets is not None else previous.get("assets", []) if previous else story["assets"]
        board = checked(board, evidence or [], assets, story["fidelity"])
        rev = self._new_revision(
            story,
            render_storyboard(board, evidence or [], assets, story["fidelity"]),
            base,
            evidence,
            limitations,
            origin,
            assets=assets,
        )
        direction = next(
            (d for d in story["directions"] if previous and d["id"] == previous["direction_id"]), None
        )
        if direction is None or new_direction:
            direction = {"id": identity("direction")}
            story["directions"].append(direction)
        direction.update(
            name=board["name"],
            approach=board["approach"],
            tradeoff=board["tradeoff"],
            latest_revision=rev["id"],
            brief_id=story["brief_id"],
            superseded=False,
        )
        rev.update(
            kind="storyboard",
            storyboard=board,
            direction_id=direction["id"],
            brief_id=story["brief_id"],
            brief=copy.deepcopy(story["briefs"][-1]),
            audience=story["audience"],
            fidelity=story["fidelity"],
        )
        return rev

    def create_storyboard(
        self,
        title,
        storyboard,
        request_id,
        sources=None,
        asset_ids=None,
        purpose="Develop this visual sequence",
        audience="Reader",
        fidelity="mixed",
    ):
        """Import one structured storyboard without model use; images are retained assets or visibly planned."""
        supplied = self._sources(sources or [])

        def action(db):
            story = self._storyboard_story(
                title, purpose, audience, supplied, select(db, asset_ids or []), fidelity
            )
            rev = self._board_revision(
                story, storyboard, limitations=["Imported storyboard; semantic review not performed."]
            )
            self.store.put(db, "stories", story)
            self.store.event(db, story["id"], "story_created", revision_id=rev["id"])
            return {
                "status": "succeeded",
                "story_id": story["id"],
                "revision_id": rev["id"],
                "direction_id": rev["direction_id"],
            }

        return self._mutation(
            request_id,
            "create_storyboard",
            [title, storyboard, supplied, asset_ids, purpose, audience, fidelity],
            action,
        )

    def generate_storyboard(
        self,
        title,
        idea,
        audience,
        grant,
        request_id,
        sources=None,
        asset_ids=None,
        explore=False,
        fidelity="outline",
    ):
        """Develop one storyboard, or two directions only when explore is explicitly requested; shared 12-call limit."""
        require(type(explore) is bool, "explore must be a boolean; enable only for requested alternatives.")
        supplied, authority = self._sources(sources or []), self._grant(grant)

        def action(db):
            story = self._storyboard_story(
                title, idea, audience, supplied, select(db, asset_ids or []), fidelity
            )
            story["explore"] = explore
            op_id = self._queue(db, story, "generate", authority)
            op = self.store.get(db, "operations", op_id)
            op.update(brief_id=story["brief_id"], direction_count=2 if explore else 1)
            self.store.put(db, "operations", op)
            self.store.put(db, "stories", story)
            return {"status": "queued", "story_id": story["id"], "operation_id": op_id}

        return self._mutation(
            request_id,
            "generate_storyboard",
            [title, idea, audience, grant, supplied, asset_ids, explore, fidelity, self.config.public()],
            action,
        )

    def revise_storyboard(
        self, story_id, revision_id, storyboard, request_id, asset_ids=None, new_direction=False
    ):
        """Retain an explicit structured edit or new alternative; earlier panels/assets and acceptance remain unchanged."""
        require(type(new_direction) is bool, "new_direction must be boolean.")

        def action(db):
            story = self.store.get(db, "stories", story_id)
            require(story.get("kind") == "storyboard", "This operation requires a storyboard.")
            base = self._revision(story, revision_id)
            direction = next(d for d in story["directions"] if d["id"] == base["direction_id"])
            require(
                new_direction or direction["latest_revision"] == revision_id,
                "Direction has a newer revision; use it or explicitly create a new direction.",
                "revision_conflict",
            )
            assets = select(db, asset_ids) if asset_ids is not None else base.get("assets", [])
            rev = self._board_revision(
                story,
                storyboard,
                revision_id,
                base["evidence"],
                assets,
                limitations=["Explicit edit; prior model checks and acceptance do not transfer."],
                new_direction=new_direction,
            )
            self.store.put(db, "stories", story)
            self.store.event(
                db, story_id, "storyboard_revised", revision_id=rev["id"], direction_id=rev["direction_id"]
            )
            return {
                "status": "succeeded",
                "story_id": story_id,
                "revision_id": rev["id"],
                "direction_id": rev["direction_id"],
            }

        return self._mutation(
            request_id,
            "revise_storyboard",
            [story_id, revision_id, storyboard, asset_ids, new_direction],
            action,
        )

    def select_direction(self, story_id, revision_id, request_id):
        """Record a user's direction choice at an exact revision; no generation or human acceptance is implied."""

        def action(db):
            story = self.store.get(db, "stories", story_id)
            require(story.get("kind") == "storyboard", "Direction selection currently supports storyboards.")
            rev = self._revision(story, revision_id)
            require(
                rev["brief_id"] == story["brief_id"],
                "This direction uses a superseded brief.",
                "brief_conflict",
            )
            story.update(selected_direction=rev["direction_id"], selected_revision=revision_id)
            self.store.put(db, "stories", story)
            self.store.event(
                db, story_id, "direction_selected", direction_id=rev["direction_id"], revision_id=revision_id
            )
            return {"status": "succeeded", "direction_id": rev["direction_id"], "revision_id": revision_id}

        return self._mutation(request_id, "select_direction", [story_id, revision_id], action)

    def update_storyboard_brief(self, story_id, brief, request_id):
        """Correct shared intent without generating; mark existing directions superseded and retain earlier briefs."""
        brief = checked_brief(brief)

        def action(db):
            story = self.store.get(db, "stories", story_id)
            require(story.get("kind") == "storyboard", "This operation requires a storyboard.")
            revised = {**brief, "id": identity("brief")}
            story["briefs"].append(revised)
            story.update(brief_id=revised["id"], purpose=brief["intent"])
            for direction in story["directions"]:
                direction["superseded"] = True
            self.store.put(db, "stories", story)
            self.store.event(db, story_id, "brief_updated", brief_id=revised["id"])
            return {
                "status": "succeeded",
                "brief_id": revised["id"],
                "superseded_directions": len(story["directions"]),
            }

        return self._mutation(request_id, "update_storyboard_brief", [story_id, brief], action)

    def get_comparison(self, story_id, revision_ids=None):
        """Read up to two exact revision previews for any retained format; no selection or generation."""
        with self.store.transaction() as db:
            story = self.store.get(db, "stories", story_id)
            ids = (
                revision_ids
                if revision_ids is not None
                else (
                    [d["latest_revision"] for d in story.get("directions", [])][-2:]
                    if story.get("directions")
                    else [r["id"] for r in story["revisions"]][-2:]
                )
            )
            require(
                isinstance(ids, list)
                and 1 <= len(ids) <= 2
                and all(isinstance(i, str) for i in ids)
                and len(set(ids)) == len(ids),
                "Choose one or two distinct retained revisions.",
            )
            revisions = [self._revision(story, rid) for rid in ids]
        return {
            "story_id": story_id,
            "selected_direction": story.get("selected_direction"),
            "selected_revision": story["selected_revision"],
            "items": [
                {
                    "revision_id": r["id"],
                    "direction_id": r.get("direction_id"),
                    "name": r.get("storyboard", {}).get("name", story["title"]),
                    "approach": r.get("storyboard", {}).get("approach", ""),
                    "tradeoff": r.get("storyboard", {}).get("tradeoff", ""),
                    "superseded": bool(r.get("brief_id") and r["brief_id"] != story.get("brief_id")),
                    "preview": self.get_preview(story_id, r["id"]),
                }
                for r in revisions
            ],
        }

    def _commit_storyboards(self, db, story, operation, result):
        from .accountability import disclosure_hash, validate_disclosures
        from .artifacts import evidence_checked
        from .quality import validate_record

        require(
            isinstance(result, dict) and result.get("action") in {"revise", "answer", "clarify"},
            "Invalid storyboard result.",
            "invalid_model_result",
        )
        text(result.get("message"), "response", 10000, True)
        require(
            operation.get("brief_id", story["brief_id"]) == story["brief_id"],
            "Shared brief changed during execution.",
            "brief_conflict",
        )
        base = self._revision(story, operation["revision_id"]) if operation["revision_id"] else None
        if base:
            direction = next(d for d in story["directions"] if d["id"] == base["direction_id"])
            require(
                direction["latest_revision"] == base["id"],
                "Direction changed during execution.",
                "revision_conflict",
            )
        requested = operation.get("direction_count", 1)
        candidates = result.get("candidates", [])
        require(isinstance(candidates, list) and len(candidates) <= requested, "Unexpected direction count.")
        if operation["kind"] == "generate":
            require(result["action"] != "answer", "Generation requires storyboard or clarification.")
        require(result["action"] == "revise" or not candidates, "Answers/questions cannot submit artifacts.")
        failures = copy.deepcopy(result.get("failures", []))
        require(isinstance(failures, list), "Failures must be a list.")
        new_ids = []
        if result["action"] == "revise":
            require(bool(candidates) or bool(failures), "No storyboard candidate or failure was submitted.")
            brief = checked_brief(result.get("brief"))
            # Refinement cannot silently change common intent for sibling directions.
            if not base and not story["revisions"]:
                revised = {**brief, "id": identity("brief")}
                story["briefs"].append(revised)
                story["brief_id"] = revised["id"]
            for candidate in candidates:
                evidence = evidence_checked(candidate.get("evidence", []), story["sources"])
                candidate["action"] = "revise"
                validate_disclosures(candidate, story, operation)
                require(bool(evidence) or not story["sources"], "Sourced storyboards require evidence.")
                assets = base.get("assets", []) if base else story["assets"]
                html = render_storyboard(candidate.get("storyboard"), evidence, assets, story["fidelity"])
                require(candidate.get("html", html) == html, "Storyboard and reviewed HTML disagree.")
                quality = candidate.get("quality_review")
                if self.intelligence is None or quality is not None:
                    validate_record(html, quality)
                    require(
                        quality.get("disclosure_sha256") == disclosure_hash(candidate),
                        "Disclosure changed after review.",
                        "stale_review",
                    )
                limitations = candidate.get("limitations", [])
                require(
                    isinstance(limitations, list) and all(isinstance(v, str) for v in limitations),
                    "Invalid limitations.",
                )
                rev = self._board_revision(
                    story,
                    candidate["storyboard"],
                    base["id"] if base else None,
                    evidence,
                    assets,
                    "model",
                    limitations,
                )
                rev.update(changes=candidate["changes"], calculations=candidate["calculations"])
                if quality:
                    rev["quality_review"] = quality
                    rev["review"].update(
                        semantic="passed: model review; audience comprehension not tested",
                        visual="passed: model review of static storyboard sheets",
                    )
                new_ids.append(rev["id"])
        if result["action"] == "revise" and len(new_ids) < requested and not failures:
            failures.append(
                {"code": "incomplete_comparison", "message": "Not all requested directions completed."}
            )
        state = (
            "needs_input"
            if result["action"] == "clarify"
            else "partial"
            if failures and new_ids
            else "failed"
            if failures
            else "succeeded"
        )
        for note in story["annotations"]:
            if note["id"] == operation["annotation_id"]:
                note["responses"].append(
                    {"author": "stories", "text": result["message"], "at": now(), "evidence": []}
                )
                note.update(
                    status="needs_input"
                    if state == "needs_input"
                    else "failed"
                    if state == "failed"
                    else "answered",
                    result_revision=new_ids[0] if new_ids else None,
                )
        operation.update(
            state=state,
            finished_at=now(),
            cleanup="complete",
            result={
                "action": result["action"],
                "message": result["message"],
                "revision_id": new_ids[0] if new_ids else None,
                "revision_ids": new_ids,
                "requested_directions": requested,
                "brief": copy.deepcopy(result.get("brief")),
                "failures": failures,
                "provenance": result.get("provenance", {}),
                "review_attempts": result.get("review_attempts", []),
            },
        )
        self.store.put(db, "stories", story)
        self.store.put(db, "operations", operation)
        self.store.event(
            db,
            story["id"],
            "operation_completed",
            operation_id=operation["id"],
            revision_id=new_ids[0] if new_ids else None,
            revision_ids=new_ids,
            state=state,
        )
        return operation
