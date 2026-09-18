"""Retained spoken scripts, distinct from slide notes and synthesized audio."""

import hashlib
import json
import math

from .artifacts import parse_html
from .errors import require
from .store import identity, now


def slide_material(revision):
    soup = parse_html(revision["html"])
    slides = []
    for i, slide in enumerate(soup.select(".slide"), 1):
        notes = [n.get_text(" ", strip=True) for n in slide.select(".notes,[data-speaker-notes]")]
        for n in slide.select(".notes,[data-speaker-notes]"):
            n.decompose()
        slides.append(
            {
                "slide": i,
                "text": slide.get_text(" ", strip=True),
                "speaker_notes": "\n".join(notes),
                "image_descriptions": [img.get("alt", "") for img in slide.select("img")],
            }
        )
    require(slides and revision.get("kind") != "document", "Narration scripts require presentation slides.")
    return slides


def validate_script(result, count, references):
    require(isinstance(result, dict), "Script must be an object.", "invalid_model_result")
    require(
        isinstance(result.get("throughline"), str) and result["throughline"].strip(),
        "Script needs an audience takeaway.",
        "invalid_model_result",
    )
    rows = result.get("slides")
    require(
        isinstance(rows, list) and len(rows) == count,
        "Script must cover every slide exactly once.",
        "invalid_model_result",
    )
    for i, row in enumerate(rows, 1):
        require(
            isinstance(row, dict) and type(row.get("slide")) is int and row["slide"] == i,
            "Script slide order must match the deck.",
            "invalid_model_result",
        )
        require(
            isinstance(row.get("text"), str) and row["text"].strip() and len(row["text"]) <= 4000,
            "Each spoken script must contain 1–4000 characters.",
            "invalid_model_result",
        )
        refs = row.get("references")
        require(
            isinstance(refs, list) and refs and all(isinstance(r, str) and r in references for r in refs),
            "Script references must identify supplied slides, notes or sources.",
            "invalid_model_result",
        )
    require(
        isinstance(result.get("limitations"), list)
        and all(isinstance(x, str) for x in result["limitations"]),
        "Script limitations must be text entries.",
        "invalid_model_result",
    )
    return result


def references_for(story, count):
    return {f"{kind}:{i}" for kind in ("slide", "notes") for i in range(1, count + 1)} | {
        f"source:{s['id']}" for s in story["sources"]
    }


def retain(
    api, db, story, revision, result, *, origin, base_script_id=None, guidance="", target_seconds=None
):
    count = len(slide_material(revision))
    validate_script(result, count, references_for(story, count))
    core = {k: result[k] for k in ("throughline", "slides", "limitations")}
    record = {
        "id": identity("script"),
        "story_id": story["id"],
        "revision_id": revision["id"],
        "source_sha256": revision["sha256"],
        "created_at": now(),
        "origin": origin,
        "base_script_id": base_script_id,
        "guidance": guidance,
        "target_seconds": target_seconds,
        **core,
        "sha256": hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest(),
        "estimated_seconds": round(sum(len(s["text"].split()) for s in result["slides"]) / 140 * 60, 1),
        "timing_basis": "rough estimate at 140 words/minute; actual speech determines video timing",
        "review": result.get("review", {"method": "not_performed"}),
        "provenance": result.get("provenance", {}),
    }
    api.store.put(db, "narration_scripts", record)
    api.store.event(
        db, story["id"], "narration_script_created", script_id=record["id"], revision_id=revision["id"]
    )
    return record


