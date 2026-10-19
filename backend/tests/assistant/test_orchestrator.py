"""
backend/tests/assistant/test_orchestrator.py
--------------------------------------------
Integration and API tests for /assistant/config and /assistant/chat endpoints (§1217, §1254).
Tests answered, unsupported, degraded, and error flows with the scripted FakeLLMClient.
"""

import pytest
from fastapi.testclient import TestClient

from app.assistant.llm import FakeLLMClient
from app.assistant.orchestrator import AssistantOrchestrator
from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def fake_app():
    """Create test application wired with FakeLLMClient."""
    settings = Settings(
        LLM_PROVIDER="fake",
        AI_DAILY_REQUEST_CAP=300,
        LOG_AI_PROMPTS=False,
    )
    test_app = create_app(settings=settings)
    return test_app


@pytest.fixture
def client(fake_app):
    with TestClient(fake_app) as test_client:
        yield test_client


def test_get_assistant_config(client: TestClient) -> None:
    """GET /api/v1/assistant/config returns available=True, mode=llm, 6 suggested questions, and limits."""
    resp = client.get("/api/v1/assistant/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True
    assert data["mode"] == "llm"
    assert len(data["suggested_questions"]) == 6
    assert data["limits"]["max_question_chars"] == 500
    assert data["limits"]["max_history_turns"] == 6

    ids = [sq["id"] for sq in data["suggested_questions"]]
    assert "sq_overview" in ids
    assert "sq_top_category" in ids
    assert "sq_trends" in ids


def test_chat_answered_overview_question(client: TestClient) -> None:
    """POST /api/v1/assistant/chat successfully answers overview question with data_blocks and evidence."""
    payload = {
        "question": "What is the total number of complaints and the timely response rate?",
        "history": [],
    }
    resp = client.post("/api/v1/assistant/chat", json=payload)
    assert resp.status_code == 200
    assert resp.headers.get("Cache-Control") == "no-store"

    data = resp.json()
    assert data["status"] == "answered"
    assert "complaints" in data["answer_markdown"].lower()
    assert len(data["data_blocks"]) >= 1
    assert data["data_blocks"][0]["type"] == "kpi"
    assert len(data["evidence"]) >= 1
    assert data["evidence"][0]["tool"] == "get_dataset_overview"
    assert len(data["limitations"]) > 0
    assert data["grounding"]["checked"] is True
    assert data["grounding"]["fallback_used"] is False


def test_chat_answered_category_comparison(client: TestClient) -> None:
    """POST /api/v1/assistant/chat compares categories and returns structured table block."""
    payload = {
        "question": "Compare complaints across categories and tell me which has the highest volume",
        "history": [],
    }
    resp = client.post("/api/v1/assistant/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "answered"
    assert "Banking" in data["answer_markdown"]
    assert len(data["data_blocks"]) >= 1
    assert data["data_blocks"][0]["type"] == "table"


def test_chat_unsupported_question(client: TestClient) -> None:
    """POST /api/v1/assistant/chat returns status=unsupported when asked about individual companies."""
    payload = {
        "question": "How many complaints did Wells Fargo and Bank of America receive?",
        "history": [],
    }
    resp = client.post("/api/v1/assistant/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unsupported"
    assert "without specific company names" in data["answer_markdown"]
    assert len(data["data_blocks"]) == 0
    assert len(data["evidence"]) == 0


def test_chat_triggers_fallback_when_model_fabricates_numbers(fake_app) -> None:
    """When the LLM fabricates unsupported numbers, orchestrator replaces narrative with fallback renderer."""
    # Wire an orchestrator with a FakeLLMClient that injects fabricated numbers
    lying_client = FakeLLMClient(inject_fabricated_numbers=True)
    orchestrator = AssistantOrchestrator(
        settings=fake_app.state.settings,
        llm_client=lying_client,
    )

    from app.api.assistant import get_orchestrator

    fake_app.dependency_overrides[get_orchestrator] = lambda: orchestrator

    with TestClient(fake_app) as test_client:
        resp = test_client.post(
            "/api/v1/assistant/chat", json={"question": "What are the dataset KPIs?"}
        )
        assert resp.status_code == 200
        data = resp.json()

        # The fabricated number "999,999" must NOT appear in the user-facing answer!
        assert "999,999" not in data["answer_markdown"]
        assert data["grounding"]["fallback_used"] is True
        # The deterministic fallback must contain the real grounded numbers
        assert "complaints" in data["answer_markdown"].lower()

    fake_app.dependency_overrides.clear()


def test_chat_degraded_mode_suggested_question() -> None:
    """When LLM_PROVIDER=disabled, passing suggested_question_id returns status=degraded with verified data."""
    disabled_settings = Settings(LLM_PROVIDER="disabled")
    app_disabled = create_app(settings=disabled_settings)
    with TestClient(app_disabled) as test_client:
        config_resp = test_client.get("/api/v1/assistant/config")
        assert config_resp.json()["mode"] == "degraded"
        assert config_resp.json()["available"] is False

        payload = {
            "question": "What is the total number of complaints?",
            "suggested_question_id": "sq_overview",
        }
        resp = test_client.post("/api/v1/assistant/chat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert "[Degraded Mode Notice:" in data["answer_markdown"]
        assert len(data["data_blocks"]) == 1
        assert data["grounding"]["fallback_used"] is True


def test_chat_degraded_mode_free_text() -> None:
    """When LLM_PROVIDER=disabled, free-text questions return guidance without calling model."""
    disabled_settings = Settings(LLM_PROVIDER="disabled")
    app_disabled = create_app(settings=disabled_settings)
    with TestClient(app_disabled) as test_client:
        payload = {"question": "Can you summarize all complaints?"}
        resp = test_client.post("/api/v1/assistant/chat", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert "language model is currently disabled or unreachable" in data["answer_markdown"]
        assert len(data["data_blocks"]) == 0


def test_chat_validation_errors(client: TestClient) -> None:
    """Oversize questions and excessive history return 422."""
    # Oversize question (> 500 chars)
    oversize_payload = {"question": "a" * 501}
    resp1 = client.post("/api/v1/assistant/chat", json=oversize_payload)
    assert resp1.status_code == 422

    # Empty question
    empty_payload = {"question": ""}
    resp2 = client.post("/api/v1/assistant/chat", json=empty_payload)
    assert resp2.status_code == 422

    # Excess history (> 6 turns)
    excess_history = [
        {"role": "user" if i % 2 == 0 else "assistant", "content": f"msg {i}"} for i in range(7)
    ]
    resp3 = client.post(
        "/api/v1/assistant/chat", json={"question": "Hi", "history": excess_history}
    )
    assert resp3.status_code == 422
