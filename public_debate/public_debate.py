from dotenv import load_dotenv
import os
from ollama import Client
from public_debate.helpers import enforce_limit, format_opponent_argument
from public_debate.public_debate_system_prompt import (
    SPEAKER_A_SYSTEM_PROMPT,
    SPEAKER_B_SYSTEM_PROMPT,
    JUDGE_SYSTEM_PROMPT,
)
from public_debate.tools import BaseTool
from public_debate.tools.registry import ToolRegistry
from tui_formatter.console import console
from tui_formatter.formatter import (
    print_speaker_label,
    print_thinking,
    print_tool_assignment,
    print_tool_result,
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


def stream_agent_with_tools(
    messages: list[dict],
    system_prompt: str = "",
    tools: list[BaseTool] = None,
    tool_schemas: list[dict] = None,
    role_style: str = "",
    registry: ToolRegistry = None,
) -> str:
    """Stream an agent's response character-by-character via Rich console."""
    tools = tools or []
    tool_schemas = tool_schemas or []
    registry = registry or ToolRegistry()

    all_messages = (
        [{"role": "system", "content": system_prompt}] + messages
        if system_prompt
        else messages
    )

    # 1. Initial non-streaming call to detect tool calls
    response = client.chat(
        model=MODEL,
        messages=all_messages,
        tools=tool_schemas or None,
    )

    # 2. No tool calls — stream the text for TUI effect
    if not response.message or not response.message.tool_calls:
        stream = client.chat(
            model=MODEL,
            messages=all_messages,
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

    # 3. Tool calls detected — execute them
    tool_results = []
    for tool_call in response.message.tool_calls:
        tool = registry.get(tool_call.function.name)

        result = tool.execute(**tool_call.function.arguments)
        print_tool_result(tool.name, result)
        tool_results.append(
            {
                "role": "tool",
                "name": tool_call.function.name,
                "content": result,
            }
        )

    # 4. Re-call with tool results, streaming the final argument
    all_messages.append(
        {
            "role": "assistant",
            "content": response.message.content or "",
            "tool_calls": [
                {
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.message.tool_calls
            ],
        }
    )

    all_messages.extend(tool_results)

    final_stream = client.chat(
        model=MODEL,
        messages=all_messages,
        stream=True,
    )
    full_response = ""
    for chunk in final_stream:
        if chunk.message and chunk.message.content:
            text = chunk.message.content
            console.print(text, end="", style=role_style, highlight=False)
            full_response += text
    console.print()
    return full_response


def call_agent(
    messages: list[dict],
    system_prompt: str = "",
    tools: list[BaseTool] = None,
    tool_schemas: list[dict] = None,
    registry: ToolRegistry = None,
) -> str:
    """Call an agent without streaming (returns full response at once)."""
    tools = tools or []
    tool_schemas = tool_schemas or []
    registry = registry or ToolRegistry()

    all_messages = (
        [{"role": "system", "content": system_prompt}] + messages
        if system_prompt
        else messages
    )
    response = client.chat(
        model=MODEL,
        messages=all_messages,
        tools=tool_schemas or None,
    )

    if response.message and response.message.tool_calls:
        tool_results = []

        for tool_call in response.message.tool_calls:
            tool = registry.get(tool_call.function.name)
            result = tool.execute(**tool_call.function.arguments)
            print_tool_result(tool.name, result)
            tool_results.append(
                {
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": result,
                }
            )
        all_messages.append(
            {
                "role": "assistant",
                "content": response.message.content or "",
                "tool_calls": [
                    {
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in response.message.tool_calls
                ],
            }
        )
        all_messages.extend(tool_results)

        final_response = client.chat(
            model=MODEL,
            messages=all_messages,
        )

        return final_response.message.content if final_response.message else ""

    return response.message.content if response.message else ""


def run_debate(
    motion: str,
    max_rounds: int = ROUNDS,
    max_chars: int = MAX_CHARS,
) -> list[tuple[str, str]]:
    registry = ToolRegistry()
    tools_a, tools_b = registry.assign_random()
    schemas_a = registry.get_schemas(tools_a)
    schemas_b = registry.get_schemas(tools_b)

    # Display tool assignments
    print_tool_assignment(SPEAKER_A, tools_a)
    print_tool_assignment(SPEAKER_B, tools_b)
    console.print()

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
        a_response = stream_agent_with_tools(
            (
                speaker_a_msgs + format_opponent_argument("Speaker B", last_b_response)
                if round_num > 0
                else speaker_a_msgs
            ),
            SPEAKER_A_SYSTEM_PROMPT.format(motion=motion, MAX_CHARS=max_chars),
            tools=tools_a,
            tool_schemas=schemas_a,
            role_style=SPEAKER_A.text_style,
            registry=registry,
        )
        a_response = enforce_limit(a_response, max_chars)
        speaker_a_msgs.append({"role": "assistant", "content": a_response})
        transcript.append(("Speaker A", a_response))

        print_speaker_label(SPEAKER_B)
        b_response = stream_agent_with_tools(
            (
                speaker_b_msgs + format_opponent_argument("Speaker A", a_response)
                if round_num > 0
                else speaker_b_msgs
            ),
            SPEAKER_B_SYSTEM_PROMPT.format(motion=motion, MAX_CHARS=max_chars),
            tools=tools_b,
            tool_schemas=schemas_b,
            role_style=SPEAKER_B.text_style,
            registry=registry,
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
    registry = ToolRegistry()
    judge_tools = registry.judge_tools()
    judge_schemas = registry.get_schemas(judge_tools)

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
        tools=judge_tools,
        tool_schemas=judge_schemas,
        registry=registry,
    )
    verdict = enforce_limit(verdict, max_chars)

    print_verdict(JUDGE, verdict)

    return verdict


if __name__ == "__main__":
    motion = prompt_motion()
    transcript = run_debate(motion)
    judge_debate(transcript, motion)
