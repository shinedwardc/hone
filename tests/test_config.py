"""Provider resolution: a flag beats an env var beats the preset, and a missing key stops the run."""

import argparse

import pytest

from hone.cli import DEFAULT_MAX_TOKENS, DEFAULT_PROVIDER, PROVIDERS, resolve_config

ENV_VARS = (
    "HONE_PROVIDER",
    "HONE_API_KEY",
    "HONE_BASE_URL",
    "HONE_MODEL",
    "HONE_MAX_TOKENS",
    *(preset["api_key_env"] for preset in PROVIDERS.values()),
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Hide the real environment so a developer's own keys cannot change the outcome."""
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def args(provider=None, model=None, base_url=None):
    """The parsed flags resolve_config reads, with everything unset by default."""
    return argparse.Namespace(provider=provider, model=model, base_url=base_url)


def test_falls_back_to_the_default_provider_preset(monkeypatch):
    """Assert an unflagged run resolves to DEFAULT_PROVIDER and that preset's values"""
    preset = PROVIDERS[DEFAULT_PROVIDER]
    monkeypatch.setenv(preset["api_key_env"], "key-from-env")

    config = resolve_config(args())

    assert config["provider"] == DEFAULT_PROVIDER
    assert config["base_url"] == preset["base_url"]
    assert config["model"] == preset["model"]
    assert config["api_key"] == "key-from-env"


@pytest.mark.parametrize("provider", sorted(PROVIDERS), ids=sorted(PROVIDERS))
def test_every_preset_resolves_its_own_endpoint_and_key(provider, monkeypatch):
    """Assert each named provider yields its own base_url, model, and api key env"""
    preset = PROVIDERS[provider]
    monkeypatch.setenv(preset["api_key_env"], f"{provider}-key")

    config = resolve_config(args(provider=provider))

    assert config["base_url"] == preset["base_url"]
    assert config["model"] == preset["model"]
    assert config["api_key"] == f"{provider}-key"


def test_unknown_provider_is_refused_with_the_known_names(monkeypatch):
    """Assert an unrecognised provider exits and lists the providers that do exist"""
    with pytest.raises(SystemExit) as excinfo:
        resolve_config(args(provider="not-a-provider"))

    message = str(excinfo.value)
    assert "not-a-provider" in message
    for known in PROVIDERS:
        assert known in message


def test_a_missing_api_key_names_the_variable_to_set(monkeypatch):
    """Assert a run with no key exits naming that provider's env var and HONE_API_KEY"""
    with pytest.raises(SystemExit) as excinfo:
        resolve_config(args(provider="anthropic"))

    message = str(excinfo.value)
    assert "anthropic" in message
    assert PROVIDERS["anthropic"]["api_key_env"] in message
    assert "HONE_API_KEY" in message


def test_hone_api_key_serves_any_provider(monkeypatch):
    """Assert HONE_API_KEY satisfies a provider whose own key variable is unset"""
    monkeypatch.setenv("HONE_API_KEY", "generic-key")

    assert resolve_config(args(provider="ollama"))["api_key"] == "generic-key"


def test_hone_api_key_beats_the_provider_specific_variable(monkeypatch):
    """Assert the generic key wins when both it and the provider's own key are set"""
    monkeypatch.setenv("HONE_API_KEY", "generic-key")
    monkeypatch.setenv(PROVIDERS["anthropic"]["api_key_env"], "specific-key")

    assert resolve_config(args(provider="anthropic"))["api_key"] == "generic-key"


def test_the_provider_env_var_is_used_without_a_flag(monkeypatch):
    """Assert HONE_PROVIDER selects the preset when no --provider is given"""
    monkeypatch.setenv("HONE_PROVIDER", "ollama")
    monkeypatch.setenv(PROVIDERS["ollama"]["api_key_env"], "key")

    assert resolve_config(args())["provider"] == "ollama"


def test_the_provider_flag_beats_the_provider_env_var(monkeypatch):
    """Assert --provider overrides HONE_PROVIDER"""
    monkeypatch.setenv("HONE_PROVIDER", "ollama")
    monkeypatch.setenv("HONE_API_KEY", "key")

    assert resolve_config(args(provider="anthropic"))["provider"] == "anthropic"


@pytest.mark.parametrize(
    "field, flag, env_var",
    [("model", "model", "HONE_MODEL"), ("base_url", "base_url", "HONE_BASE_URL")],
)
def test_the_flag_beats_the_env_var_beats_the_preset(field, flag, env_var, monkeypatch):
    """Assert model and base_url each resolve flag first, then env var, then preset"""
    preset = PROVIDERS[DEFAULT_PROVIDER]
    monkeypatch.setenv(preset["api_key_env"], "key")

    assert resolve_config(args())[field] == preset[field]

    monkeypatch.setenv(env_var, "from-env")
    assert resolve_config(args())[field] == "from-env"

    assert resolve_config(args(**{flag: "from-flag"}))[field] == "from-flag"


def test_max_tokens_defaults_to_the_constant(monkeypatch):
    """Assert an unset HONE_MAX_TOKENS leaves DEFAULT_MAX_TOKENS in place"""
    monkeypatch.setenv(PROVIDERS[DEFAULT_PROVIDER]["api_key_env"], "key")

    assert resolve_config(args())["max_tokens"] == DEFAULT_MAX_TOKENS


def test_max_tokens_comes_back_as_an_int(monkeypatch):
    """Assert HONE_MAX_TOKENS overrides the default and is converted from its string"""
    monkeypatch.setenv(PROVIDERS[DEFAULT_PROVIDER]["api_key_env"], "key")
    monkeypatch.setenv("HONE_MAX_TOKENS", "512")

    max_tokens = resolve_config(args())["max_tokens"]

    assert max_tokens == 512
    assert isinstance(max_tokens, int)
