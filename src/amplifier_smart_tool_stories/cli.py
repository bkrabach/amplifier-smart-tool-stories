"""JSON adapter over the public library. No domain logic belongs here."""

import argparse
import inspect
import json
import sys
from importlib.resources import files

from .errors import StoriesError
from .lib import CAPABILITIES, Stories


def parser():
    p = argparse.ArgumentParser(prog="stories", description="Evidence-based HTML stories and shared review.")
    p.add_argument("--store", help="Retained state directory")
    p.add_argument("--model-env", action="store_true", help="Authorize reading native provider credentials")
    p.add_argument("--provider", help="openai, chatgpt, copilot, anthropic, gemini")
    p.add_argument("--model", help="Provider model ID; omitted uses provider default")
    p.add_argument("--execution", choices=["queued", "background", "in_process"], default="queued")
    sub = p.add_subparsers(dest="command")
    for name in CAPABILITIES:
        method = getattr(Stories, name)
        c = sub.add_parser(
            name.replace("_", "-"),
            description=method.__doc__ + "\n" + str(inspect.signature(method)),
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        c.add_argument("--input", default="{}", help="JSON object, @file.json, or - for stdin")
    sub.add_parser("skill", help="Print complete operating instructions")
    return p


def main():
    if len(sys.argv) == 1 or sys.argv[1:] in (["--help"], ["-h"]):
        print(files("amplifier_smart_tool_stories").joinpath("SMART_TOOL.md").read_text())
        return
    args = parser().parse_args()
    if args.command is None:
        parser().error("Choose a capability; run stories --help.")
    try:
        if args.command == "skill":
            print(files("amplifier_smart_tool_stories").joinpath("SMART_TOOL.md").read_text())
            return
        raw = args.input
        if raw.startswith("@"):
            from pathlib import Path

            raw = Path(raw[1:]).read_text()
        elif raw == "-":
            raw = sys.stdin.read()
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("Input must be an object")
        name = args.command.replace("-", "_")
        if name == "manifest":
            result = Stories.manifest()
        else:
            api = Stories(
                args.store,
                model_env=args.model_env,
                provider=args.provider,
                model=args.model,
                execution=args.execution,
            )
            method = getattr(api, name)
            inspect.signature(method).bind(**data)
            if name == "provider_login":
                data["on_progress"] = lambda text: print(text, file=sys.stderr, flush=True)
            result = method(**data)
            if args.execution == "in_process" and isinstance(result, dict) and result.get("operation_id"):
                result = {**result, "operation": api.get_operation(result["operation_id"])}
        print(json.dumps(result, ensure_ascii=False))
        if isinstance(result, dict) and (
            result.get("state") == "failed"
            or result.get("status") == "failed"
            or result.get("operation", {}).get("state") == "failed"
        ):
            raise SystemExit(1)
    except StoriesError as exc:
        print(json.dumps(exc.public()))
        raise SystemExit(1) from None
    except (ValueError, TypeError, OSError) as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": {
                        "code": "invalid_input",
                        "message": str(exc),
                        "remedy": "Read capability --help and check input files.",
                    },
                }
            )
        )
        raise SystemExit(2) from None
