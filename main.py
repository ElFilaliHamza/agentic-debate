from dotenv import load_dotenv
import math
import os
import sys
from ollama import Client

load_dotenv()
MODEL = "nemotron-3-super:cloud"


client = Client(
    host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    headers=(
        {"Authorization": f"Bearer {os.getenv('OLLAMA_API_KEY', '')}"}
        if os.getenv("OLLAMA_API_KEY")
        else None
    ),
)


def calculate(expression: str) -> str:
    """
    Calculate the result of a mathematical expression.

    Args:
        expression (str): The mathematical expression to evaluate.

    Returns:
        str: The result of the evaluation as a string.
    """
    allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}

    allowed_names["__builtins__"] = {}

    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a mathematical expression. Use Python syntax, e.g., '2 + 2', 'sqrt(16)'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The mathematical expression to evaluate.",
                    }
                },
                "required": ["expression"],
            },
        },
    }
]

TOOL_MAP = {"calculate": calculate}

MAX_TURNS = 5


def run_agent(user_query: str) -> str:

    messages = [{"role": "user", "content": user_query}]

    for turn in range(MAX_TURNS):

        response = client.chat(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )
        # If the model provides a direct text answer (no tool calls), stop.
        if response.message.content:
            print("\nFinal answer:", response.message.content)
            return

        if response.message.tool_calls:
            messages.append(
                {
                    "role": "assistant",
                    "content": response.message.content,
                    "tool_calls": response.message.tool_calls,
                }
            )

            for tool_call in response.message.tool_calls:
                print(f"\nReceived tool call: {tool_call}")
                print(f"\nTool call: {tool_call.function.name} with arguments: {tool_call.function.arguments}")
                fn_name = tool_call["function"]["name"]
                fn_args = tool_call["function"]["arguments"]

                # Execute the tool function and get the result
                print(f"\nExecuting tool: {fn_name} with arguments: {fn_args}")

                fn = TOOL_MAP.get(fn_name)

                result = fn(**fn_args)

                messages.append(
                    {
                        "role": "tool",
                        "content": result,
                    }
                )
        else:
            # No content and no tool calls – model stopped unexpectedly
            print("Agent stopped without a final answer.")
            return

    print("Agent reached maximum turns without finishing.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = input("Your question: ")
    run_agent(query)