class ScriptLibrary:
    def prepare_narration(
        self,
        story_id,
        revision_id,
        grant,
        request_id,
        guidance="",
        target_seconds=None,
        base_script_id=None,
        draft_notes=None,
    ):
        """Write or refine a retained spoken story using the writing provider, without speech synthesis."""
        revision = self.get_revision(story_id, revision_id)
        material = slide_material(revision)
        require(
            draft_notes is None
            or (
                isinstance(draft_notes, list)
                and len(draft_notes) == len(material)
                and all(isinstance(n, str) and len(n) <= 4000 for n in draft_notes)
            ),
            "Draft passages must match slide count; empty passages are allowed, up to 4000 characters each.",
        )
        require(
            isinstance(guidance, str) and len(guidance) <= 8000,
            "Guidance must be text up to 8000 characters.",
        )
        require(
            target_seconds is None
            or (
                type(target_seconds) in (int, float)
                and math.isfinite(target_seconds)
                and 10 <= target_seconds <= 7200
            ),
            "Target duration must be 10–7200 seconds, or omitted.",
        )
        if base_script_id:
            base = self.get_narration_script(story_id, base_script_id)
            require(
                base["revision_id"] == revision_id, "Base script belongs to another revision.", "stale_script"
            )
        checked = self._grant(grant)

        def action(db):
            story = self.store.get(db, "stories", story_id)
            op_id = self._queue(db, story, "prepare_narration", checked, revision_id)
            op = self.store.get(db, "operations", op_id)
            op.update(
                guidance=guidance,
                target_seconds=target_seconds,
                base_script_id=base_script_id,
                draft_notes=draft_notes,
            )
            if base_script_id:
                op["base_script"] = self.store.get(db, "narration_scripts", base_script_id)
            self.store.put(db, "operations", op)
            return {
                "status": "queued",
                "operation_id": op_id,
                "story_id": story_id,
                "revision_id": revision_id,
            }

        return self._mutation(
            request_id,
            "prepare_narration",
            [story_id, revision_id, grant, guidance, target_seconds, base_script_id, self.config.public()]
            + ([draft_notes] if draft_notes is not None else []),
            action,
        )

    def get_narration_script(self, story_id, script_id):
        """Read an exact retained spoken script, its source revision, guidance and review."""
        with self.store.transaction() as db:
            record = self.store.get(db, "narration_scripts", script_id)
        require(record["story_id"] == story_id, "Script belongs to another story.")
        return record

    def list_narration_scripts(self, story_id, revision_id=None):
        """List retained spoken scripts without writing or speech provider access."""
        self.get_story(story_id)
        if revision_id:
            self.get_revision(story_id, revision_id)
        with self.store.transaction() as db:
            rows = db.execute(
                "SELECT data FROM narration_scripts WHERE json_extract(data, '$.story_id')=? ORDER BY rowid",
                (story_id,),
            ).fetchall()
        return {
            "scripts": [
                s
                for (data,) in rows
                if (s := json.loads(data)) and (revision_id is None or s["revision_id"] == revision_id)
            ]
        }

    def save_narration_script(self, story_id, revision_id, notes, request_id, base_script_id=None):
        """Retain an explicitly authored or edited script as a new version, without model use."""
        revision = self.get_revision(story_id, revision_id)
        count = len(slide_material(revision))
        require(
            isinstance(notes, list)
            and len(notes) == count
            and all(isinstance(n, str) and n.strip() and len(n) <= 4000 for n in notes),
            "Supply one nonempty script per slide (maximum 4000 characters each).",
        )
        base = self.get_narration_script(story_id, base_script_id) if base_script_id else None
        require(
            base is None or base["revision_id"] == revision_id,
            "Base script belongs to another revision.",
            "stale_script",
        )

        def action(db):
            story = self.store.get(db, "stories", story_id)
            result = {
                "throughline": base["throughline"] if base else story["title"],
                "slides": [
                    {
                        "slide": i,
                        "text": text,
                        "references": base["slides"][i - 1]["references"] if base else [f"slide:{i}"],
                    }
                    for i, text in enumerate(notes, 1)
                ],
                "limitations": list(base["limitations"]) if base else [],
            }
            result["limitations"].append(
                "Explicitly supplied text; source support and narrative quality have not been reviewed after this edit."
            )
            record = retain(
                self, db, story, revision, result, origin="supplied", base_script_id=base_script_id
            )
            return {"status": "succeeded", "script_id": record["id"], "revision_id": revision_id}

        return self._mutation(
            request_id, "save_narration_script", [story_id, revision_id, notes, base_script_id], action
        )
