import json
import urllib.request
from unittest.mock import patch, MagicMock
from public_debate.tools.joke import JokeTool


def test_joke_name():
    tool = JokeTool()
    assert tool.name == "joke"


def test_joke_description():
    tool = JokeTool()
    assert "joke" in tool.description.lower()


def test_joke_parameters_schema():
    tool = JokeTool()
    params = tool.parameters
    assert params["type"] == "object"
    assert "topic" in params["properties"]
    assert params["required"] == ["topic"]


def test_joke_execute_with_results():
    tool = JokeTool()
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({
        "results": [
            {"joke": "Why do mathematicians hate the outdoors? Too many natural logs."}
        ]
    }).encode()
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("public_debate.tools.joke.urllib.request.urlopen", return_value=mock_response):
        result = tool.execute(topic="math")
    assert "natural logs" in result


def test_joke_execute_no_results_falls_back_to_random():
    tool = JokeTool()
    call_count = 0

    def mock_urlopen(req, timeout=0):
        nonlocal call_count
        call_count += 1
        mock_resp = MagicMock()
        # req may be a Request object or a string; check for "search" in the URL
        url_str = req.full_url if isinstance(req, urllib.request.Request) else str(req)
        if "search" in url_str:
            # No results for search
            mock_resp.read.return_value = json.dumps({"results": []}).encode()
        else:
            # Random joke fallback
            mock_resp.read.return_value = json.dumps({
                "joke": "I told my opponent a chemistry joke. No reaction."
            }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    with patch("public_debate.tools.joke.urllib.request.urlopen", side_effect=mock_urlopen):
        result = tool.execute(topic="xyzzy_nonexistent_topic")
    assert call_count == 2  # search then random
    assert "chemistry" in result


def test_joke_execute_network_error_returns_fallback():
    tool = JokeTool()
    with patch(
        "public_debate.tools.joke.urllib.request.urlopen",
        side_effect=urllib.error.URLError("Network error"),
    ):
        result = tool.execute(topic="anything")
    # Should return one of the hardcoded fallback jokes
    assert len(result) > 0
    assert isinstance(result, str)
    assert result in JokeTool.FALLBACK_JOKES