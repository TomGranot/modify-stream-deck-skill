#!/usr/bin/env python3
"""Fail CI when public files contain common live-profile or credential artifacts."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", "__pycache__"}
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".py", ".txt", ".svg", ""}
PATTERNS = {
    "credential assignment": re.compile(r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*['\"][^'\"]{8,}"),
    "Stream Deck device serial": re.compile(r"@\(\d+\)\[[^\]]+\]"),
    "absolute user path": re.compile(r"/(Users|home)/[A-Za-z0-9._-]+/"),
    "live profile UUID path": re.compile(r"ProfilesV3/[0-9A-Fa-f-]{30,}\.sdProfile"),
}


def main() -> int:
    findings = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(ROOT)}:{line}: {label}")
    if findings:
        print("Privacy scan failed:", file=sys.stderr)
        print("\n".join(findings), file=sys.stderr)
        return 1
    print("Privacy scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
