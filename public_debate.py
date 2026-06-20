from dotenv import load_dotenv
import os
import sys
import time
from ollama import Client
from helpers import enforce_limit, format_opponent_argument
from public_debate_system_prompt import (
    SPEAKER_A_SYSTEM_PROMPT,
    SPEAKER_B_SYSTEM_PROMPT,
    JUDGE_SYSTEM_PROMPT,
)

load_dotenv()
MODEL = "glm-5.1:cloud"
ROUNDS = int(os.getenv("DEBATE_ROUNDS", 3))
MAX_CHARS = int(os.getenv("DEBATE_MAX_CHARS", 300))
OLLAMA_HOST = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "")
TYPING_DELAY = float(os.getenv("TYPING_DELAY", "0.02"))

client = Client(
    host=OLLAMA_HOST,
    headers=({"Authorization": f"Bearer {OLLAMA_API_KEY}"} if OLLAMA_API_KEY else None),
)


def stream_agent(messages: list[dict], system_prompt: str = "", tools: list = []) -> str:
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
            for char in text:
                sys.stdout.write(char)
                sys.stdout.flush()
                time.sleep(TYPING_DELAY)
            full_response += text
    print()
    return full_response


def run_debate(
    motion: str,
    max_rounds: int = ROUNDS,
    max_chars: int = MAX_CHARS,
    speaker_a_name: str = "Speaker A",
    speaker_b_name: str = "Speaker B",
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
    transcript = []

    for round_num in range(max_rounds):
        print(f"\n--- Round {round_num + 1} ---")

        print(f"\n{speaker_a_name} (FOR): ", end="", flush=True)
        a_response = stream_agent(
            (
                speaker_a_msgs
                + format_opponent_argument(speaker_b_name, last_b_response)
                if round_num > 0
                else speaker_a_msgs
            ),
            SPEAKER_A_SYSTEM_PROMPT.format(motion=motion, MAX_CHARS=max_chars),
        )
        a_response = enforce_limit(a_response, max_chars)
        speaker_a_msgs.append({"role": "assistant", "content": a_response})
        transcript.append((speaker_a_name, a_response))

        print(f"\n{speaker_b_name} (AGAINST): ", end="", flush=True)
        b_response = stream_agent(
            (
                speaker_b_msgs + format_opponent_argument(speaker_a_name, a_response)
                if round_num > 0
                else speaker_b_msgs
            ),
            SPEAKER_B_SYSTEM_PROMPT.format(motion=motion, MAX_CHARS=max_chars),
        )
        b_response = enforce_limit(b_response, max_chars)
        speaker_b_msgs.append({"role": "assistant", "content": b_response})
        transcript.append((speaker_b_name, b_response))

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

    print("\nJudge's verdict: ", end="", flush=True)
    verdict = stream_agent(
        judge_input, JUDGE_SYSTEM_PROMPT.format(motion=motion, MAX_CHARS=max_chars)
    )
    verdict = enforce_limit(verdict, max_chars)

    return verdict


if __name__ == "__main__":
    motion = input("Enter the debate motion: ")
    transcript = run_debate(motion)
    judge_debate(transcript, motion)