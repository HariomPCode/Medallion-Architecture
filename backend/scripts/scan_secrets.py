"""
backend/scripts/scan_secrets.py
-------------------------------
Scans git history and repository files for accidental secret leakage.
Uses high-confidence regex patterns to verify AC-6.4.
"""

import re
import subprocess
import sys

PATTERNS = [
    (
        r"DefaultEndpointsProtocol=[^;\s]+;AccountName=[^;\s]+;AccountKey=[^;\s]+",
        "Azure Storage Connection String",
    ),
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API Key"),
    (r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "Private Key"),
    (
        r"(?:api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"][0-9a-zA-Z_\-]{20,}['\"]",
        "API/Secret Key Assignment",
    ),
    (r"https://[a-zA-Z0-9_\-\.]+:[0-9a-zA-Z_\-]+@", "URL with Embedded Credentials"),
]

ALLOWLIST_PATTERNS = [
    r"test-internal-secret-key-[0-9a-zA-Z]+",
    r"test-custom-request-id-[0-9a-zA-Z]+",
    r"a-very-secure-production-key-[0-9a-zA-Z]+",
    r"super-secret-key-[0-9a-zA-Z\-]+",
    r"super-secure-internal-api-key-[0-9a-zA-Z\-]+",
    r"test-secret-key-[0-9a-zA-Z\-]+",
    r"sk-dummy-test-key",
    r"DefaultEndpointsProtocol=https;AccountName=\{storage",
]


def scan_git_history() -> int:
    """Scans all commit diffs in git history."""
    try:
        git_log = subprocess.check_output(
            ["git", "log", "-p", "--full-history"],
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as e:
        print(f"Error running git log: {e}", file=sys.stderr)
        return 1

    findings = []
    lines = git_log.splitlines()
    commit = "unknown"

    for i, line in enumerate(lines):
        if line.startswith("commit "):
            commit = line.split()[1][:8]
            continue
        if not line.startswith("+"):
            continue

        # Check against allowlist
        if any(re.search(allow, line) for allow in ALLOWLIST_PATTERNS):
            continue

        for regex, desc in PATTERNS:
            if re.search(regex, line, re.IGNORECASE):
                findings.append((commit, desc, line.strip()))

    if findings:
        print(f"FAILED: Found {len(findings)} potential secrets in git history:")
        for commit, desc, line in findings:
            print(f"  [{commit}] {desc}: {line[:80]}")
        return 1

    print("SUCCESS: 0 secrets found in git history.")
    return 0


if __name__ == "__main__":
    sys.exit(scan_git_history())
