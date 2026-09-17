"""Amplifier provider adapter. Credentials stay in env/provider-owned caches, never story state."""

import asyncio
import copy
import hashlib
import importlib
import json
import os
import pickle
import sys
from pathlib import Path

from .errors import StoriesError, require

PROVIDERS = {
    "openai": "openai",
    "chatgpt": "openai-chatgpt",
    "copilot": "github-copilot",
    "anthropic": "anthropic",
    "gemini": "gemini",
}
ENV = {
    "openai": ("OPENAI_API_KEY",),
    "anthropic": ("ANTHROPIC_API_KEY",),
    "gemini": ("GOOGLE_API_KEY", "GEMINI_API_KEY"),
    "copilot": ("COPILOT_AGENT_TOKEN", "COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"),
}
SETUP = {
    "openai": "Set OPENAI_API_KEY.",
    "anthropic": "Set ANTHROPIC_API_KEY.",
    "gemini": "Set GOOGLE_API_KEY or GEMINI_API_KEY; GOOGLE_API_KEY takes precedence.",
    "copilot": "Authenticate gh with Copilot access, then export GH_TOKEN from gh auth token, or set COPILOT_AGENT_TOKEN.",
    "chatgpt": "Complete Amplifier's explicit ChatGPT device login first. Stories uses its OAuth cache; it never prompts during work.",
}


class ProviderConfig:
    def __init__(self, provider=None, model=None, *, use_env=True):
        name = provider or (os.environ.get("STORIES_PROVIDER", "openai") if use_env else "openai")
        aliases = {v: k for k, v in PROVIDERS.items()}
        self.provider = aliases.get(name, name)
        require(self.provider in PROVIDERS, "Choose openai, chatgpt, copilot, anthropic, or gemini.")
        self.model = model or (os.environ.get("STORIES_MODEL") if use_env else None) or None
        require(
            self.model is None or isinstance(self.model, str) and len(self.model) < 200,
            "Model must be a short string.",
        )

    def public(self):
        return {"provider": self.provider, "model": self.model}

    def entry(self):
        from amplifier_agent_cli.provider_sources import build_provider_entry, resolve_credential_detailed

        name = PROVIDERS[self.provider]
        if self.provider != "chatgpt":
            key = next((key for key in ENV[self.provider] if os.environ.get(key)), None)
            if not key:
                raise StoriesError(
                    "provider_unavailable", f"{self.provider} credentials are missing.", SETUP[self.provider]
                )
        else:
            if not resolve_credential_detailed(name).resolved:
                raise StoriesError(
                    "provider_unavailable", "ChatGPT OAuth is not configured.", SETUP[self.provider]
                )
        entry = build_provider_entry(name, model_override=self.model)
        if self.provider != "chatgpt":
            entry["config"]["api_key"] = os.environ[key]
        else:
            entry["config"]["login_on_mount"] = False
        return entry


def settings(config):
    rows = []
    for name in PROVIDERS:
        keys = ENV.get(name, ())
        key = next((key for key in keys if os.environ.get(key)), None)
        row = {"name": name, "configured": bool(key), "source": key or "none", "setup": SETUP[name]}
        if name == "chatgpt":
            from amplifier_agent_cli.provider_sources import resolve_credential_detailed

            row.update(
                configured=bool(resolve_credential_detailed("openai-chatgpt").resolved),
                source="provider OAuth cache",
            )
        rows.append(row)
    return {
        "effective": config.public(),
        "scope": "process and explicit per-operation snapshot",
        "providers": rows,
    }


def marker(config):
    from amplifier_agent_lib import __version__
    from amplifier_agent_lib.bundle.cache import cache_dir_for_version

    return cache_dir_for_version(__version__) / f"stories-{config.provider}-ready.json"


async def prepared(config, allow_prepare=False):
    from amplifier_agent_lib import __version__
    from amplifier_agent_lib.bundle.cache import load_and_prepare_cached

    entry = config.entry()  # Fail before any resolver side effect on missing credentials.
    if allow_prepare:
        bundle = copy.copy(await load_and_prepare_cached(aaa_version=__version__))
    else:
        bundle = _load_local_runtime(config)
    bundle.mount_plan = copy.deepcopy(bundle.mount_plan)
    bundle.mount_plan.update(providers=[entry], tools=[], agents={}, hooks=[])
    if config.provider == "chatgpt":
        from amplifier_agent_cli.provider_sources import PROVIDER_CATALOG

        item = PROVIDER_CATALOG["openai-chatgpt"]
        path = str(
            (await bundle.resolver.async_resolve(item["module"], source_hint=item["source"])).resolve()
        )
        if path not in sys.path:
            sys.path.insert(0, path)
        oauth = importlib.import_module("amplifier_module_provider_openai_chatgpt.oauth")
        token_path = entry["config"].get("token_file_path")
        tokens = oauth.load_tokens(token_path)
        if not oauth.is_token_valid(tokens) and tokens and tokens.get("refresh_token"):
            tokens = await oauth.refresh_tokens(tokens["refresh_token"], path=token_path)
        if not oauth.is_token_valid(tokens):
            raise StoriesError("provider_unavailable", "ChatGPT login is expired.", SETUP["chatgpt"])
    return bundle


