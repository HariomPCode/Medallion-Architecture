"""
backend/tests/assistant/test_llm.py
-----------------------------------
Unit tests for LLM abstraction, DisabledLLMClient, FakeLLMClient,
and AzureOpenAIClient failure handling (§1196).
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.assistant.llm import (
    AzureOpenAIClient,
    DisabledLLMClient,
    FakeLLMClient,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
    get_llm_client,
)
from app.core.config import Settings


@pytest.mark.anyio
async def test_disabled_llm_client_raises_unavailable() -> None:
    """DisabledLLMClient must raise LLMUnavailableError with 503."""
    client = DisabledLLMClient()
    with pytest.raises(LLMUnavailableError) as exc_info:
        await client.chat(messages=[{"role": "user", "content": "Hello"}])

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "LLM_UNAVAILABLE"


@pytest.mark.anyio
async def test_fake_llm_client_routing_and_unsupported() -> None:
    """FakeLLMClient routes keywords to appropriate tools and handles unsupported queries."""
    client = FakeLLMClient()

    # T2 Routing
    resp_cat = await client.chat(
        messages=[{"role": "user", "content": "Compare complaints across categories"}]
    )
    assert len(resp_cat.tool_calls) == 1
    assert resp_cat.tool_calls[0].name == "compare_categories"

    # T3 Routing
    resp_trend = await client.chat(
        messages=[{"role": "user", "content": "Show me yearly trends over time"}]
    )
    assert len(resp_trend.tool_calls) == 1
    assert resp_trend.tool_calls[0].name == "get_trend"

    # T4 Routing
    resp_bd = await client.chat(
        messages=[{"role": "user", "content": "Breakdown by submission channel"}]
    )
    assert len(resp_bd.tool_calls) == 1
    assert resp_bd.tool_calls[0].name == "get_breakdown"

    # T6 Routing
    resp_dq = await client.chat(
        messages=[{"role": "user", "content": "What is the data quality health score?"}]
    )
    assert len(resp_dq.tool_calls) == 1
    assert resp_dq.tool_calls[0].name == "get_quality_summary"

    # T7 Routing
    resp_anom = await client.chat(
        messages=[{"role": "user", "content": "List flagged anomaly records"}]
    )
    assert len(resp_anom.tool_calls) == 1
    assert resp_anom.tool_calls[0].name == "list_anomalies"

    # T8 Routing
    resp_explain = await client.chat(
        messages=[{"role": "user", "content": "Explain how M-03 timely rate is defined"}]
    )
    assert len(resp_explain.tool_calls) == 1
    assert resp_explain.tool_calls[0].name == "explain_metric"

    # Unsupported query: specific company name
    resp_unsupported = await client.chat(
        messages=[{"role": "user", "content": "How many complaints did Wells Fargo receive?"}]
    )
    assert resp_unsupported.content is not None
    assert resp_unsupported.content.startswith("UNSUPPORTED:")
    assert len(resp_unsupported.tool_calls) == 0


@pytest.mark.anyio
async def test_fake_llm_client_synthesis() -> None:
    """FakeLLMClient generates grounded narrative from tool result envelope."""
    client = FakeLLMClient()
    tool_envelope = {
        "tool": "get_dataset_overview",
        "result": {
            "total_complaints": 62516,
            "timely": {"rate": 96.06, "rate_denominator": 61022},
            "in_progress_count": 1494,
        },
    }
    messages = [
        {"role": "user", "content": "Dataset overview?"},
        {"role": "assistant", "content": None, "tool_calls": []},
        {"role": "tool", "content": json.dumps(tool_envelope)},
    ]
    resp = await client.chat(messages=messages)
    assert resp.content is not None
    assert "62,516" in resp.content
    assert "96.06%" in resp.content
    assert "61,022" in resp.content
    assert "1,494" in resp.content


@pytest.mark.anyio
async def test_fake_llm_client_failure_injections() -> None:
    """Verify FakeLLMClient failure injection flags."""
    # Timeout
    client_timeout = FakeLLMClient(inject_timeout=True)
    with pytest.raises(LLMTimeoutError):
        await client_timeout.chat(messages=[{"role": "user", "content": "Hi"}])

    # 429 Rate Limit
    client_429 = FakeLLMClient(inject_429=True)
    with pytest.raises(LLMRateLimitError):
        await client_429.chat(messages=[{"role": "user", "content": "Hi"}])

    # 500 Server Error
    client_err = FakeLLMClient(inject_server_error=True)
    with pytest.raises(LLMUnavailableError):
        await client_err.chat(messages=[{"role": "user", "content": "Hi"}])

    # Fabricated numbers
    client_fab = FakeLLMClient(inject_fabricated_numbers=True)
    envelope = {"tool": "get_dataset_overview", "result": {"total_complaints": 62516}}
    resp = await client_fab.chat(
        messages=[
            {"role": "user", "content": "Hi"},
            {"role": "tool", "content": json.dumps(envelope)},
        ]
    )
    assert "999,999" in (resp.content or "")


def test_get_llm_client_factory() -> None:
    """Verify get_llm_client instantiates correct client based on settings."""
    settings_disabled = Settings(LLM_PROVIDER="disabled")
    assert isinstance(get_llm_client(settings_disabled), DisabledLLMClient)

    settings_fake = Settings(LLM_PROVIDER="fake")
    assert isinstance(get_llm_client(settings_fake), FakeLLMClient)

    settings_azure = Settings(
        LLM_PROVIDER="azure_openai",
        LLM_ENDPOINT="https://test-foundry.openai.azure.com",
        LLM_DEPLOYMENT="gpt-4o-mini",
        LLM_API_KEY="test-secret-key-12345",
    )
    azure_client = get_llm_client(settings_azure)
    assert isinstance(azure_client, AzureOpenAIClient)


@pytest.mark.anyio
async def test_azure_openai_client_sanitized_errors_and_retries() -> None:
    """Verify AzureOpenAIClient maps errors without leaking keys or endpoints."""
    fake_key = "sk-super-secret-key-that-must-never-leak"
    settings = Settings(
        LLM_PROVIDER="azure_openai",
        LLM_ENDPOINT="https://test.openai.azure.com",
        LLM_DEPLOYMENT="test-deployment",
        LLM_API_KEY=fake_key,
    )
    client = AzureOpenAIClient(settings=settings)

    # Mock AsyncAzureOpenAI to raise APIConnectionError
    mock_inner_client = MagicMock()
    mock_create = AsyncMock(side_effect=Exception(f"Connection failed to {fake_key}"))
    mock_inner_client.chat.completions.create = mock_create
    client._client = mock_inner_client

    with pytest.raises(LLMUnavailableError) as exc_info:
        await client.chat(messages=[{"role": "user", "content": "Hello"}])

    error_str = str(exc_info.value.message)
    # Assert secret key is NOT present in user-facing message
    assert fake_key not in error_str
    assert "Unexpected error communicating with AI service." in error_str
