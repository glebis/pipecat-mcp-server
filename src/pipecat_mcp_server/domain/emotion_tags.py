"""Pure-function emotion tag processing for Orpheus and Cartesia TTS.

This module strips or converts Orpheus-style emotion markup without
any pipecat framework dependencies -- only ``re`` from the stdlib.
"""

import re

# Patterns to match Orpheus emotion tags
_BRACKET_TAG_RE = re.compile(r"\[(?:cheerful|whisper|excited|sad|calm)\]\s*", re.IGNORECASE)
_EMOTION_TAG_RE = re.compile(
    r"<(?:laugh|chuckle|sigh|gasp|yawn|groan|cough|sniffle)>\s*", re.IGNORECASE
)

# Orpheus bracket tag -> Cartesia <emotion value="..."/> mapping
_ORPHEUS_TO_CARTESIA = {
    "cheerful": "happy",
    "whisper": "calm",  # No whisper in Cartesia; calm is closest
    "excited": "excited",
    "sad": "sad",
    "calm": "calm",
}

# Presets that support Orpheus-style emotional markup natively (pass through).
_ORPHEUS_PRESETS = {"groq"}

# Presets that support Cartesia-style SSML emotion tags (convert from Orpheus).
_CARTESIA_PRESETS = {"cartesia"}


def _strip_emotion_tags(text: str) -> str:
    """Remove Orpheus-style emotion markup from text."""
    text = _BRACKET_TAG_RE.sub("", text)
    text = _EMOTION_TAG_RE.sub("", text)
    return text.strip()


def _orpheus_to_cartesia(text: str) -> str:
    """Convert Orpheus emotion tags to Cartesia SSML-like emotion tags.

    Bracket directions like [cheerful] become <emotion value="happy"/>.
    Non-speech sounds like <laugh> are stripped (Cartesia can't produce them).
    """

    def replace_bracket(match: re.Match) -> str:
        """Replace a single bracket emotion tag with Cartesia SSML."""
        tag = match.group(1).lower()
        cartesia_emotion = _ORPHEUS_TO_CARTESIA.get(tag)
        if cartesia_emotion:
            return f'<emotion value="{cartesia_emotion}"/>'
        return ""

    # Convert bracket directions [cheerful] -> <emotion value="happy"/>
    text = re.sub(
        r"\[(cheerful|whisper|excited|sad|calm)\]\s*",
        replace_bracket,
        text,
        flags=re.IGNORECASE,
    )
    # Strip non-speech sounds (Cartesia can't produce them)
    text = _EMOTION_TAG_RE.sub("", text)
    return text.strip()
