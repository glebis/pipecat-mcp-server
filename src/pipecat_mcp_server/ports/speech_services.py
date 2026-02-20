"""Port interfaces for speech services (STT and TTS)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class STTServicePort(Protocol):
    """Protocol for speech-to-text services."""

    ...


@runtime_checkable
class TTSServicePort(Protocol):
    """Protocol for text-to-speech services."""

    ...
