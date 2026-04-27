#!/usr/bin/env python3
"""Run OSS compliance scanners and enforce baseline release thresholds."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REPORT_LICENSE = ROOT / "docs" / "compliance" / "latest_license_audit.md"
REPORT_SECRET = ROOT / "docs" / "compliance" / "secret_scan_report.md"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=ROOT, check=True)


def extract_metric(path: Path, pattern: str, label: str) -> int:
    text = path.read_text(encoding="utf-8")
    match = re.search(pattern, text)
    if not match:
        raise RuntimeError(f"Could not find metric '{label}' in {path}")
    return int(match.group(1))


def main() -> int:
    print("Running compliance scanners...")
    run([sys.executable, "scripts/compliance/license_audit.py"])
    run([sys.executable, "scripts/compliance/repo_license_text_scan.py"])
    run([sys.executable, "scripts/compliance/secret_scan.py"])

    license_review_count = extract_metric(
        REPORT_LICENSE,
        r"Items requiring review: \*\*(\d+)\*\*",
        "items requiring review",
    )
    secret_hits = extract_metric(
        REPORT_SECRET,
        r"Total potential matches: \*\*(\d+)\*\*",
        "total potential matches",
    )

    print(f"License review-required items: {license_review_count}")
    print(f"Secret scan potential matches: {secret_hits}")

    failures: list[str] = []
    if license_review_count > 0:
        failures.append(f"license audit has {license_review_count} review-required item(s)")
    if secret_hits > 0:
        failures.append(f"secret scan has {secret_hits} potential match(es)")

    if failures:
        print("Compliance gate failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Compliance gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
