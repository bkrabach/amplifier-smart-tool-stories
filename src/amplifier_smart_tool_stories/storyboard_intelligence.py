"""Storyboard planning, composition and review inside the existing bounded Agent session."""

import copy
import time
from importlib.resources import files

from .accountability import disclosure_hash, validate_disclosures
from .artifacts import revision_evidence, selected_evidence, source_excerpts
from .errors import StoriesError, require
from .quality import record, render
from .storyboards import BOARD, BRIEF, checked_brief, render_storyboard
from .submissions import CALCULATIONS, CHANGES, EVIDENCE, REVIEW, SECTION, TEXT, TEXTS, obj

STORYBOARD_EVIDENCE = copy.deepcopy(EVIDENCE)
STORYBOARD_EVIDENCE["properties"]["evidence"]["maxItems"] = 12

CANDIDATE = obj({"storyboard": BOARD, "changes": CHANGES, "calculations": CALCULATIONS, "limitations": TEXTS})
RESULT = obj(
    {
        "action": {"type": "string", "enum": ["revise", "answer", "clarify"]},
        "message": TEXT,
        "brief": BRIEF,
        "candidates": {"type": "array", "items": CANDIDATE, "maxItems": 2},
    }
)


async def compose(story, operation, ask, calls):
    prompt = files("amplifier_smart_tool_stories").joinpath("resources/storyboarding.md").read_text()
    catalog, excerpts = source_excerpts(story["sources"])
    base = next((r for r in story["revisions"] if r["id"] == operation["revision_id"]), None)
    brief = next(b for b in story["briefs"] if b["id"] == story["brief_id"])
    note = next((n for n in story["annotations"] if n["id"] == operation["annotation_id"]), None)
    count = operation.get("direction_count", 1)
    assets = base.get("assets", []) if base else story["assets"]
    payload = {
        "title": story["title"],
        "audience": story["audience"],
        "brief": brief,
        "fidelity": story["fidelity"],
        "requested_direction_count": count,
        "base": base,
        "comment": note,
        "assets": assets,
        "continuation": operation.get("continuation", []),
        "related_comments": [
            n
            for n in story["annotations"]
            if note and n["revision_id"] == note["revision_id"] and n["anchor"] == note["anchor"]
        ],
    }
    extracted = await ask(
        prompt
        + "\nExtract evidence before factual composition. Select at most 12 evidence references, using only supplied excerpt IDs; "
        "return empty evidence if no factual sources. Select general expertise and plan an audience-appropriate sequence.",
        {**payload, "sources": catalog},
        schema=STORYBOARD_EVIDENCE,
    )
    evidence = selected_evidence(extracted.get("evidence", []), excerpts, story["sources"])
    if base:
        evidence = revision_evidence(base.get("evidence", []), evidence)
    payload.update(
        evidence=evidence, plan=extracted.get("plan"), limitations=extracted.get("limitations", [])
    )
    result_schema = copy.deepcopy(RESULT)
    result_schema["properties"]["candidates"]["maxItems"] = count
    result = await ask(
        prompt
        + "\nSubmit candidates only for revise; answers and focused questions use an empty candidates array. "
        "Generation must revise or clarify. Refinement returns one candidate containing the entire storyboard, "
        "not one candidate per panel. Include change disclosures and calculations.",
        payload,
        schema=result_schema,
    )
    checked_brief(result.get("brief"))
    if not isinstance(result.get("candidates"), list) or len(result["candidates"]) > count:
        result = await ask(
            prompt
            + "\nRepair the structured submission below. Return native arrays and objects, NOT JSON-encoded strings. "
            "The candidates field must be an array containing at most the requested number of whole storyboards. "
            "Preserve the draft content; escape quotations correctly within text. Include the complete result.",
            {"request": payload, "invalid_submission": result},
            schema=result_schema,
        )
        checked_brief(result.get("brief"))
    require(
        isinstance(result.get("candidates"), list) and len(result["candidates"]) <= count,
        f"Expected at most {count} candidates; received {len(result.get('candidates', [])) if isinstance(result.get('candidates'), list) else type(result.get('candidates')).__name__}.",
        "invalid_model_result",
    )
    attempts, completed, failures = [], [], []
    if result.get("action") == "revise":
        for index, candidate in enumerate(result["candidates"]):
            reviews = []
            try:
                for attempt in range(2):
                    candidate.update(action="revise", evidence=evidence)
                    try:
                        validate_disclosures(candidate, story, operation)
                        candidate["html"] = render_storyboard(
                            candidate.get("storyboard"), evidence, assets, story["fidelity"]
                        )
                        rendered = await render(
                            candidate["html"],
                            operation["deadline"] - time.time(),
                            media=story.get("_media_images"),
                        )
                        verdict = await ask(
                            prompt + "\nReview the actual storyboard sheets and sources. "
                            "Fail unsupported claims, lost qualifiers, unclear sequencing, unreadable layout, "
                            "and edits outside the requested scope. Planned imagery is valid at outline/mixed fidelity. "
                            "A static review does not establish audience understanding or produced video. "
                            "Findings are BLOCKING defects only: a passed section MUST have an empty findings array. "
                            "Put nonblocking caveats in warnings; omit positive observations.",
                            {
                                "request": payload,
                                "candidate": candidate,
                                "sources": story["sources"],
                                "rendered_text": rendered["rendered_text"],
                                "findings": rendered["findings"],
                            },
                            rendered["images"],
                            schema=REVIEW,
                        )
                        review = record(candidate["html"], rendered, verdict, calls[-1])
                    except StoriesError as exc:
                        if exc.code in {"cancelled", "execution_timeout", "execution_limit"}:
                            raise
                        review = {"passed": False, "error": exc.public()["error"]}
                    reviews.append(review)
                    if review["passed"]:
                        review["disclosure_sha256"] = disclosure_hash(candidate)
                        candidate["quality_review"] = review
                        completed.append(candidate)
                        break
                    if attempt == 1:
                        raise StoriesError(
                            "quality_review_failed", "Storyboard still has findings after one repair."
                        )
                    candidate = await ask(
                        prompt
                        + "\nRepair this candidate using the findings. Keep its direction and panel IDs.",
                        {"request": payload, "candidate": candidate, "review": review},
                        schema=CANDIDATE,
                    )
            except StoriesError as exc:
                if exc.code == "cancelled":
                    raise
                failures.append({"candidate": index + 1, **exc.public()["error"], "submission": candidate})
            attempts.append({"candidate": index + 1, "reviews": reviews})
        if len(completed) == 2:
            try:
                diversity = await ask(
                    "Judge whether these are substantively different narrative/visual approaches to the same brief. "
                    "Different styles, labels or feature slices alone fail. This is a model judgment, not human proof.",
                    {"brief": brief, "candidates": [c["storyboard"] for c in completed]},
                    schema=SECTION,
                )
                require(
                    diversity.get("status") == "passed",
                    "Alternative directions are not substantively distinct.",
                    "comparison_review_failed",
                )
                attempts.append({"comparison": diversity, "reviewer": calls[-1]})
            except StoriesError as exc:
                if exc.code == "cancelled":
                    raise
                failures.append({"candidate": 2, **exc.public()["error"], "submission": completed.pop()})
        if len(completed) < count and not failures:
            failures.append({"code": "incomplete_comparison", "message": "Missing requested direction."})
        result.update(candidates=completed, failures=failures)
    result["review_attempts"] = attempts
    result["provenance"] = {
        "runtime": "amplifier-agent",
        "calls": calls,
        "model_calls": len(calls),
        "plan": extracted.get("plan"),
        "expertise": ["shared-storyboarding"],
    }
    return result
