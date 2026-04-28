#!/usr/bin/env python3
"""Generate a lightweight OSS license audit report for this repository.

The script inspects:
1) Frontend npm lockfile package license metadata.
2) Backend requirements with curated license mappings and PyPI fallback metadata.
3) Git-based Python dependencies via a first-party allowlist and GitHub license API.

The report is written to docs/compliance/latest_license_audit.md.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
FRONT_LOCKFILE = ROOT / "AccessAppFront" / "package-lock.json"
BACK_REQS = ROOT / "AccessBackEnd" / "requirements.txt"
OUT_REPORT = ROOT / "docs" / "compliance" / "latest_license_audit.md"
FIRST_PARTY_LICENSES = ROOT / "docs" / "compliance" / "first_party_dependency_licenses.json"
PYTHON_LICENSES = ROOT / "docs" / "compliance" / "python_dependency_licenses.json"

COPYLEFT_PATTERNS = (
    "gpl",
    "agpl",
    "lgpl",
    "epl",
    "cddl",
    "mpl-2.0",
)


@dataclass
class Finding:
    ecosystem: str
    package: str
    version: str
    license_value: str
    status: str
    notes: str = ""


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def classify_license(license_value: str) -> str:
    norm = normalize(license_value)
    if not norm or norm == "unknown":
        return "unknown"
    if any(pattern in norm for pattern in COPYLEFT_PATTERNS):
        return "copyleft-review"
    return "permissive-or-other"


def load_first_party_licenses() -> dict[str, dict[str, str]]:
    if not FIRST_PARTY_LICENSES.exists():
        return {}
    payload = json.loads(FIRST_PARTY_LICENSES.read_text(encoding="utf-8"))
    dependencies = payload.get("dependencies", [])
    by_requirement: dict[str, dict[str, str]] = {}
    for dependency in dependencies:
        requirement = dependency.get("requirement")
        if isinstance(requirement, str) and requirement.strip():
            by_requirement[requirement.strip()] = dependency
    return by_requirement


def load_python_licenses() -> dict[str, dict[str, str]]:
    if not PYTHON_LICENSES.exists():
        return {}
    payload = json.loads(PYTHON_LICENSES.read_text(encoding="utf-8"))
    dependencies = payload.get("dependencies", [])
    by_name: dict[str, dict[str, str]] = {}
    for dependency in dependencies:
        name = dependency.get("name")
        if isinstance(name, str) and name.strip():
            by_name[name.strip().lower()] = dependency
    return by_name


def parse_npm_findings() -> list[Finding]:
    payload = json.loads(FRONT_LOCKFILE.read_text(encoding="utf-8"))
    packages = payload.get("packages", {})
    findings: list[Finding] = []

    for package_path, meta in sorted(packages.items()):
        if not package_path:
            continue

        package_name = package_path.replace("node_modules/", "", 1)
        version = str(meta.get("version", "unknown"))
        license_value = str(meta.get("license", "UNKNOWN"))
        status = classify_license(license_value)
        findings.append(
            Finding(
                ecosystem="npm",
                package=package_name,
                version=version,
                license_value=license_value,
                status=status,
            )
        )

    return findings


def parse_requirement_name(raw_line: str) -> str | None:
    line = raw_line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("git+"):
        return None

    splitters = ["==", ">=", "<=", "~=", "!=", ">", "<"]
    name = line
    for splitter in splitters:
        if splitter in line:
            name = line.split(splitter, 1)[0]
            break

    name = name.strip()
    name = name.split("[", 1)[0]
    return name or None


def fetch_json(url: str, headers: dict[str, str] | None = None) -> dict | None:
    request_headers = {"User-Agent": "Accessibility-AI-License-Audit"}
    if headers:
        request_headers.update(headers)
    request = urllib.request.Request(url, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def fetch_pypi_license(name: str) -> tuple[str, str]:
    url = f"https://pypi.org/pypi/{urllib.parse.quote(name)}/json"
    payload = fetch_json(url)
    if not payload:
        return "UNKNOWN", "PyPI lookup failed"

    info = payload.get("info", {})
    classifiers: Iterable[str] = info.get("classifiers") or []
    license_field = (info.get("license") or "").strip()

    license_from_classifier = ""
    for classifier in classifiers:
        if classifier.startswith("License ::"):
            license_from_classifier = classifier
            break

    if license_from_classifier:
        return license_from_classifier, "from PyPI classifier"
    if license_field:
        return license_field, "from PyPI license field"
    return "UNKNOWN", "No PyPI license metadata"


def parse_github_repo_from_git_requirement(requirement_line: str) -> tuple[str, str] | None:
    pattern = r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.#]+)(?:\.git)?"
    match = re.search(pattern, requirement_line)
    if not match:
        return None
    owner = match.group("owner")
    repo = match.group("repo")
    return owner, repo


def fetch_github_license_spdx(owner: str, repo: str) -> tuple[str, str]:
    payload = fetch_json(
        f"https://api.github.com/repos/{owner}/{repo}/license",
        headers={"Accept": "application/vnd.github+json"},
    )
    if not payload:
        return "UNKNOWN", "GitHub license API lookup failed"

    license_blob = payload.get("license") or {}
    spdx = license_blob.get("spdx_id") or "UNKNOWN"
    html_url = payload.get("html_url") or f"https://github.com/{owner}/{repo}/blob/HEAD/LICENSE"
    return str(spdx), f"from GitHub API ({html_url})"


def build_git_requirement_finding(requirement: str, first_party_map: dict[str, dict[str, str]]) -> Finding:
    mapped = first_party_map.get(requirement)
    if mapped:
        license_value = str(mapped.get("license", "UNKNOWN"))
        status = classify_license(license_value)
        evidence = mapped.get("evidence", "first-party mapping")
        return Finding(
            ecosystem="pip",
            package=requirement,
            version="n/a",
            license_value=license_value,
            status=status,
            notes=f"first-party mapping ({evidence})",
        )

    repo = parse_github_repo_from_git_requirement(requirement)
    if repo:
        owner, name = repo
        license_value, note = fetch_github_license_spdx(owner, name)
        status = classify_license(license_value)
        return Finding(
            ecosystem="pip",
            package=requirement,
            version="n/a",
            license_value=license_value,
            status=status,
            notes=note,
        )

    return Finding(
        ecosystem="pip",
        package=requirement,
        version="n/a",
        license_value="UNKNOWN",
        status="manual-review",
        notes="Git dependency not in first-party mapping and could not infer repository metadata.",
    )


def parse_python_findings() -> list[Finding]:
    findings: list[Finding] = []
    raw_lines = BACK_REQS.read_text(encoding="utf-8").splitlines()
    first_party_map = load_first_party_licenses()
    python_license_map = load_python_licenses()

    for raw_line in raw_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("git+"):
            findings.append(build_git_requirement_finding(stripped, first_party_map))
            continue

        req_name = parse_requirement_name(stripped)
        if not req_name:
            continue

        curated = python_license_map.get(req_name.lower())
        if curated:
            license_value = str(curated.get("license", "UNKNOWN"))
            evidence = str(curated.get("evidence", "no evidence URL"))
            note = f"from curated mapping ({evidence})"
        else:
            license_value, note = fetch_pypi_license(req_name)

        status = classify_license(license_value)
        findings.append(
            Finding(
                ecosystem="pip",
                package=req_name,
                version="specifier in requirements.txt",
                license_value=license_value,
                status=status,
                notes=note,
            )
        )

    return findings


def build_report(npm_findings: list[Finding], py_findings: list[Finding]) -> str:
    all_findings = npm_findings + py_findings
    flagged = [f for f in all_findings if f.status in {"copyleft-review", "manual-review", "unknown"}]

    lines = [
        "# Latest license audit",
        "",
        "This report is generated by `scripts/compliance/license_audit.py`.",
        "",
        "## Summary",
        f"- npm dependencies scanned: **{len(npm_findings)}**",
        f"- Python dependencies scanned: **{len(py_findings)}**",
        f"- Items requiring review: **{len(flagged)}**",
        "",
        "## Review-required items",
        "",
    ]

    if not flagged:
        lines.append("No dependencies matched the copyleft/manual-review heuristics.")
    else:
        lines.append("| Ecosystem | Package | License metadata | Status | Notes |")
        lines.append("|---|---|---|---|---|")
        for finding in flagged:
            lines.append(
                f"| {finding.ecosystem} | `{finding.package}` | `{finding.license_value}` | {finding.status} | {finding.notes or '-'} |"
            )

    lines.extend(
        [
            "",
            "## Notes",
            "- Heuristic flags are conservative and require human verification.",
            "- Absence of a flag is not legal advice.",
            "- Keep this report current before every tagged release.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    npm_findings = parse_npm_findings()
    py_findings = parse_python_findings()
    report = build_report(npm_findings, py_findings)
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(report + "\n", encoding="utf-8")
    print(f"wrote {OUT_REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
