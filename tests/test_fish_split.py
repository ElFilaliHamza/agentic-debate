"""Tests for voice.fish._split_text — paragraph/sentence boundary splitting."""

from voice.fish import _split_text, MAX_CHUNK_LENGTH


class TestSplitTextShort:
    """Texts that fit in a single chunk should be returned as-is."""

    def test_short_text_unchanged(self):
        text = "Hello world."
        assert _split_text(text) == [text]

    def test_exactly_max_length(self):
        text = "a" * MAX_CHUNK_LENGTH
        assert _split_text(text) == [text]

    def test_empty_after_strip(self):
        # Single char is fine
        assert _split_text("Hi.") == ["Hi."]


class TestSplitTextParagraphs:
    """Splitting on paragraph boundaries (double newlines)."""

    def test_two_paragraphs_fit_together(self):
        para1 = "First paragraph."
        para2 = "Second paragraph."
        text = f"{para1}\n\n{para2}"
        result = _split_text(text, max_length=500)
        assert result == [text]

    def test_two_paragraphs_split(self):
        para1 = "a. " * 50  # ~150 chars
        para2 = "b. " * 50  # ~150 chars
        text = f"{para1.strip()}\n\n{para2.strip()}"
        # Max length 200 means they can't fit together
        result = _split_text(text, max_length=200)
        assert len(result) == 2
        assert result[0].strip() == para1.strip()
        assert result[1].strip() == para2.strip()

    def test_three_paragraphs_grouped(self):
        para1 = "Short one."
        para2 = "Short two."
        para3 = "Short three."
        text = f"{para1}\n\n{para2}\n\n{para3}"
        result = _split_text(text, max_length=200)
        # All three should fit in one chunk
        assert len(result) == 1


class TestSplitTextSentences:
    """Falling back to sentence boundaries for long paragraphs."""

    def test_long_paragraph_split_at_sentences(self):
        sentences = [f"Sentence number {i}." for i in range(20)]
        text = " ".join(sentences)
        result = _split_text(text, max_length=100)
        assert len(result) > 1
        # Each chunk must be <= max_length
        for chunk in result:
            assert len(chunk) <= 100
        # No chunk should split mid-sentence
        for chunk in result:
            # Should end with a sentence-ending punctuation
            assert chunk[-1] in ".!?", f"Chunk doesn't end at sentence boundary: ...{chunk[-20:]}"

    def test_no_mid_sentence_split(self):
        text = "This is a very long sentence that goes on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on and on."
        result = _split_text(text, max_length=50)
        # The whole thing is one sentence, so it goes as one chunk even if over max_length
        assert len(result) == 1
        assert result[0] == text


class TestSplitTextRealWorld:
    """Realistic debate text patterns."""

    def test_host_text(self):
        text = (
            "Someone is programming your reality. The stakes are your mind. "
            "Tonight we debate whether governments should regulate social media "
            "algorithms to reduce misinformation, or if that just trades a chaotic "
            "truth for a controlled lie. Ahmed, you're up."
        )
        result = _split_text(text, max_length=500)
        assert len(result) == 1  # Should fit in one chunk

    def test_long_speaker_text(self):
        text = (
            "The opposition will say this is about free speech. It's not. "
            "This is about a machine that decides, silently, that a lie is more "
            "profitable than truth.\n\n"
            "An MIT study analyzed every contested rumor on Twitter over eleven years. "
            "False news reaches more people and spreads faster than truth. Not by a "
            "little. False political stories reached 20,000 people; true ones barely "
            "1,000. Algorithms do what they're built to do: maximize engagement. More "
            "outrage, more revenue. So they amplified the lies.\n\n"
            "Trust these companies to self-regulate? They've had a decade. They promised "
            "fact-checking, community notes. Meanwhile, misinformation erodes public "
            "trust. I don't believe the free market corrects lies when lies are more "
            "profitable.\n\n"
            "Regulation doesn't mean government decides what's true. It means requiring "
            "transparency about what algorithms amplify and why. Every industry affecting "
            "public safety faces oversight. Why should social media be exempt?\n\n"
            "The opposition will cry censorship. But regulation isn't banning speech — "
            "it's stopping machines from amplifying lies for profit. If you can't see "
            "the difference, you're not paying attention."
        )
        result = _split_text(text, max_length=500)
        assert len(result) > 1  # Should split into multiple chunks
        # Each chunk should be <= max_length
        for chunk in result:
            assert len(chunk) <= 500
        # Reassembled text should preserve all content (minus extra whitespace)
        reassembled = " ".join(chunk.replace("\n\n", " ") for chunk in result)
        original = text.replace("\n\n", " ")
        # All significant words should be present
        for word in original.split():
            assert word in reassembled, f"Missing word: {word}"