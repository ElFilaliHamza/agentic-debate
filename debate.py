from dotenv import load_dotenv
import os
from ollama import Client
from debate_system_prompts import (
    PROPOSER_SYSTEM_PROMPT,
    CRITIC_SYSTEM_PROMPT,
    JUDGE_SYSTEM_PROMPT,
)

load_dotenv()
MODEL = "glm-5.1:cloud"


client = Client(
    host=os.getenv("OLLAMA_HOST"),
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


ROUNDS = 3


def format_proposer_arguments(proposer_response: str) -> list[dict]:
    """Wrap the proposer's response as a user message for the critic."""
    if not proposer_response:
        return []
    return [{"role": "user", "content": "The proposer's arguments are: " + proposer_response}]


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


def run_debate(claim: str):
    proposer_messages = [{"role": "user", "content": claim}]
    critic_messages = []
    critic_response = ""
    proposer_response = ""
    
    print("Starting debate on the claim:", claim)
    for _round in range(ROUNDS):
        print(f"\n--- Round {_round + 1} ---")
        proposer_response = call_agent(
            proposer_messages + format_critic_arguments(critic_response),
            PROPOSER_SYSTEM_PROMPT,
        )
        print("Proposer's response:", proposer_response)
        proposer_messages.append({"role": "assistant", "content": proposer_response})

        critic_response = call_agent(
            critic_messages + format_proposer_arguments(proposer_response),
            CRITIC_SYSTEM_PROMPT,
        )
        print("Critic's response:", critic_response)
        critic_messages.append({"role": "assistant", "content": critic_response})
        print("Round completed.")

    print("\nDebate completed. Finalizing judge's verdict...")
    judge_response = call_agent(
        format_judge_arguments(proposer_messages, critic_messages),
        JUDGE_SYSTEM_PROMPT,
    )
    print("Judge's verdict:", judge_response)

    return proposer_response, critic_response, judge_response


if __name__ == "__main__":
    claim = input("Enter a factual claim to debate: ")
    print("The claim to debate is:", claim)
    print("Running debate...")
    proposer_response, critic_response, judge_response = run_debate(
        f"{claim}"
    )  # Add a period at the end of the claim)

    print("\nProposer's final response:\n", proposer_response)
    print("\nCritic's final response:\n", critic_response)
    print("\nJudge's final verdict:\n", judge_response)
