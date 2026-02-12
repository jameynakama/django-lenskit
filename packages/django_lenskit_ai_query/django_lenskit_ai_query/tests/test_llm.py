from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest
from django.test import override_settings

from django_lenskit_ai_query.llm import (
    LlmNotConfigured,
    _ai_cfg,
    _available_model_labels,
    _build_system_prompt,
    _extract_json,
    _schema_from_settings,
    generate_dsl_from_nl,
    is_configured,
)


def test_ai_cfg_returns_ai_query_config() -> None:
    """Should return ai_query config from settings."""
    with override_settings(ADMIN_LENSKIT={"ai_query": {"allowed_models": ["auth.User"]}}):
        cfg = _ai_cfg()
        assert cfg == {"allowed_models": ["auth.User"]}


def test_ai_cfg_returns_empty_when_not_dict() -> None:
    """Should return empty dict when config is not a dict."""
    with override_settings(ADMIN_LENSKIT=None):
        cfg = _ai_cfg()
        assert cfg == {}

    with override_settings(ADMIN_LENSKIT="string"):
        cfg = _ai_cfg()
        assert cfg == {}


def test_ai_cfg_returns_empty_when_ai_query_not_dict() -> None:
    """Should return empty dict when ai_query is not a dict."""
    with override_settings(ADMIN_LENSKIT={"ai_query": "string"}):
        cfg = _ai_cfg()
        assert cfg == {}


def test_available_model_labels_filters_by_allowed_models() -> None:
    """Should filter models by allowed_models setting."""
    with override_settings(ADMIN_LENSKIT={"ai_query": {"allowed_models": ["contenttypes.ContentType"]}}):
        labels = _available_model_labels()
        # ContentType should be available in any Django test setup
        assert "contenttypes.ContentType" in labels
        # auth.User not in allowed_models, so it should be filtered out
        assert "auth.User" not in labels


def test_available_model_labels_includes_all_when_wildcard() -> None:
    """Should include all models when allowed_models contains wildcard."""
    with override_settings(ADMIN_LENSKIT={"ai_query": {"allowed_models": ["*"]}}):
        labels = _available_model_labels()
        assert len(labels) > 0


def test_available_model_labels_limits_to_200() -> None:
    """Should limit results to 200 models."""
    labels = _available_model_labels()
    assert len(labels) <= 200


def test_is_configured_checks_openai_api_key(monkeypatch) -> None:
    """Should check for OPENAI_API_KEY env var."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    assert is_configured() is True

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert is_configured() is False


def test_build_system_prompt_includes_available_models() -> None:
    """Should include available models in system prompt."""
    with override_settings(ADMIN_LENSKIT={"ai_query": {"allowed_models": ["contenttypes.ContentType"]}}):
        schema = json.dumps({"allowed_models": ["contenttypes.ContentType"]})
        prompt = _build_system_prompt(schema)
        assert "contenttypes.ContentType" in prompt
        assert "model" in prompt
        assert "fields" in prompt


def test_schema_from_settings_includes_model_fields() -> None:
    """Should include model fields in schema."""
    with override_settings(ADMIN_LENSKIT={"ai_query": {"allowed_models": ["contenttypes.ContentType"]}}):
        schema = _schema_from_settings()
        parsed = json.loads(schema)
        assert "model_fields" in parsed
        assert "available_models" in parsed
        assert "contenttypes.ContentType" in parsed["available_models"]


def test_schema_from_settings_handles_wildcard() -> None:
    """Should handle wildcard in allowed_models."""
    with override_settings(ADMIN_LENSKIT={"ai_query": {"allowed_models": "*"}}):
        schema = _schema_from_settings()
        parsed = json.loads(schema)
        assert parsed["allowed_models"] == ["*"]


def test_extract_json_from_plain_json() -> None:
    """Should extract JSON from plain JSON string."""
    json_str = '{"model": "ai_test.Book", "limit": 10}'
    result = _extract_json(json_str)
    assert result == {"model": "ai_test.Book", "limit": 10}


def test_extract_json_from_fenced_code() -> None:
    """Should extract JSON from code fences."""
    fenced = '```json\n{"model": "ai_test.Book", "limit": 10}\n```'
    result = _extract_json(fenced)
    assert result == {"model": "ai_test.Book", "limit": 10}


def test_extract_json_with_surrounding_text() -> None:
    """Should extract JSON from text with surrounding content."""
    text = 'Here is the result: {"model": "ai_test.Book", "limit": 10} and done.'
    result = _extract_json(text)
    assert result == {"model": "ai_test.Book", "limit": 10}


def test_generate_dsl_from_nl_raises_when_not_configured(monkeypatch) -> None:
    """Should raise LlmNotConfigured when OPENAI_API_KEY not set."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LlmNotConfigured, match="OPENAI_API_KEY not set"):
        generate_dsl_from_nl("show me all books")


