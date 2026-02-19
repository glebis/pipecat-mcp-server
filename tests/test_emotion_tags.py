"""Tests for Orpheus emotion tag processing functions."""

from pipecat_mcp_server.agent import _orpheus_to_cartesia, _strip_emotion_tags


class TestStripEmotionTags:
    """Slice 1: _strip_emotion_tags removes all Orpheus-style emotion markup."""

    def test_strips_bracket_tags_and_sound_tags(self):
        # Arrange
        text = "[cheerful] Hello <laugh> how are <sigh> you [WHISPER] today"

        # Act
        result = _strip_emotion_tags(text)

        # Assert
        assert result == "Hello how are you today"

    def test_strips_all_bracket_tag_variants(self):
        text = "[excited] Go! [sad] Oh no [calm] Relax"
        result = _strip_emotion_tags(text)
        assert result == "Go! Oh no Relax"

    def test_strips_all_sound_tag_variants(self):
        text = "<chuckle> Ha <gasp> Wow <yawn> Tired <groan> Ugh <cough> Ahem <sniffle> Sniff"
        result = _strip_emotion_tags(text)
        assert result == "Ha Wow Tired Ugh Ahem Sniff"

    def test_case_insensitive(self):
        text = "[CHEERFUL] Hello <LAUGH> there"
        result = _strip_emotion_tags(text)
        assert result == "Hello there"

    def test_plain_text_unchanged(self):
        text = "Hello, how are you?"
        result = _strip_emotion_tags(text)
        assert result == "Hello, how are you?"


class TestOrpheusToCartesia:
    """Slice 2: _orpheus_to_cartesia converts Orpheus tags to Cartesia SSML emotion tags."""

    def test_cheerful_converts_to_happy(self):
        text = "[cheerful] Hello there"
        result = _orpheus_to_cartesia(text)
        assert result == '<emotion value="happy"/>Hello there'

    def test_whisper_converts_to_calm(self):
        text = "[whisper] Be quiet"
        result = _orpheus_to_cartesia(text)
        assert result == '<emotion value="calm"/>Be quiet'

    def test_excited_converts_to_excited(self):
        text = "[excited] Wow!"
        result = _orpheus_to_cartesia(text)
        assert result == '<emotion value="excited"/>Wow!'

    def test_sad_converts_to_sad(self):
        text = "[sad] I'm sorry"
        result = _orpheus_to_cartesia(text)
        assert result == '<emotion value="sad"/>I\'m sorry'

    def test_calm_converts_to_calm(self):
        text = "[calm] Everything is fine"
        result = _orpheus_to_cartesia(text)
        assert result == '<emotion value="calm"/>Everything is fine'

    def test_strips_non_speech_sounds(self):
        text = "Hello <laugh> world <sigh> goodbye"
        result = _orpheus_to_cartesia(text)
        assert result == "Hello world goodbye"

    def test_case_insensitive(self):
        text = "[CHEERFUL] Hello"
        result = _orpheus_to_cartesia(text)
        assert result == '<emotion value="happy"/>Hello'
