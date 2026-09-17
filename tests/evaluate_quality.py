"""Opt-in live evaluation against historical bundle assets; never run by pytest.

uv run python tests/evaluate_quality.py --allow-model --provider openai \
    --store .work/evaluation --run-id unique-run
Reports model review separately from narrow deterministic scenario expectations.
"""

import argparse
import json
from pathlib import Path

from bs4 import BeautifulSoup

from amplifier_smart_tool_stories import Stories


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-model", action="store_true", required=True)
    parser.add_argument(
        "--provider", choices=["openai", "anthropic", "gemini", "chatgpt", "copilot"], required=True
    )
    parser.add_argument("--store", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    fixtures = Path(__file__).parent / "fixtures"
    api = Stories(args.store, provider=args.provider, model_env=True, execution="in_process")
    receipt = api.generate(
        title="Historical Stories bundle: evidence for an adoption decision",
        purpose=(
            "Create exactly three slides for engineering leadership. Explain what the historical "
            "reports claimed, what the metrics actually support, and what to verify before adoption. "
            "Include the January 2026 date and reported 11 specialist agents. Preserve qualifiers "
            "and source attribution. Do not invent ROI or present historical claims as current facts."
        ),
        audience="Engineering leaders deciding what to verify before adoption",
        sources=[
            {"id": name.removesuffix(".md"), "name": name, "content": (fixtures / name).read_text()}
            for name in ["case-study-building-stories.md", "metrics-analysis.md"]
        ],
        grant={"timeout_seconds": 600, "max_output_tokens": 10000},
        request_id=args.run_id,
    )
    operation = api.get_operation(receipt["operation_id"])
    report = {"operation_id": operation["id"], "state": operation["state"], "error": operation.get("error")}
    if operation["state"] == "succeeded":
        revision = api.get_revision(receipt["story_id"], operation["result"]["revision_id"])
        soup = BeautifulSoup(revision["html"], "html.parser")
        text = soup.get_text(" ", strip=True)
        report.update(
            deterministic={
                "three_slides": len(soup.select(".slide")) == 3,
                "historical_date_preserved": "2026" in text,
                "requested_count_preserved": "11" in text,
            },
            model_review=revision["quality_review"],
            provenance=operation["result"]["provenance"],
        )
    print(json.dumps(report, indent=2))
    if operation["state"] != "succeeded" or not all(report["deterministic"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
