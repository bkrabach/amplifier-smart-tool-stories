"""Opt-in story expertise evaluation using historical bundle assets, not quality oracles.

Each invocation runs one bounded scenario. A failed result is retained, never retried automatically.
"""

import argparse
import json
from pathlib import Path

from bs4 import BeautifulSoup

from amplifier_smart_tool_stories import Stories

SCENARIOS = {
    "case-study": (
        ["case-study-building-stories.md", "metrics-analysis.md"],
        "Write a concise case study of the bundle's extraction: challenge, approach, outcomes and transferable lessons. Distinguish reported achievements from independent validation.",
        "Engineers learning from a project",
        ["case-study"],
        ["11", "2026"],
    ),
    "release": (
        ["bundle-development-log.txt"],
        "Write development release notes from this supplied commit log, grouped by change type. No release tag or release date was supplied: label the scope accordingly and don't invent a version, migration command or compatibility guarantee. Explain user-relevant changes without claiming you read code.",
        "Maintainers reviewing changes",
        ["release"],
        ["schema", "2"],
    ),
    "technical": (
        ["case-study-building-stories.md"],
        "Explain the architecture and workflow of the supplied historical bundle, including components, constraints and what remains unverified. Do not claim current API or executable tutorial validation.",
        "Developers evaluating the design",
        ["technical"],
        ["11"],
    ),
    "marketing": (
        ["blog-stories-launch.md", "metrics-analysis.md"],
        "Draft a short public-facing feature article using the historical launch material. Explain the reader problem, concrete capability and limits. Keep it welcoming without presenting source promotional claims as independently measured impact.",
        "Potential users unfamiliar with the bundle",
        ["marketing"],
        ["Stories"],
    ),
    "community": (
        ["community-announcement.md"],
        "Write a community digest of this supplied historical announcement: what the community can learn, contributor attribution when actually supplied, and unknowns. Do not invent named members, testimonials or engagement numbers. Do not publish anything.",
        "Community participants",
        ["community"],
        ["11"],
    ),
    "executive": (
        ["case-study-building-stories.md", "metrics-analysis.md"],
        "Write an executive decision brief on what must be verified before adoption. Explain trade-offs, unknowns and next evidence needed; don't turn activity counts into ROI.",
        "Leadership considering a pilot",
        ["executive"],
        ["11", "2026"],
    ),
    "adaptation": (
        ["case-study-building-stories.md"],
        "Adapt this existing case study into a plain-language leadership briefing. Preserve its core meaning, historical attribution and important caveats while dropping implementation detail. Do not invent financial savings.",
        "Nontechnical decision-makers",
        ["adaptation"],
        ["Stories"],
    ),
    "strategy": (
        ["case-study-building-stories.md", "metrics-analysis.md"],
        "Produce an editorial plan comparing three possible story angles from this material. Recommend one based on evidence quality and audience relevance, identify missing support and a supported output format. The requested deliverable is the plan, not a finished promotional story.",
        "An editor choosing what to communicate",
        ["strategy"],
        ["evidence"],
    ),
    "data": (
        ["metrics-analysis.md"],
        "Explain the supplied historical measurements, their units and limits. Include the reported 83,548 bytes and 11 agents exactly, distinguish inventory counts from impact, and explain why ROI or adoption cannot be inferred. Do not create a workbook or invent a benchmark.",
        "Analysts interpreting the report",
        ["data"],
        ["83,548", "11"],
    ),
}


def run(case, provider, model, store, request_id):
    source_names, purpose, audience, expected, phrases = SCENARIOS[case]
    api = Stories(store, provider=provider, model=model, model_env=True, execution="in_process")
    fixtures = Path(__file__).parent / "fixtures"
    receipt = api.generate(
        title=f"Stories: {case}",
        purpose=purpose
        + " Keep this document under 350 words, use at most 8 blocks, and retain critical caveats. Cite the provided evidence.",
        audience=audience,
        kind="document",
        sources=[
            {"id": str(i), "name": name, "content": (fixtures / name).read_text()}
            for i, name in enumerate(source_names)
        ],
        grant={"timeout_seconds": 600, "max_output_tokens": 7000},
        request_id=request_id,
    )
    op = api.get_operation(receipt["operation_id"])
    report = {"case": case, "receipt": receipt, "state": op["state"], "error": op.get("error")}
    if op["state"] == "succeeded":
        revision = api.get_revision(receipt["story_id"], op["result"]["revision_id"])
        text = BeautifulSoup(revision["html"], "html.parser").get_text(" ", strip=True)
        selected = [r["id"] for r in op["result"]["provenance"]["expertise"]]
        report.update(
            text=text,
            selected=selected,
            checks={
                "appropriate_expertise": set(expected) <= set(selected),
                "requested_details": all(p.lower() in text.lower() for p in phrases),
                "source_and_render_review_passed": revision["quality_review"]["passed"],
            },
            provenance=op["result"]["provenance"],
        )
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--allow-model", action="store_true", required=True)
    p.add_argument("--case", choices=SCENARIOS, required=True)
    p.add_argument("--provider", required=True)
    p.add_argument("--model")
    p.add_argument("--store", required=True)
    p.add_argument("--request-id", required=True)
    p.add_argument("--report", required=True)
    a = p.parse_args()
    report = run(a.case, a.provider, a.model, a.store, a.request_id)
    Path(a.report).write_text(json.dumps(report, indent=2))
    print(
        json.dumps({k: v for k, v in report.items() if k in {"case", "state", "error", "checks", "selected"}})
    )
    raise SystemExit(0 if report["state"] == "succeeded" and all(report["checks"].values()) else 1)
