"""
backend/app/assistant/budget.py
-------------------------------
In-memory UTC-day budget tracker and token usage accumulator for AI requests.
Enforces AI_DAILY_REQUEST_CAP per worker instance (§14.6, §22).
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Callable, Optional

from app.core.errors import AppError


class BudgetExceededError(AppError):
    """Raised when the daily AI request quota has been exhausted."""

    def __init__(
        self, message: str = "Daily AI assistant request limit reached. Please try again tomorrow."
    ):
        super().__init__(message=message, status_code=429, code="AI_BUDGET_EXHAUSTED")


class BudgetTracker:
    """Thread-safe in-memory budget and token accumulator."""

    def __init__(
        self,
        daily_cap: int = 300,
        clock: Optional[Callable[[], datetime]] = None,
    ) -> None:
        self.daily_cap = daily_cap
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()

        # State
        self._current_day: str = self._get_today_str()
        self._request_count: int = 0
        self._prompt_tokens: int = 0
        self._completion_tokens: int = 0

    def _get_today_str(self) -> str:
        return self._clock().strftime("%Y-%m-%d")

    def _maybe_rollover_locked(self) -> None:
        today = self._get_today_str()
        if today != self._current_day:
            self._current_day = today
            self._request_count = 0
            # Token counts are cumulative across the worker lifespan,
            # but daily request cap resets each day.

    def check_and_increment(self) -> int:
        """
        Atomically check whether the daily request cap is exceeded and increment count.
        Returns the current request count for today.
        Raises BudgetExceededError if the daily cap has been reached.
        """
        with self._lock:
            self._maybe_rollover_locked()
            if self._request_count >= self.daily_cap:
                raise BudgetExceededError(
                    f"Daily AI assistant request limit ({self.daily_cap}) reached for {self._current_day}. "
                    "Quota resets at 00:00 UTC."
                )
            self._request_count += 1
            return self._request_count

    def record_tokens(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Record token consumption for logging and metrics."""
        with self._lock:
            self._prompt_tokens += max(0, prompt_tokens)
            self._completion_tokens += max(0, completion_tokens)

    def get_status(self) -> dict[str, int | str]:
        """Return a snapshot of current budget state."""
        with self._lock:
            self._maybe_rollover_locked()
            return {
                "day": self._current_day,
                "request_count": self._request_count,
                "daily_cap": self.daily_cap,
                "remaining_requests": max(0, self.daily_cap - self._request_count),
                "total_prompt_tokens": self._prompt_tokens,
                "total_completion_tokens": self._completion_tokens,
                "total_tokens": self._prompt_tokens + self._completion_tokens,
            }

    def reset_for_tests(self, daily_cap: Optional[int] = None) -> None:
        """Reset state for deterministic unit testing."""
        with self._lock:
            if daily_cap is not None:
                self.daily_cap = daily_cap
            self._current_day = self._get_today_str()
            self._request_count = 0
            self._prompt_tokens = 0
            self._completion_tokens = 0


# Global singleton per worker
_GLOBAL_BUDGET: Optional[BudgetTracker] = None
_BUDGET_LOCK = threading.Lock()


def get_budget_tracker(daily_cap: int = 300) -> BudgetTracker:
    """Retrieve or initialize the global budget tracker."""
    global _GLOBAL_BUDGET
    with _BUDGET_LOCK:
        if _GLOBAL_BUDGET is None:
            _GLOBAL_BUDGET = BudgetTracker(daily_cap=daily_cap)
        elif _GLOBAL_BUDGET.daily_cap != daily_cap:
            _GLOBAL_BUDGET.daily_cap = daily_cap
        return _GLOBAL_BUDGET
