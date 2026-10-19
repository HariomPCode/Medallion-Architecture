"""
backend/tests/assistant/test_budget.py
--------------------------------------
Unit tests for AI budget tracker, daily caps, token counters, and day rollover (§1196).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from app.assistant.budget import BudgetExceededError, BudgetTracker, get_budget_tracker


def test_budget_tracker_increments_and_enforces_cap() -> None:
    """Ensure requests are tracked and BudgetExceededError is raised when cap is reached."""
    tracker = BudgetTracker(daily_cap=5)
    for i in range(1, 6):
        count = tracker.check_and_increment()
        assert count == i

    status = tracker.get_status()
    assert status["request_count"] == 5
    assert status["remaining_requests"] == 0

    with pytest.raises(BudgetExceededError) as exc_info:
        tracker.check_and_increment()

    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "AI_BUDGET_EXHAUSTED"
    assert "Daily AI assistant request limit (5) reached" in exc_info.value.message


def test_budget_tracker_day_rollover_resets_count() -> None:
    """Verify that crossing into a new UTC calendar day resets the request count."""
    current_time = datetime(2026, 10, 19, 23, 59, 0, tzinfo=timezone.utc)

    def mock_clock() -> datetime:
        return current_time

    tracker = BudgetTracker(daily_cap=2, clock=mock_clock)
    assert tracker.check_and_increment() == 1
    assert tracker.check_and_increment() == 2

    # Attempting a 3rd request today raises error
    with pytest.raises(BudgetExceededError):
        tracker.check_and_increment()

    # Advance time past midnight UTC
    current_time = datetime(2026, 10, 20, 0, 1, 0, tzinfo=timezone.utc)

    # Count must reset to 1
    assert tracker.check_and_increment() == 1
    status = tracker.get_status()
    assert status["day"] == "2026-10-20"
    assert status["request_count"] == 1
    assert status["remaining_requests"] == 1


def test_budget_token_accumulation() -> None:
    """Verify prompt and completion tokens accumulate correctly."""
    tracker = BudgetTracker(daily_cap=10)
    tracker.record_tokens(150, 50)
    tracker.record_tokens(200, 100)

    status = tracker.get_status()
    assert status["total_prompt_tokens"] == 350
    assert status["total_completion_tokens"] == 150
    assert status["total_tokens"] == 500


def test_budget_thread_safety() -> None:
    """Verify concurrent requests safely increment without race conditions."""
    tracker = BudgetTracker(daily_cap=100)

    def worker() -> None:
        for _ in range(10):
            tracker.check_and_increment()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker) for _ in range(5)]
        for f in futures:
            f.result()

    status = tracker.get_status()
    assert status["request_count"] == 50


def test_get_budget_tracker_singleton() -> None:
    """Verify global budget tracker singleton accessor."""
    tracker1 = get_budget_tracker(daily_cap=300)
    tracker2 = get_budget_tracker(daily_cap=300)
    assert tracker1 is tracker2
