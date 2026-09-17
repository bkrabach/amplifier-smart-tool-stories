import json

import pytest

from amplifier_smart_tool_stories import Stories, StoriesError
from amplifier_smart_tool_stories.providers import ENV, ProviderConfig


@pytest.mark.parametrize("name", ["openai", "anthropic", "gemini", "copilot"])
def test_missing_native_credentials_do_not_boot_runtime(monkeypatch, name):
    for keys in ENV.values():
        for key in keys:
            monkeypatch.delenv(key, raising=False)
    with pytest.raises(StoriesError) as exc:
        ProviderConfig(name).entry()
    assert exc.value.code == "provider_unavailable"


@pytest.mark.parametrize("alias,canonical", [("openai-chatgpt", "chatgpt"), ("github-copilot", "copilot")])
def test_subscription_provider_aliases(alias, canonical):
    assert ProviderConfig(alias).provider == canonical


def test_snapshot_does_not_resolve_new_ambient_defaults(monkeypatch):
    monkeypatch.setenv("STORIES_MODEL", "later-model")
    assert ProviderConfig("openai", None, use_env=False).model is None
    assert ProviderConfig("openai").model == "later-model"


def test_redaction_and_configuration_do_not_spend(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "secret-test-value")
    api = Stories(tmp_path)
    assert "secret-test-value" not in json.dumps(api.provider_settings())
    for provider in ["openai", "chatgpt", "copilot", "anthropic", "gemini"]:
        assert api.configure_provider(provider)["provider"] == provider
    with pytest.raises(StoriesError) as exc:
        api.test_provider()
    assert exc.value.code == "model_access_required"


def test_all_capabilities_have_cli_help(tmp_path):
    import subprocess
    import sys

    from amplifier_smart_tool_stories.lib import CAPABILITIES

    for name in CAPABILITIES:
        p = subprocess.run(
            [sys.executable, "-m", "amplifier_smart_tool_stories", name.replace("_", "-"), "--help"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert p.returncode == 0 and "--input" in p.stdout


def test_runtime_cache_never_cold_prepares_or_activates(tmp_path, monkeypatch):
    import hashlib
    import pickle
    import sys
    from types import SimpleNamespace

    from amplifier_smart_tool_stories import providers

    mark = tmp_path / 'stories-openai-ready.json'
    monkeypatch.setattr(providers, 'marker', lambda config: mark)
    config = ProviderConfig('openai')
    artifact = pickle.dumps(SimpleNamespace())
    (tmp_path / 'prepared.pickle').write_bytes(artifact)
    module = tmp_path / 'provider'
    module.mkdir()
    mark.write_text(json.dumps({
        'python_prefix': sys.prefix,
        'artifact_sha256': hashlib.sha256(artifact).hexdigest(),
        'module_paths': {'provider-openai': str(module)},
    }))
    bundle = providers._load_local_runtime(config)
    assert bundle.resolver._activator is None
    assert bundle.resolver.resolve('provider-openai').resolve() == module
    module.rmdir()
    with pytest.raises(StoriesError, match='missing or changed'):
        providers._load_local_runtime(config)
    module.mkdir()
    (tmp_path / 'prepared.pickle').write_bytes(b'corrupt')
    with pytest.raises(StoriesError, match='missing or changed'):
        providers._load_local_runtime(config)
    mark.unlink()
    with pytest.raises(StoriesError, match='missing or changed'):
        providers._load_local_runtime(config)


def test_in_process_cli_reports_model_failure_nonzero(tmp_path):
    import os
    import subprocess
    import sys

    env = {k: v for k, v in os.environ.items() if k not in ENV['openai']}
    payload = {'title': 'Test', 'purpose': 'Explain', 'audience': 'Reader',
               'sources': [{'id': 's', 'content': 'A supplied fact.'}],
               'grant': {'timeout_seconds': 10}, 'request_id': 'missing-key'}
    result = subprocess.run(
        [sys.executable, '-m', 'amplifier_smart_tool_stories', '--store', str(tmp_path),
         '--provider', 'openai', '--model-env', '--execution', 'in_process',
         'generate', '--input', json.dumps(payload)],
        env=env, capture_output=True, text=True, timeout=20,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)['operation']['state'] == 'failed'
