"""Infrastructure layer: concrete STT/TTS service factories.

These functions encapsulate the creation of speech-to-text and text-to-speech
service instances based on a voice preset name. They are allowed to depend on
external frameworks (pipecat service classes) -- that is the purpose of the
infrastructure layer.
"""

import os
import sys
from typing import Any


def create_stt_service(preset: str) -> Any:
    """Create an STT service based on the voice preset.

    Args:
        preset: Voice preset name (groq, deepgram, cartesia, local, kokoro).

    Returns:
        An STT service instance.

    Raises:
        ValueError: If required API keys are missing.

    """
    if preset in ("deepgram", "cartesia"):
        api_key = os.getenv("DEEPGRAM_API_KEY", "")
        if not api_key:
            raise ValueError(f"DEEPGRAM_API_KEY required for '{preset}' preset")
        from pipecat.services.deepgram import DeepgramSTTService

        return DeepgramSTTService(
            api_key=api_key,
            model="nova-3-general",
        )

    if preset in ("local", "kokoro"):
        if sys.platform == "darwin":
            from pipecat.services.whisper.stt import WhisperSTTServiceMLX

            return WhisperSTTServiceMLX(model="mlx-community/whisper-large-v3-turbo")
        else:
            from pipecat.services.whisper.stt import WhisperSTTService

            return WhisperSTTService(model="Systran/faster-distil-whisper-large-v3")

    # Default: groq
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        raise ValueError("GROQ_API_KEY required for 'groq' preset")
    from pipecat.services.groq import GroqSTTService

    return GroqSTTService(
        api_key=groq_key,
        model="whisper-large-v3-turbo",
    )


def create_tts_service(preset: str) -> Any:
    """Create a TTS service based on the voice preset.

    Args:
        preset: Voice preset name (groq, deepgram, cartesia, local, kokoro).

    Returns:
        A TTS service instance.

    Raises:
        ValueError: If required API keys are missing.

    """
    if preset == "deepgram":
        api_key = os.getenv("DEEPGRAM_API_KEY", "")
        if not api_key:
            raise ValueError("DEEPGRAM_API_KEY required for 'deepgram' preset")
        from pipecat.services.deepgram import DeepgramTTSService

        return DeepgramTTSService(
            api_key=api_key,
            voice="aura-2-en-US-asteria",
        )

    if preset == "cartesia":
        api_key = os.getenv("CARTESIA_API_KEY", "")
        if not api_key:
            raise ValueError("CARTESIA_API_KEY required for 'cartesia' preset")
        from pipecat.services.cartesia import CartesiaTTSService

        return CartesiaTTSService(
            api_key=api_key,
            voice_id="a0e99841-438c-4a64-b679-ae501e7d6091",
        )

    if preset == "kokoro":
        from pipecat_mcp_server.processors.kokoro_tts import KokoroTTSService

        return KokoroTTSService(voice_id="af_heart")

    if preset == "local":
        from pipecat.services.piper import PiperTTSService

        return PiperTTSService(voice="en_US-amy-medium")

    # Default: groq
    api_key = os.getenv("GROQ_API_KEY", "")
    from pipecat.services.groq import GroqTTSService

    return GroqTTSService(
        api_key=api_key,
        model_name="canopylabs/orpheus-v1-english",
        voice_id="hannah",
    )
