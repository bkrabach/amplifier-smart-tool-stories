"""Help is a self-contained, side-effect-free calling skill in installed packages."""

import inspect
import os
import subprocess
import sys

from amplifier_smart_tool_stories.help import GUIDANCE, example
from amplifier_smart_tool_stories.lib import CAPABILITIES, Stories


def test_help_examples_match_public_signatures():
    assert set(GUIDANCE) == set(CAPABILITIES)
    for name in CAPABILITIES:
        method = getattr(Stories, name)
        args = () if name == "manifest" else (None,)
        inspect.signature(method).bind(*args, **example(name))


def test_every_help_surface_is_an_offline_skill(tmp_path):
    env = {
        key: value
        for key, value in os.environ.items()
        if not any(word in key for word in ("TOKEN", "KEY", "STORIES", "PROVIDER"))
    }
    store = tmp_path / "must-not-exist"
    for command in [None, "skill", *[name.replace("_", "-") for name in CAPABILITIES]]:
        for flag in ("-h", "--help"):
            args = [sys.executable, "-m", "amplifier_smart_tool_stories", "--store", str(store)]
            if command:
                args.append(command)
            result = subprocess.run(args + [flag], cwd=tmp_path, env=env, capture_output=True, text=True)
            assert result.returncode == 0, result.stderr
            assert result.stdout.startswith('<skill_content name="stories')
            assert result.stdout.rstrip().endswith("</skill_content>")
            assert "<skill_resources>" in result.stdout
            assert "--input" in result.stdout
            assert not result.stderr
            if command not in (None, "skill"):
                assert "## When to use" in result.stdout
                assert "## Result and next steps" in result.stdout
                assert "## Failures" in result.stdout
    assert not store.exists()
