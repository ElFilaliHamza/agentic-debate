from dotenv import load_dotenv
import os
from ollama import Client
from normal_critic_debate.debate_system_prompts import (
    PROPOSER_SYSTEM_PROMPT,
    CRITIC_SYSTEM_PROMPT,
    JUDGE_SYSTEM_PROMPT,
)
from tui_formatter.formatter import (
    print_claim,
    print_speaker_response,
    print_thinking,
    print_verdict,
    prompt_claim,
)
from tui_formatter.roles import CRITIC, JUDGE, PROPOSER

load_dotenv()
MODEL = "glm-5.1:cloud"
DEFAULT_ROUNDS = 3

client = Client(
    host=os.getenv("OLLAMA_API_URL", "http://localhost:11434"),
    headers=(
        {"Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY', '')}"}
        if os.getenv("OLLAMA_API_KEY")
        else None
    ),
)


def call_agent(messages: list[dict], system_prompt: str = "", tools: list = []) -> str:
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


def format_proposer_arguments(proposer_response: str) -> list[dict]:
    """Wrap the proposer's response as a user message for the critic."""
    if not proposer_response:
        return []
    return [
        {
            "role": "user",
            "content": "The proposer's arguments are: " + proposer_response,
        }
    ]


def format_critic_arguments(critic_response: str) -> list[dict]:
    """Wrap the critic's response as a user message for the proposer."""
    if not critic_response:
        return []
    return [{"role": "user", "content": "The critic's response is: " + critic_response}]


def format_judge_arguments(
    proposer_messages: list[dict], critic_messages: list[dict]
) -> list[dict]:
    """Combine the full debate history into a single user message for the judge."""
    proposer_text = "\n".join(
        msg["content"] for msg in proposer_messages if msg.get("content")
    )
    critic_text = "\n".join(
        msg["content"] for msg in critic_messages if msg.get("content")
    )
    debate_summary = (
        "Here is a debate between the Proposer and Critic over all rounds:\n"
        "Proposer's arguments:\n"
        f"{proposer_text}\n"
        "Critic's response:\n"
        f"{critic_text}"
    )
    return [{"role": "user", "content": debate_summary}]


def run_debate(claim: str, rounds: int = DEFAULT_ROUNDS) -> tuple[str, str, str]:
    proposer_messages = [{"role": "user", "content": claim}]
    critic_messages = []
    critic_response = ""
    proposer_response = ""
    transcript: list[tuple[str, str]] = []

    for round_num in range(rounds):
        print_thinking(PROPOSER)
        proposer_response = call_agent(
            proposer_messages + format_critic_arguments(critic_response),
            PROPOSER_SYSTEM_PROMPT,
        )
        print_speaker_response(PROPOSER, proposer_response)
        proposer_messages.append({"role": "assistant", "content": proposer_response})
        transcript.append(("Proposer", proposer_response))

        print_thinking(CRITIC)
        critic_response = call_agent(
            critic_messages + format_proposer_arguments(proposer_response),
            CRITIC_SYSTEM_PROMPT,
        )
        print_speaker_response(CRITIC, critic_response)
        critic_messages.append({"role": "assistant", "content": critic_response})
        transcript.append(("Critic", critic_response))

    print_thinking(JUDGE)
    judge_response = call_agent(
        format_judge_arguments(proposer_messages, critic_messages),
        JUDGE_SYSTEM_PROMPT,
    )
    print_verdict(JUDGE, judge_response)

    return proposer_response, critic_response, judge_response


if __name__ == "__main__":
    claim = prompt_claim()
    run_debate(claim)
