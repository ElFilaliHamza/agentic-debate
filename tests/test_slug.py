"""Tests for voice.slug — motion-to-slug and debate directory creation."""

import tempfile
from pathlib import Path

from voice.slug import create_debate_dir, motion_to_slug


class TestMotionToSlug:
    def test_simple_motion(self):
        assert motion_to_slug("AI should replace teachers") == "ai-should-replace-teachers"

    def test_special_characters_removed(self):
        assert motion_to_slug("Free speech is absolute!") == "free-speech-is-absolute"

    def test_multiple_spaces_collapsed(self):
        assert motion_to_slug("AI  is   great") == "ai-is-great"

    def test_leading_trailing_hyphens_stripped(self):
        assert motion_to_slug("  hello world  ") == "hello-world"

    def test_long_motion_truncated(self):
        motion = " ".join(["word"] * 20)
        result = motion_to_slug(motion)
        assert len(result) <= 50

    def test_empty_string(self):
        assert motion_to_slug("") == "debate"

    def test_only_special_chars(self):
        assert motion_to_slug("!!! ???") == "debate"


class TestCreateDebateDir:
    def test_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            motion = "AI should replace teachers"
            result = create_debate_dir(motion, base_dir=Path(tmp))
            assert result.is_dir()
            assert result.parent == Path(tmp)
            assert "ai-should-replace-teachers" in result.name

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            motion = "AI should replace teachers"
            first = create_debate_dir(motion, base_dir=Path(tmp))
            second = create_debate_dir(motion, base_dir=Path(tmp))
            assert first == second