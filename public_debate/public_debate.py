from dotenv import load_dotenv
import os
from ollama import Client
from public_debate.helpers import enforce_limit, format_opponent_argument
from public_debate.public_debate_system_prompt import (
    SPEAKER_A_SYSTEM_PROMPT,
    SPEAKER_B_SYSTEM_PROMPT,
    JUDGE_SYSTEM_PROMPT,
)
from tui_formatter.console import console
from tui_formatter.formatter import (
    print_speaker_label,
    print_thinking,
    print_verdict,
    prompt_motion,
)
from tui_formatter.roles import JUDGE, SPEAKER_A, SPEAKER_B

load_dotenv()
MODEL = "glm-5.1:cloud"
ROUNDS = int(os.getenv("DEBATE_ROUNDS", 3))
MAX_CHARS = int(os.getenv("DEBATE_MAX_CHARS", 300))
OLLAMA_HOST = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")

client = Client(
    host=OLLAMA_HOST,
    headers=({"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else None),
)


def stream_agent(
    messages: list[dict],
    system_prompt: str = "",
    tools: list = [],
    role_style: str = "",
) -> str:
    """Stream an agent's response character-by-character via Rich console."""
    all_messages = (
        [{"role": "system", "content": system_prompt}] + messages
        if system_prompt
        else messages
    )
    stream = client.chat(
        model=MODEL,
        messages=all_messages,
        tools=tools,
        stream=True,
    )
    full_response = ""
    for chunk in stream:
        if chunk.message and chunk.message.content:
            text = chunk.message.content
            console.print(text, end="", style=role_style, highlight=False)
            full_response += text
    console.print()
    return full_response


def call_agent(
    messages: list[dict], system_prompt: str = "", tools: list = []
) -> str:
    """Call an agent without streaming (returns full response at once)."""
    all_messages = (
        [{"role": "system", "content": system_prompt}] + messages
        if system_prompt
        else messages
    )
    response = client.chat(
        model=MODEL,
        messages=all_messages,
        tools=tools,
    )
    return response.message.content if response.message else ""


def run_debate(
    motion: str,
    max_rounds: int = ROUNDS,
    max_chars: int = MAX_CHARS,
) -> list[tuple[str, str]]:
    speaker_a_msgs = [
        {
            "role": "user",
            "content": f"You are starting a public debate. The motion is: {motion}",
        }
    ]
    speaker_b_msgs = [
        {
            "role": "user",
            "content": f"You are the second speaker in a public debate. The motion is: {motion}",
        }
    ]

    last_b_response = ""
    transcript: list[tuple[str, str]] = []

    for round_num in range(max_rounds):
        print_speaker_label(SPEAKER_A)
        a_response = stream_agent(
            (
                speaker_a_msgs + format_opponent_argument("Speaker B", last_b_response)
                if round_num > 0
                else speaker_a_msgs
            ),
            SPEAKER_A_SYSTEM_PROMPT.format(motion=motion, MAX_CHARS=max_chars),
            role_style=SPEAKER_A.text_style,
        )
        a_response = enforce_limit(a_response, max_chars)
        speaker_a_msgs.append({"role": "assistant", "content": a_response})
        transcript.append(("Speaker A", a_response))

        print_speaker_label(SPEAKER_B)
        b_response = stream_agent(
            (
                speaker_b_msgs + format_opponent_argument("Speaker A", a_response)
                if round_num > 0
                else speaker_b_msgs
            ),
            SPEAKER_B_SYSTEM_PROMPT.format(motion=motion, MAX_CHARS=max_chars),
            role_style=SPEAKER_B.text_style,
        )
        b_response = enforce_limit(b_response, max_chars)
        speaker_b_msgs.append({"role": "assistant", "content": b_response})
        transcript.append(("Speaker B", b_response))

        last_b_response = b_response

    return transcript


def judge_debate(
    transcript: list[tuple[str, str]],
    motion: str,
    max_chars: int = MAX_CHARS,
) -> str:
    debate_text = "\n".join(f"{speaker}: {content}" for speaker, content in transcript)

    judge_input = [
        {
            "role": "user",
            "content": f"Here is the full debate:\n{debate_text}\n\nPlease deliver your verdict.",
        }
    ]

    print_thinking(JUDGE)
    verdict = call_agent(
        judge_input,
        JUDGE_SYSTEM_PROMPT.format(motion=motion, MAX_CHARS=max_chars),
    )
    verdict = enforce_limit(verdict, max_chars)

    print_verdict(JUDGE, verdict)

    return verdict


if __name__ == "__main__":
    motion = prompt_motion()
    transcript = run_debate(motion)
    judge_debate(transcript, motion)
