"""Pure-function voice preset resolution and validation.

This module resolves voice preset names and validates required API keys
without any external dependencies -- only ``dataclasses`` from the stdlib.
"""

from dataclasses import dataclass, field

VALID_PRESETS = ("groq", "deepgram", "cartesia", "local", "kokoro")

PRESET_REQUIRED_KEYS: dict[str, list[str]] = {
    "groq": ["GROQ_API_KEY"],
    "deepgram": ["DEEPGRAM_API_KEY"],
    "cartesia": ["DEEPGRAM_API_KEY", "CARTESIA_API_KEY"],
    "local": [],
    "kokoro": [],
}


@dataclass(frozen=True)
class VoicePresetConfig:
    """Immutable value object representing a resolved voice preset."""

    name: str
    required_keys: list[str] = field(default_factory=list)
    missing_keys: list[str] = field(default_factory=list)
    is_valid: bool = True
    error: str | None = None


def resolve_preset(preset_name: str | None = None) -> VoicePresetConfig:
    """Resolve and validate a voice preset by name.

    Args:
        preset_name: Preset name, or None for default ("groq").

    Returns:
        VoicePresetConfig with validation results.

    """
    name = (preset_name or "groq").lower()
    if name not in VALID_PRESETS:
        return VoicePresetConfig(
            name=name,
            is_valid=False,
            error=f"Unknown preset '{name}'. Valid: {', '.join(VALID_PRESETS)}",
        )
    required = PRESET_REQUIRED_KEYS.get(name, [])
    return VoicePresetConfig(name=name, required_keys=list(required))


def validate_preset_with_env(env: dict[str, str]) -> VoicePresetConfig:
    """Resolve preset from env and check required API keys.

    Args:
        env: Environment variables dict (typically os.environ).

    Returns:
        VoicePresetConfig with missing_keys populated.

    """
    config = resolve_preset(env.get("VOICE_PRESET"))
    if not config.is_valid:
        return config
    missing = [k for k in config.required_keys if not env.get(k)]
    if missing:
        return VoicePresetConfig(
            name=config.name,
            required_keys=config.required_keys,
            missing_keys=missing,
            is_valid=True,
            error=f"Missing API key(s) for '{config.name}' preset: {', '.join(missing)}",
        )
    return config
