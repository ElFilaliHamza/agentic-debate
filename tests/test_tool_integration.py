from public_debate.tools import SentimentTool, JokeTool
from public_debate.tools.registry import ToolRegistry


def test_registry_has_sentiment_tool():
    registry = ToolRegistry()
    assert "sentiment" in registry._tools


def test_registry_has_joke_tool():
    registry = ToolRegistry()
    assert "joke" in registry._tools


def test_registry_has_six_tools_total():
    registry = ToolRegistry()
    assert len(registry.get_all()) == 6


def test_sentiment_tool_schema_in_registry():
    registry = ToolRegistry()
    tool = registry.get("sentiment")
    schemas = registry.get_schemas([tool])
    assert schemas[0]["function"]["name"] == "sentiment"
    assert "text" in schemas[0]["function"]["parameters"]["properties"]


def test_joke_tool_schema_in_registry():
    registry = ToolRegistry()
    tool = registry.get("joke")
    schemas = registry.get_schemas([tool])
    assert schemas[0]["function"]["name"] == "joke"
    assert "topic" in schemas[0]["function"]["parameters"]["properties"]


def test_assign_random_includes_new_tools():
    registry = ToolRegistry()
    tools_a, tools_b = registry.assign_random()
    all_names = {t.name for t in tools_a} | {t.name for t in tools_b}
    assert "sentiment" in all_names
    assert "joke" in all_names