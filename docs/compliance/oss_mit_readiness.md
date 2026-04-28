# OSS MIT readiness policy

This project targets **MIT licensing** for source distribution and downstream use.

## Goals

- Keep repository-owned code under MIT.
- Prevent accidental introduction of copyleft obligations through dependencies or vendored assets.
- Keep a repeatable audit trail for every release.

## Mandatory checks before release

1. Ensure `LICENSE` remains MIT and present at the repository root.
2. Run:
   - `python scripts/compliance/compliance_gate.py`
   - (optional) `python scripts/compliance/license_audit.py`
   - (optional) `python scripts/compliance/repo_license_text_scan.py`
   - (optional) `python scripts/compliance/secret_scan.py`
3. Review `docs/compliance/latest_license_audit.md` and resolve every flagged item.
4. Review `docs/compliance/repo_license_text_scan.md`; investigate any hits outside compliance/docs folders.
5. Review `docs/compliance/secret_scan_report.md`; remove or rotate any confirmed credential material before release.
6. Keep `docs/compliance/python_dependency_licenses.json` updated with evidence URLs for Python dependencies when network metadata is unavailable.
7. Keep `docs/compliance/first_party_dependency_licenses.json` updated for git-sourced first-party dependencies.
8. Keep `.github/workflows/oss-compliance.yml` required on protected branches.
9. Do not merge if any dependency is confirmed GPL/AGPL/LGPL/EPL/CDDL/MPL-2.0+ without explicit legal approval.

## First-party git dependency handling

- Git-sourced requirements are allowed only when either:
  - a first-party mapping exists in `docs/compliance/first_party_dependency_licenses.json`, or
  - the upstream repository license is confirmed directly (for example, through the GitHub license API).
- Every first-party mapping must include evidence URL(s) to the upstream license file.

## Operating model

- Treat the generated report as an engineering gate, not legal advice.
- If uncertain, pin a specific commit and capture license evidence in documentation.
- Prefer permissive dependencies (MIT/BSD/Apache-2.0/ISC/PSF) for long-term interoperability.
