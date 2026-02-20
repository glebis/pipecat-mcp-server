"""Tests for Orpheus emotion tag processing functions."""

from pipecat_mcp_server.domain.emotion_tags import _orpheus_to_cartesia, _strip_emotion_tags


class TestStripEmotionTags:
    """Slice 1: _strip_emotion_tags removes all Orpheus-style emotion markup."""

    def test_strips_bracket_tags_and_sound_tags(self):
        """All bracket and sound tags are removed from mixed text."""
        # Arrange
        text = "[cheerful] Hello <laugh> how are <sigh> you [WHISPER] today"

        # Act
        result = _strip_emotion_tags(text)

        # Assert
        assert result == "Hello how are you today"

    def test_strips_all_bracket_tag_variants(self):
        """Each bracket emotion variant is stripped."""
        text = "[excited] Go! [sad] Oh no [calm] Relax"
        result = _strip_emotion_tags(text)
        assert result == "Go! Oh no Relax"

    def test_strips_all_sound_tag_variants(self):
        """Each angle-bracket sound variant is stripped."""
        text = "<chuckle> Ha <gasp> Wow <yawn> Tired <groan> Ugh <cough> Ahem <sniffle> Sniff"
        result = _strip_emotion_tags(text)
        assert result == "Ha Wow Tired Ugh Ahem Sniff"

    def test_case_insensitive(self):
        """Tags in any case are stripped."""
        text = "[CHEERFUL] Hello <LAUGH> there"
        result = _strip_emotion_tags(text)
        assert result == "Hello there"

    def test_plain_text_unchanged(self):
        """Plain text without tags passes through unchanged."""
        text = "Hello, how are you?"
        result = _strip_emotion_tags(text)
        assert result == "Hello, how are you?"


class TestOrpheusToCartesia:
    """Slice 2: _orpheus_to_cartesia converts Orpheus tags to Cartesia SSML emotion tags."""

    def test_cheerful_converts_to_happy(self):
        """[cheerful] maps to Cartesia happy emotion."""
        text = "[cheerful] Hello there"
        result = _orpheus_to_cartesia(text)
        assert result == '<emotion value="happy"/>Hello there'

    def test_whisper_converts_to_calm(self):
        """[whisper] maps to Cartesia calm emotion."""
        text = "[whisper] Be quiet"
        result = _orpheus_to_cartesia(text)
        assert result == '<emotion value="calm"/>Be quiet'

    def test_excited_converts_to_excited(self):
        """[excited] maps to Cartesia excited emotion."""
        text = "[excited] Wow!"
        result = _orpheus_to_cartesia(text)
        assert result == '<emotion value="excited"/>Wow!'

    def test_sad_converts_to_sad(self):
        """[sad] maps to Cartesia sad emotion."""
        text = "[sad] I'm sorry"
        result = _orpheus_to_cartesia(text)
        assert result == '<emotion value="sad"/>I\'m sorry'

    def test_calm_converts_to_calm(self):
        """[calm] maps to Cartesia calm emotion."""
        text = "[calm] Everything is fine"
        result = _orpheus_to_cartesia(text)
        assert result == '<emotion value="calm"/>Everything is fine'

    def test_strips_non_speech_sounds(self):
        """Non-speech sound tags are removed (Cartesia cannot produce them)."""
        text = "Hello <laugh> world <sigh> goodbye"
        result = _orpheus_to_cartesia(text)
        assert result == "Hello world goodbye"

    def test_case_insensitive(self):
        """Uppercase tags are converted correctly."""
        text = "[CHEERFUL] Hello"
        result = _orpheus_to_cartesia(text)
        assert result == '<emotion value="happy"/>Hello'