def test_generate_dsl_from_nl_raises_when_openai_not_available(monkeypatch) -> None:
    """Should raise LlmNotConfigured when openai module not available."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with patch("importlib.import_module", side_effect=ImportError("No module named openai")):
        with pytest.raises(LlmNotConfigured, match="OpenAI client not available"):
            generate_dsl_from_nl("show me all books")


def test_generate_dsl_from_nl_calls_openai_api(monkeypatch) -> None:
    """Should call OpenAI API with correct parameters."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Mock OpenAI client
    mock_choice = Mock()
    mock_choice.message.content = '{"model": "contenttypes.ContentType", "fields": ["id"], "limit": 10}'
    mock_response = Mock()
    mock_response.choices = [mock_choice]

    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_response

    mock_openai_class = Mock(return_value=mock_client)

    with patch("importlib.import_module") as mock_import:
        mock_module = Mock()
        mock_module.OpenAI = mock_openai_class
        mock_import.return_value = mock_module

        with override_settings(
            ADMIN_LENSKIT={"ai_query": {"allowed_models": ["contenttypes.ContentType"], "openai_model": "gpt-4"}}
        ):
            result = generate_dsl_from_nl("show me all content types")

    assert result["model"] == "contenttypes.ContentType"
    assert result["limit"] == 10
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4"
    assert call_kwargs["temperature"] == 0.2
    assert call_kwargs["max_tokens"] == 600


def test_generate_dsl_from_nl_uses_default_model(monkeypatch) -> None:
    """Should use default model when not specified in settings."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    mock_choice = Mock()
    mock_choice.message.content = '{"model": "contenttypes.ContentType", "limit": 10}'
    mock_response = Mock()
    mock_response.choices = [mock_choice]

    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_response

    mock_openai_class = Mock(return_value=mock_client)

    with patch("importlib.import_module") as mock_import:
        mock_module = Mock()
        mock_module.OpenAI = mock_openai_class
        mock_import.return_value = mock_module

        with override_settings(ADMIN_LENSKIT={"ai_query": {"allowed_models": ["contenttypes.ContentType"]}}):
            generate_dsl_from_nl("show me all content types")

    call_kwargs = mock_client.chat.completions.create.call_args[1]
    assert call_kwargs["model"] == "gpt-4-1106-preview"


def test_generate_dsl_from_nl_handles_empty_content(monkeypatch) -> None:
    """Should handle empty content from OpenAI response."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    mock_choice = Mock()
    mock_choice.message.content = None
    mock_response = Mock()
    mock_response.choices = [mock_choice]

    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_response

    mock_openai_class = Mock(return_value=mock_client)

    with patch("importlib.import_module") as mock_import:
        mock_module = Mock()
        mock_module.OpenAI = mock_openai_class
        mock_import.return_value = mock_module

        with override_settings(ADMIN_LENSKIT={"ai_query": {"allowed_models": ["contenttypes.ContentType"]}}):
            with pytest.raises(json.JSONDecodeError):
                generate_dsl_from_nl("show me all content types")
