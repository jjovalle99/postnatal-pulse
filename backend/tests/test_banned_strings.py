"""Static compliance check: clinician-facing strings must avoid diagnostic framing.

Spec references: PRD §7 (Guardrail row "Zero patient-facing copy uses 'diagnose',
'detect PPD', or 'replaces clinician'") and SPEC §3.4 BE-11 / BR-007.
"""

from pathlib import Path

import pytest


BANNED_SUBSTRINGS = (
    "diagnose",
    "diagnosing",
    "diagnoses",
    "detect postpartum",
    "detects postpartum",
    "detect ppd",
    "detects ppd",
    "replace clinician",
    "replaces clinician",
    "replacing clinician",
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
FRONTEND_SRC_ROOT = REPO_ROOT / "frontend" / "src"
FRONTEND_DIST_ROOT = REPO_ROOT / "frontend" / "dist"

# Per PRD guardrail row: exempt disclaimer surfaces where the banned word is
# used to say "this is NOT a diagnosis". The check is on affirmative claims.
ALLOWED_EXEMPTIONS = (
    "not a diagnosis",
    "does not replace clinical",
    "replace clinical judgment",
    "does not replace clinician",
    "this is not a diagnosis",
)


def _iter_candidate_files() -> list[Path]:
    files: list[Path] = []
    for root, suffixes in (
        (BACKEND_ROOT / "src", {".py"}),
        (BACKEND_ROOT / "templates", {".html", ".jinja", ".jinja2"}),
        (FRONTEND_SRC_ROOT, {".ts", ".tsx", ".css", ".html"}),
        (FRONTEND_DIST_ROOT, {".js", ".css", ".html"}),
    ):
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in suffixes:
                files.append(path)
    return files


def _line_is_exempt(line_lower: str) -> bool:
    return any(exemption in line_lower for exemption in ALLOWED_EXEMPTIONS)


@pytest.mark.parametrize("banned", BANNED_SUBSTRINGS)
def test_no_banned_substrings_in_clinician_surfaces(banned: str) -> None:
    offenders: list[tuple[Path, int, str]] = []
    for path in _iter_candidate_files():
        try:
            contents = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, raw_line in enumerate(contents.splitlines(), start=1):
            line_lower = raw_line.lower()
            if banned not in line_lower:
                continue
            if _line_is_exempt(line_lower):
                continue
            if path.name == "test_banned_strings.py":
                continue
            offenders.append((path, line_number, raw_line.strip()))

    assert offenders == [], (
        f"Banned substring '{banned}' appears in clinician-facing surfaces: "
        + "; ".join(f"{p}:{n} → {t}" for p, n, t in offenders[:5])
    )
