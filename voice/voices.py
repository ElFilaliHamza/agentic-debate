"""Voice pools per role and random assignment with no duplicates."""

from __future__ import annotations

import random

MODERATOR_VOICES = ["en-US-EricNeural", "en-US-GuyNeural", "en-US-ChristopherNeural"]
PROPOSER_VOICES = ["en-US-GuyNeural", "en-US-BrianNeural", "en-US-JennyNeural"]
CRITIC_VOICES = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-MichelleNeural"]
SPEAKER_A_VOICES = ["en-US-GuyNeural", "en-US-BrianNeural", "en-US-ChristopherNeural"]
SPEAKER_B_VOICES = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-MichelleNeural"]
JUDGE_VOICES = ["en-US-ChristopherNeural", "en-US-EricNeural", "en-US-GuyNeural"]


class VoiceAssignment:
    """Assigns unique voices to each role for a debate session.

    Guarantees no two roles share the same voice in a single session.
    """

    def __init__(self) -> None:
        self._assignments: dict[str, str] = {}
        self._used_voices: set[str] = set()

    def _pick_unique(self, pool: list[str]) -> str:
        """Pick a voice from pool that hasn't been used yet."""
        available = [v for v in pool if v not in self._used_voices]
        if not available:
            available = pool
        voice = random.choice(available)
        self._used_voices.add(voice)
        return voice

    @property
    def moderator(self) -> str:
        if "moderator" not in self._assignments:
            self._assignments["moderator"] = self._pick_unique(MODERATOR_VOICES)
        return self._assignments["moderator"]

    @property
    def proposer(self) -> str:
        if "proposer" not in self._assignments:
            self._assignments["proposer"] = self._pick_unique(PROPOSER_VOICES)
        return self._assignments["proposer"]

    @property
    def critic(self) -> str:
        if "critic" not in self._assignments:
            self._assignments["critic"] = self._pick_unique(CRITIC_VOICES)
        return self._assignments["critic"]

    @property
    def speaker_a(self) -> str:
        if "speaker_a" not in self._assignments:
            self._assignments["speaker_a"] = self._pick_unique(SPEAKER_A_VOICES)
        return self._assignments["speaker_a"]

    @property
    def speaker_b(self) -> str:
        if "speaker_b" not in self._assignments:
            self._assignments["speaker_b"] = self._pick_unique(SPEAKER_B_VOICES)
        return self._assignments["speaker_b"]

    @property
    def judge(self) -> str:
        if "judge" not in self._assignments:
            self._assignments["judge"] = self._pick_unique(JUDGE_VOICES)
        return self._assignments["judge"]

    def get_voice(self, role_key: str) -> str:
        """Get voice for a role by key (e.g., 'moderator', 'speaker_a')."""
        return getattr(self, role_key)