def _load_local_runtime(config):
    """Use only the explicitly prepared local artifact, with lazy installation disabled."""
    from amplifier_foundation.bundle._prepared import BundleModuleResolver

    try:
        mark = marker(config)
        receipt = json.loads(mark.read_text())
        artifact = (mark.parent / "prepared.pickle").read_bytes()
        paths = {key: Path(value) for key, value in receipt["module_paths"].items()}
        if (
            receipt["python_prefix"] != sys.prefix
            or receipt["artifact_sha256"] != hashlib.sha256(artifact).hexdigest()
            or not paths
            or not all(path.is_dir() for path in paths.values())
        ):
            raise ValueError("Runtime cache changed")
        # This is Amplifier Agent's trusted, local cache, never caller-supplied data.
        bundle = pickle.loads(artifact)
        bundle.resolver = BundleModuleResolver(paths)  # No activator: no downloads/install.
        return bundle
    except Exception:
        raise StoriesError(
            "runtime_not_prepared",
            "This provider's runtime is missing or changed since preparation.",
            "Run stories --provider NAME prepare-runtime explicitly, then retry with a new request_id.",
        ) from None


def prepare_runtime(config):
    async def run():
        bundle = await prepared(config, allow_prepare=True)
        session = await bundle.create_session()
        async with session:
            require(
                bool(session.coordinator.get("providers")),
                "Provider failed to mount.",
                "provider_unavailable",
            )
        mark = marker(config)
        mark.parent.mkdir(parents=True, exist_ok=True)
        mark.write_text(json.dumps({
            **config.public(),
            "python_prefix": sys.prefix,
            "artifact_sha256": hashlib.sha256((mark.parent / "prepared.pickle").read_bytes()).hexdigest(),
            "module_paths": {key: str(path) for key, path in bundle.resolver._paths.items()},
        }))
        return {"status": "succeeded", "provider": config.provider, "runtime": "amplifier-agent"}

    try:
        return asyncio.run(asyncio.wait_for(run(), 300))
    except StoriesError:
        raise
    except Exception as exc:
        raise StoriesError(
            "runtime_prepare_failed",
            f"Runtime preparation failed ({type(exc).__name__}).",
            "Check provider credentials, network and installed Amplifier dependencies.",
        ) from None


async def complete(provider, config, messages, max_tokens, timeout):
    from amplifier_core.message_models import ChatRequest, Message

    response = await provider.complete(
        ChatRequest(
            messages=[Message(**m) for m in messages],
            model=config.model,
            max_output_tokens=max_tokens,
            timeout=timeout,
        )
    )
    content = response.content
    if isinstance(content, str):
        text = content
    else:
        text = "".join(getattr(part, "text", "") or "" for part in content)
    usage = getattr(response, "usage", None)
    usage = usage.model_dump() if hasattr(usage, "model_dump") else {}
    return text, {
        "provider": config.provider,
        "model": config.model or getattr(provider, "default_model", None),
        "usage": {k: v for k, v in usage.items() if isinstance(v, (float, int))},
    }


def test_provider(config, timeout_seconds):
    require(type(timeout_seconds) is int and 1 <= timeout_seconds <= 300, "Timeout must be 1–300 seconds.")

    async def run():
        bundle = await prepared(config)
        session = await bundle.create_session()
        async with session:
            mounted = session.coordinator.get("providers")
            require(bool(mounted), "Provider failed to mount.", "provider_unavailable")
            text, provenance = await complete(
                next(iter(mounted.values())),
                config,
                [{"role": "user", "content": "Reply with OK only."}],
                128,
                timeout_seconds,
            )
            require(bool(text.strip()), "Provider returned no text.", "invalid_model_result")
            return {"status": "succeeded", **provenance}

    try:
        return asyncio.run(asyncio.wait_for(run(), timeout_seconds))
    except StoriesError:
        raise
    except Exception as exc:
        raise StoriesError(
            "provider_test_failed",
            f"Connection test failed ({type(exc).__name__}).",
            "Check credentials, model access and provider availability. No fallback was used.",
        ) from None
