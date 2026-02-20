"""Tests for domain.voice_preset pure-function module."""

from pipecat_mcp_server.domain.voice_preset import (
    PRESET_REQUIRED_KEYS,
    VALID_PRESETS,
    VoicePresetConfig,
    resolve_preset,
    validate_preset_with_env,
)


class TestResolvePreset:
    """resolve_preset() resolves and validates preset names."""

    def test_none_defaults_to_groq(self):
        """Passing None should default to the 'groq' preset."""
        config = resolve_preset(None)
        assert config.name == "groq"
        assert config.is_valid is True
        assert "GROQ_API_KEY" in config.required_keys

    def test_groq_returns_valid_config(self):
        """Explicit 'groq' should return a valid config requiring GROQ_API_KEY."""
        config = resolve_preset("groq")
        assert config.name == "groq"
        assert config.is_valid is True
        assert config.required_keys == ["GROQ_API_KEY"]
        assert config.error is None

    def test_invalid_preset_returns_error(self):
        """An unknown preset name should return is_valid=False with an error message."""
        config = resolve_preset("invalid")
        assert config.is_valid is False
        assert config.error is not None
        assert "invalid" in config.error.lower() or "Unknown" in config.error

    def test_local_requires_no_keys(self):
        """The 'local' preset requires no API keys."""
        config = resolve_preset("local")
        assert config.name == "local"
        assert config.is_valid is True
        assert config.required_keys == []

    def test_cartesia_requires_two_keys(self):
        """The 'cartesia' preset requires both DEEPGRAM_API_KEY and CARTESIA_API_KEY."""
        config = resolve_preset("cartesia")
        assert config.is_valid is True
        assert "DEEPGRAM_API_KEY" in config.required_keys
        assert "CARTESIA_API_KEY" in config.required_keys

    def test_case_insensitive(self):
        """Preset names should be case-insensitive."""
        config = resolve_preset("GROQ")
        assert config.name == "groq"
        assert config.is_valid is True


class TestValidatePresetWithEnv:
    """validate_preset_with_env() checks env vars for required API keys."""

    def test_groq_with_key_present(self):
        """Groq preset with GROQ_API_KEY set should have no missing keys."""
        env = {"VOICE_PRESET": "groq", "GROQ_API_KEY": "key"}
        config = validate_preset_with_env(env)
        assert config.name == "groq"
        assert config.missing_keys == []
        assert config.error is None

    def test_groq_missing_key(self):
        """Groq preset without GROQ_API_KEY should report it as missing."""
        env = {"VOICE_PRESET": "groq"}
        config = validate_preset_with_env(env)
        assert config.name == "groq"
        assert "GROQ_API_KEY" in config.missing_keys
        assert config.error is not None
        assert "GROQ_API_KEY" in config.error

    def test_local_no_keys_needed(self):
        """Local preset requires no keys, so should always validate."""
        env = {"VOICE_PRESET": "local"}
        config = validate_preset_with_env(env)
        assert config.name == "local"
        assert config.missing_keys == []
        assert config.error is None

    def test_default_preset_from_env(self):
        """Without VOICE_PRESET in env, should default to 'groq'."""
        env = {"GROQ_API_KEY": "key"}
        config = validate_preset_with_env(env)
        assert config.name == "groq"
        assert config.missing_keys == []

    def test_invalid_preset_from_env(self):
        """Invalid VOICE_PRESET in env should propagate the error."""
        env = {"VOICE_PRESET": "nonexistent"}
        config = validate_preset_with_env(env)
        assert config.is_valid is False
        assert config.error is not None

    def test_cartesia_partial_keys(self):
        """Cartesia with only one of two required keys should report the missing one."""
        env = {"VOICE_PRESET": "cartesia", "DEEPGRAM_API_KEY": "dg-key"}
        config = validate_preset_with_env(env)
        assert "CARTESIA_API_KEY" in config.missing_keys
        assert "DEEPGRAM_API_KEY" not in config.missing_keys


class TestVoicePresetConfigImmutability:
    """VoicePresetConfig is a frozen dataclass."""

    def test_frozen(self):
        """Attempting to modify a field should raise an error."""
        config = resolve_preset("groq")
        with __import__("pytest").raises(AttributeError):
            config.name = "other"
