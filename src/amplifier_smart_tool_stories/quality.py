"""Artifact-bound review records and cancellable static rendering."""

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

from .artifacts import digest, parse_html
from .errors import StoriesError, require


async def render(html, timeout, include_pdf=False):
    parse_html(html)
    env = os.environ.copy()
    # Standard macOS native library locations; never a development checkout.
    if sys.platform == "darwin" and not env.get("DYLD_FALLBACK_LIBRARY_PATH"):
        env["DYLD_FALLBACK_LIBRARY_PATH"] = ":".join(
            str(p) for p in (Path("/opt/homebrew/lib"), Path("/usr/local/lib")) if p.is_dir()
        )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "amplifier_smart_tool_stories.render_worker",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        env=env,
    )
    try:
        stdout, _ = await asyncio.wait_for(
            process.communicate(json.dumps({"html": html, "include_pdf": include_pdf}).encode()),
            min(40, timeout),
        )
        result = json.loads(stdout)
        if process.returncode or "error" in result:
            raise StoriesError(
                "render_failed",
                result.get("error", "Static rendering failed."),
                "Check the documented Pango prerequisite and HTML layout; no revision was committed.",
            )
        return result
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()


def record(html, rendered, verdict, provenance):
    require(isinstance(verdict, dict), "Missing structured review.", "invalid_review")
    report = {
        "artifact_sha256": digest(html),
        "method": "model_review",
        "reviewer": provenance,
        "renderer": rendered.get("renderer", "WeasyPrint static 1280x720 / PDFium rasterization"),
        "pages": [i["sha256"] for i in rendered["images"]],
        "limits": [
            "Static rendering approximates browser layout.",
            "Model review is not human approval or independent factual verification.",
        ],
    }
    for key in ("semantic", "visual"):
        part = verdict.get(key)
        require(
            isinstance(part, dict) and part.get("status") in ("passed", "failed"),
            f"Invalid {key} review.",
            "invalid_review",
        )
        findings = part.get("findings")
        require(
            isinstance(findings, list) and all(isinstance(x, str) for x in findings),
            "Review findings must be text.",
            "invalid_review",
        )
        require(
            part["status"] != "failed" or bool(findings), "Failed review needs findings.", "invalid_review"
        )
        require(
            part["status"] != "passed" or not findings, "Blocking findings cannot pass.", "invalid_review"
        )
        report[key] = {"status": part["status"], "findings": findings}
    if rendered["findings"]:
        report["visual"] = {
            "status": "failed",
            "findings": rendered["findings"] + report["visual"]["findings"],
        }
    warnings = verdict.get("warnings", [])
    require(
        isinstance(warnings, list) and all(isinstance(x, str) for x in warnings),
        "Review warnings must be text.",
        "invalid_review",
    )
    report["warnings"] = warnings
    report["passed"] = all(report[k]["status"] == "passed" for k in ("semantic", "visual"))
    return report


def validate_record(html, report):
    require(
        isinstance(report, dict) and report.get("artifact_sha256") == digest(html),
        "Review does not match the submitted artifact.",
        "stale_review",
    )
    require(
        report.get("passed") is True
        and all(
            report.get(k, {}).get("status") == "passed" and not report[k].get("findings")
            for k in ("semantic", "visual")
        ),
        "Artifact did not pass quality review.",
        "quality_review_failed",
    )
    require(bool(report.get("pages")), "Review has no rendered pages.", "invalid_review")
    require(
        all(isinstance(p, str) and len(p) == hashlib.sha256().digest_size * 2 for p in report["pages"]),
        "Invalid rendered-page identity.",
        "invalid_review",
    )
    return report
