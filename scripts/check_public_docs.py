"""Check local links in the public entry points without network access."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
ENTRY_FILES = [
    *ROOT.glob("README*.md"),
    *ROOT.glob("documentation/*.md"),
    *ROOT.glob("examples/classical-conditioning/*.md"),
    *[ROOT / p for p in (
        "CONTRIBUTING.md", "SECURITY.md", "THIRD_PARTY_NOTICES.md",
        "docs/usage.md", "docs/usage.zh-CN.md", "docs/api.md", "docs/skills.md",
        "docs/roadmap.md", "docs/release-validation.md",
    )],
]


def main() -> int:
    errors: list[str] = []
    checked = 0
    for file in ENTRY_FILES:
        if not file.exists():
            errors.append(f"Missing document: {file.relative_to(ROOT)}")
            continue
        for match in re.finditer(r"\]\(([^)]+)\)", file.read_text(encoding="utf-8")):
            target = match.group(1).split("#", 1)[0].strip("<>")
            if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            checked += 1
            if not (file.parent / unquote(target)).exists():
                errors.append(f"{file.relative_to(ROOT)}: missing {target}")
    for error in errors:
        print(error)
    print(f"Checked {checked} local links across {len(ENTRY_FILES)} documents; {len(errors)} errors.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
