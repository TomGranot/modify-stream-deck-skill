#!/usr/bin/env python3
"""Build a background macOS app that opens a registered URL without taking focus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys


URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://[^\s'\"\\]+$")


class BuildError(RuntimeError):
    pass


def apple_script(url: str) -> str:
    return "\n".join(
        [
            "on run",
            f'    do shell script "/usr/bin/open -g -u \'{url}\'"',
            "end run",
            "",
        ]
    )


def validate_args(name: str, url: str, output_dir: Path) -> Path:
    if not name or name in {".", ".."} or any(character in name for character in "/\\\x00"):
        raise BuildError("--display-name must be a simple filename")
    if not URL_RE.fullmatch(url):
        raise BuildError("--url must be a registered URL without spaces or quotes")
    if output_dir.exists() and not output_dir.is_dir():
        raise BuildError("--output-dir must be a directory")
    return output_dir / f"{name}.app"


def build(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir).expanduser()
    target = validate_args(args.display_name, args.url, output_dir)
    script = apple_script(args.url)
    if args.dry_run:
        print(json.dumps({"app": str(target), "apple_script": script}, indent=2))
        return 0
    if sys.platform != "darwin":
        raise BuildError("Background protocol apps require macOS")
    if target.exists():
        raise BuildError(f"Refusing to overwrite existing app: {target}")
    output_dir.mkdir(parents=True, exist_ok=True)
    source = output_dir / f".{args.display_name}.applescript"
    try:
        source.write_text(script, encoding="utf-8")
        subprocess.run(["/usr/bin/osacompile", "-o", str(target), str(source)], check=True)
        subprocess.run(
            ["/usr/bin/plutil", "-insert", "LSUIElement", "-bool", "true", str(target / "Contents/Info.plist")],
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BuildError(f"Could not build {target.name}: {exc}") from exc
    finally:
        source.unlink(missing_ok=True)
    print(json.dumps({"app": str(target), "background": True, "url": args.url}, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--display-name", required=True, help="Name of the generated .app bundle")
    parser.add_argument("--url", required=True, help="Registered URL to open, such as app-name://start")
    parser.add_argument("--output-dir", required=True, help="Directory where the new .app bundle is created")
    parser.add_argument("--dry-run", action="store_true", help="Print the AppleScript without creating an app")
    return parser.parse_args()


def main() -> int:
    try:
        return build(parse_args())
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
