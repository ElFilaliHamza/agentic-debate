"""Role definitions for debate participants."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    """A debate participant role with display attributes."""

    key: str
    label: str
    icon: str
    style: str
    text_style: str


PROPOSER = Role(
    key="proposer",
    label="Proposer",
    icon="🛡️",
    style="proposer",
    text_style="proposer.text",
)

CRITIC = Role(
    key="critic",
    label="Critic",
    icon="⚔️",
    style="critic",
    text_style="critic.text",
)

SPEAKER_A = Role(
    key="speaker_a",
    label="Ahmed",
    icon="🛡️",
    style="speaker_a",
    text_style="speaker_a.text",
)

SPEAKER_B = Role(
    key="speaker_b",
    label="Khaled",
    icon="⚔️",
    style="speaker_b",
    text_style="speaker_b.text",
)

JUDGE = Role(
    key="judge",
    label="Judge",
    icon="⚖️",
    style="judge",
    text_style="judge.text",
)

HOST = Role(
    key="host",
    label="Host",
    icon="🎙️",
    style="host",
    text_style="host.text",
)

# Lookup by key for generic access
ROLES: dict[str, Role] = {
    "proposer": PROPOSER,
    "critic": CRITIC,
    "speaker_a": SPEAKER_A,
    "speaker_b": SPEAKER_B,
    "judge": JUDGE,
    "host": HOST,
}

TOOL_ICONS: dict[str, str] = {
    "search": "🔍",
    "detect_fallacy": "🎯",
    "quote": "📜",
    "poll": "📊",
    "sentiment": "🎭",
    "joke": "😄",
}
