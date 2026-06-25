from unittest.mock import patch, MagicMock
from public_debate.tools.sentiment import SentimentTool, EMOTION_MAPPING


def test_sentiment_name():
    tool = SentimentTool()
    assert tool.name == "sentiment"


def test_sentiment_description():
    tool = SentimentTool()
    assert "emotional tone" in tool.description.lower()


def test_sentiment_parameters_schema():
    tool = SentimentTool()
    params = tool.parameters
    assert params["type"] == "object"
    assert "text" in params["properties"]
    assert params["required"] == ["text"]


def test_emotion_mapping_covers_key_categories():
    """Verify the mapping includes the main debate-relevant labels."""
    assert "angry" in EMOTION_MAPPING.values()
    assert "confident" in EMOTION_MAPPING.values()
    assert "defensive" in EMOTION_MAPPING.values()
    assert "desperate" in EMOTION_MAPPING.values()


def test_sentiment_execute_with_pipeline():
    tool = SentimentTool()
    # Mock the pipeline to return a known emotion
    mock_pipeline_result = [[
        {"label": "optimism", "score": 0.72},
        {"label": "neutral", "score": 0.15},
        {"label": "fear", "score": 0.08},
    ]]

    mock_pipeline = MagicMock(return_value=mock_pipeline_result)
    tool._pipeline = mock_pipeline

    result = tool.execute(text="I'm absolutely certain we're right about this!")
    assert "confident" in result.lower() or "optimism" in result.lower()
    assert "72" in result  # confidence percentage
    mock_pipeline.assert_called_once()


def test_sentiment_execute_pipeline_failure_falls_back():
    tool = SentimentTool()

    # Make _load_pipeline raise an exception
    with patch.object(tool, "_load_pipeline", side_effect=OSError("Model not found")):
        result = tool.execute(text="I am absolutely certain this is terrible and wrong!")

    # Should fall back to keyword heuristic
    assert isinstance(result, str)
    assert len(result) > 0


def test_sentiment_fallback_heuristic_confident():
    tool = SentimentTool()
    with patch.object(tool, "_load_pipeline", side_effect=OSError("No model")):
        result = tool.execute(text="This is clearly and absolutely the right path forward.")
    assert "confident" in result.lower()


def test_sentiment_fallback_heuristic_defensive():
    tool = SentimentTool()
    with patch.object(tool, "_load_pipeline", side_effect=OSError("No model")):
        result = tool.execute(text="Maybe perhaps it could possibly be considered.")
    assert "defensive" in result.lower()


def test_sentiment_fallback_heuristic_angry():
    tool = SentimentTool()
    with patch.object(tool, "_load_pipeline", side_effect=OSError("No model")):
        result = tool.execute(text="I hate this furious attack, it's awful and terrible!")
    assert "angry" in result.lower()


def test_sentiment_pipeline_lazy_loaded():
    """Pipeline should not exist until first execute call."""
    tool = SentimentTool()
    assert tool._pipeline is None


def test_sentiment_pipeline_cached_after_first_load():
    """Pipeline should be reused after first creation — _load_pipeline called only once."""
    tool = SentimentTool()
    mock_pipeline_result = [[
        {"label": "neutral", "score": 0.9},
    ]]
    mock_pipeline_instance = MagicMock(return_value=mock_pipeline_result)

    # Mock _load_pipeline to return our mock and track calls
    original_load = tool._load_pipeline
    load_calls = 0

    def mock_load():
        nonlocal load_calls
        load_calls += 1
        tool._pipeline = mock_pipeline_instance
        return mock_pipeline_instance

    with patch.object(tool, "_load_pipeline", side_effect=mock_load):
        tool.execute(text="test one")
        tool.execute(text="test two")

    # _load_pipeline called only once, but pipeline called twice
    assert load_calls == 1
    assert mock_pipeline_instance.call_count == 2