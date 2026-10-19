#!/usr/bin/env python3
"""
backend/scripts/run_ai_eval.py
------------------------------
Evaluation harness executing the 26 curated questions in tests/assistant/eval_questions.yaml (§1246).
Runs against FakeLLMClient (default; offline; in CI) or optionally live Azure OpenAI with --live.
Verifies tool routing, status accuracy, and 100% numeric grounding compliance.
"""

import argparse
import asyncio
import os
import sys
import time

import yaml

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.assistant.budget import get_budget_tracker  # noqa: E402
from app.assistant.llm import AzureOpenAIClient, FakeLLMClient  # noqa: E402
from app.assistant.orchestrator import AssistantOrchestrator  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.schemas.assistant import AssistantChatRequest  # noqa: E402


async def run_evaluation(live: bool = False, verbose: bool = False) -> int:
    print("=" * 75)
    print("FINANCE COMPLAINTS MEDALLION — AI ASSISTANT EVALUATION HARNESS")
    print("=" * 75)

    eval_yaml_path = os.path.join(BACKEND_DIR, "tests", "assistant", "eval_questions.yaml")
    if not os.path.exists(eval_yaml_path):
        print(f"Error: Evaluation file not found at {eval_yaml_path}")
        return 1

    with open(eval_yaml_path, "r", encoding="utf-8") as f:
        eval_data = yaml.safe_load(f)

    questions = eval_data.get("questions", [])
    print(f"Loaded {len(questions)} evaluation questions from {eval_yaml_path}")

    # Load data snapshot with local_snapshot data mode
    local_dir = "backend/.local_data" if os.path.exists("backend/.local_data") else ".local_data"
    base_settings = Settings(
        DATA_MODE="local_snapshot",
        LOCAL_DATA_DIR=local_dir,
        LLM_PROVIDER="azure_openai" if live else "fake",
        AI_DAILY_REQUEST_CAP=1000,
    )

    from app.data.snapshot import SnapshotManager, set_snapshot_manager

    manager = SnapshotManager(base_settings)
    set_snapshot_manager(manager)
    print(f"Loading local snapshot from {local_dir} into memory...")
    await manager.startup_load()
    snapshot = manager.current_snapshot
    if snapshot is None:
        print("Error: Could not load data snapshot.")
        return 1

    # Configure client and orchestrator
    if live:
        if not base_settings.LLM_ENDPOINT or not (
            base_settings.LLM_API_KEY or base_settings.LLM_AUTH_MODE == "entra"
        ):
            print("\n[BLOCKED_EXTERNAL: live-llm-verification]")
            print("Live evaluation requires LLM_ENDPOINT and LLM_API_KEY or Entra ID credentials.")
            print("To run live verification:")
            print("  1. Set LLM_PROVIDER=azure_openai")
            print("  2. Set LLM_ENDPOINT=https://<your-instance>.openai.azure.com/")
            print("  3. Set LLM_DEPLOYMENT=<deployment-name>")
            print("  4. Set LLM_API_KEY=<key>")
            print("  5. Re-run: python scripts/run_ai_eval.py --live")
            return 2
        print(
            f"Running evaluation against live Azure OpenAI deployment: {base_settings.LLM_DEPLOYMENT}"
        )
        client = AzureOpenAIClient(settings=base_settings)
        settings = base_settings
    else:
        print("Running evaluation against deterministic FakeLLMClient (offline mode)")
        settings = base_settings
        client = FakeLLMClient()

    budget_tracker = get_budget_tracker(daily_cap=1000)
    budget_tracker.reset_for_tests(daily_cap=1000)
    orchestrator = AssistantOrchestrator(
        settings=settings, llm_client=client, budget_tracker=budget_tracker
    )

    passed_count = 0
    grounding_passed = 0
    tool_routing_passed = 0
    failures = []

    print("\nExecuting evaluation queries...\n")
    start_total_time = time.monotonic()

    for idx, item in enumerate(questions, 1):
        qid = item["id"]
        group = item["group"]
        q_text = item["question"]
        exp_status = item["expected_status"]
        exp_tool = item.get("expected_tool")

        req = AssistantChatRequest(question=q_text, history=[])
        t0 = time.monotonic()
        try:
            resp = await orchestrator.handle_chat(
                request=req, snapshot=snapshot, request_id=f"eval-{qid}"
            )
            duration_ms = (time.monotonic() - t0) * 1000
        except Exception as exc:
            failures.append((qid, q_text, f"Exception raised: {exc}"))
            print(f"  [{idx:02d}/26] [FAIL] {qid} ({group}): Exception: {exc}")
            continue

        # Check status
        status_ok = resp.status == exp_status

        # Check tool routing
        tools_called = [e.tool for e in resp.evidence]
        if exp_tool is None:
            tool_ok = len(tools_called) == 0
        else:
            tool_ok = exp_tool in tools_called

        if tool_ok:
            tool_routing_passed += 1

        # Check numeric grounding
        # Must have zero ungrounded numbers
        g_ok = (resp.grounding.checked is True) and (resp.grounding.ungrounded_numbers == 0)
        if g_ok:
            grounding_passed += 1

        all_ok = status_ok and tool_ok and g_ok
        if all_ok:
            passed_count += 1
            print(
                f"  [{idx:02d}/26] [PASS] {qid} ({group}) — {duration_ms:.1f}ms — status={resp.status}"
            )
        else:
            reasons = []
            if not status_ok:
                reasons.append(f"status {resp.status} != {exp_status}")
            if not tool_ok:
                reasons.append(f"tools {tools_called} != expected {exp_tool}")
            if not g_ok:
                reasons.append(f"grounding ungrounded={resp.grounding.ungrounded_numbers}")
            err_msg = ", ".join(reasons)
            failures.append((qid, q_text, err_msg))
            print(f"  [{idx:02d}/26] [FAIL] {qid} ({group}) — {err_msg}")

        if verbose:
            print(f"       Answer: {resp.answer_markdown[:100]}...")

    total_duration = time.monotonic() - start_total_time
    total_q = len(questions)
    pass_rate = (passed_count / total_q) * 100.0
    grounding_rate = (grounding_passed / total_q) * 100.0
    routing_rate = (tool_routing_passed / total_q) * 100.0

    budget_status = budget_tracker.get_status()

    print("\n" + "=" * 75)
    print("AI ASSISTANT EVALUATION SUMMARY")
    print("=" * 75)
    print(f"Total Questions Evaluated  : {total_q}")
    print(f"Overall Passed             : {passed_count}/{total_q} ({pass_rate:.1f}%)")
    print(f"Tool Selection Accuracy    : {tool_routing_passed}/{total_q} ({routing_rate:.1f}%)")
    print(
        f"Numeric Grounding Rate     : {grounding_passed}/{total_q} ({grounding_rate:.1f}%) [TARGET: 100%]"
    )
    print(f"Total Evaluation Duration  : {total_duration:.2f}s")
    print(f"Total Prompt Tokens        : {budget_status['total_prompt_tokens']}")
    print(f"Total Completion Tokens    : {budget_status['total_completion_tokens']}")
    print("=" * 75)

    if failures:
        print("\nFailures:")
        for fid, fq, freason in failures:
            print(f"  - {fid}: {fq} -> {freason}")
        return 1

    print("\nALL EVALUATION CRITERIA PASSED: 100% TOOL ROUTING AND 100% GROUNDED NUMBERS")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI Assistant Evaluation Suite")
    parser.add_argument(
        "--live", action="store_true", help="Run against live Azure OpenAI (requires credentials)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print verbose response snippets"
    )
    args = parser.parse_args()

    exit_code = asyncio.run(run_evaluation(live=args.live, verbose=args.verbose))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
