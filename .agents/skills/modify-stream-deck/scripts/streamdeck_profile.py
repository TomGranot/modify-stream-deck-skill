#!/usr/bin/env python3
"""Inspect and safely patch Elgato Stream Deck V3 page manifests."""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import struct
import sys
import time
import uuid
import xml.etree.ElementTree as ET


DEFAULT_ROOT = Path.home() / "Library/Application Support/com.elgato.StreamDeck/ProfilesV3"
COORDINATE_RE = re.compile(r"^\d+,\d+$")
EMPTY_KEY = {
    "KeyCmd": False,
    "KeyCtrl": False,
    "KeyModifiers": 0,
    "KeyOption": False,
    "KeyShift": False,
    "NativeCode": -1,
    "QTKeyCode": 33554431,
    "VKeyCode": -1,
}
KEYS = {
    "return": (36, 16777220, 36),
    "space": (49, 32, 49),
    "tab": (48, 16777217, 48),
    "escape": (53, 16777216, 53),
}
MODIFIER_BITS = {"option": 1, "ctrl": 2, "shift": 4, "cmd": 8}


class ProfileError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError(f"Cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ProfileError(f"Expected a JSON object in {path}")
    return value


def find_profile_bundle(manifest: Path) -> Path:
    for parent in (manifest, *manifest.parents):
        if parent.name.endswith(".sdProfile"):
            return parent
    raise ProfileError(f"{manifest} is not inside an .sdProfile bundle")


def action_summary(action: dict) -> dict:
    settings = action.get("Settings") or {}
    return {
        "name": action.get("Name", ""),
        "uuid": action.get("UUID", ""),
        "text": settings.get("pastedText", ""),
        "routine_steps": len(settings.get("Routine") or []),
        "alternate_steps": len(settings.get("RoutineAlt") or []),
    }


def keypad_actions(manifest_data: dict) -> dict:
    controllers = manifest_data.get("Controllers")
    if not isinstance(controllers, list):
        raise ProfileError("Page manifest has no Controllers array")
    for controller in controllers:
        if controller.get("Type") == "Keypad" and isinstance(controller.get("Actions"), dict):
            return controller["Actions"]
    raise ProfileError("Page manifest has no Keypad Actions object")


def discover(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise ProfileError(f"Profile root does not exist: {root}")
    bundles = []
    for bundle in sorted(root.glob("*.sdProfile")):
        root_manifest = bundle / "manifest.json"
        if not root_manifest.is_file():
            continue
        root_data = load_json(root_manifest)
        pages = []
        for manifest in sorted((bundle / "Profiles").glob("*/manifest.json")):
            try:
                actions = keypad_actions(load_json(manifest))
            except ProfileError:
                continue
            pages.append(
                {
                    "id": manifest.parent.name,
                    "manifest": str(manifest),
                    "buttons": {key: action_summary(value) for key, value in sorted(actions.items())},
                }
            )
        bundles.append(
            {
                "bundle": str(bundle),
                "name": root_data.get("Name", ""),
                "current_page": (root_data.get("Pages") or {}).get("Current", root_data.get("CurrentPage", "")),
                "pages": pages,
            }
        )
    print(json.dumps({"profiles": bundles}, indent=2, ensure_ascii=False))
    return 0


def inspect_manifest(args: argparse.Namespace) -> int:
    manifest = Path(args.manifest).expanduser().resolve()
    actions = keypad_actions(load_json(manifest))
    output = {key: action_summary(value) for key, value in sorted(actions.items())}
    print(json.dumps({"manifest": str(manifest), "buttons": output}, indent=2, ensure_ascii=False))
    return 0


def state(icon: str | None) -> dict:
    return {"Image": icon} if icon else {}


def action_shell(name: str, action_uuid: str, settings: dict, states: list[dict]) -> dict:
    return {
        "ActionID": str(uuid.uuid4()),
        "LinkedTitle": True,
        "Name": name,
        "Resources": None,
        "Settings": settings,
        "State": 0,
        "States": states,
        "UUID": action_uuid,
    }


def nested(name: str, action_uuid: str, settings: dict) -> dict:
    return {
        "Name": name,
        "OverrideState": -1,
        "Settings": settings,
        "State": 0,
        "States": [{}],
        "UUID": action_uuid,
    }


def hotkey_settings(key: str, modifiers: list[str] | None = None) -> dict:
    normalized_key = key.lower()
    if normalized_key not in KEYS:
        raise ProfileError(f"Unsupported hotkey {key!r}; choose one of {', '.join(KEYS)}")
    normalized_modifiers = [item.lower() for item in (modifiers or [])]
    unknown = sorted(set(normalized_modifiers) - set(MODIFIER_BITS))
    if unknown:
        raise ProfileError(f"Unsupported modifiers: {', '.join(unknown)}")
    native, qt, virtual = KEYS[normalized_key]
    first = {
        "KeyCmd": "cmd" in normalized_modifiers,
        "KeyCtrl": "ctrl" in normalized_modifiers,
        "KeyModifiers": sum(MODIFIER_BITS[item] for item in set(normalized_modifiers)),
        "KeyOption": "option" in normalized_modifiers,
        "KeyShift": "shift" in normalized_modifiers,
        "NativeCode": native,
        "QTKeyCode": qt,
        "VKeyCode": virtual,
    }
    return {"Coalesce": True, "Hotkeys": [first, copy.deepcopy(EMPTY_KEY), copy.deepcopy(EMPTY_KEY), copy.deepcopy(EMPTY_KEY)]}


def build_step(item: dict) -> dict:
    if not isinstance(item, dict):
        raise ProfileError("Every sequence step must be an object")
    kind = item.get("type")
    if kind == "text":
        text = item.get("text")
        if not isinstance(text, str):
            raise ProfileError("text action requires a string 'text'")
        return nested("Text", "com.elgato.streamdeck.system.text", {"isSendingEnter": False, "pastedText": text})
    if kind == "hotkey":
        return nested("Hotkey", "com.elgato.streamdeck.system.hotkey", hotkey_settings(item.get("key", ""), item.get("modifiers")))
    if kind == "url":
        url = item.get("url")
        if not isinstance(url, str) or not url:
            raise ProfileError("url action requires a non-empty string 'url'")
        return nested("Website", "com.elgato.streamdeck.system.website", {"openInBrowser": True, "path": url})
    if kind == "open":
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise ProfileError("open action requires a non-empty string 'path'")
        return nested("Open", "com.elgato.streamdeck.system.open", {"openInBrowser": True, "path": path})
    raise ProfileError(f"Unsupported sequence step type: {kind!r}")


def image_dimensions(path: Path, data: bytes) -> tuple[int, int]:
    suffix = path.suffix.lower()
    if suffix == ".png" and data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if suffix == ".gif" and data[:6] in {b"GIF87a", b"GIF89a"} and len(data) >= 10:
        return struct.unpack("<HH", data[6:10])
    if suffix == ".svg":
        try:
            root = ET.fromstring(data.decode("utf-8"))
        except (UnicodeDecodeError, ET.ParseError) as exc:
            raise ProfileError(f"Cannot parse SVG icon {path}: {exc}") from exc
        def number(value: str | None) -> int | None:
            if value is None:
                return None
            match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(?:px)?\s*", value)
            return round(float(match.group(1))) if match else None
        width, height = number(root.get("width")), number(root.get("height"))
        if width is not None and height is not None:
            return width, height
        view_box = root.get("viewBox")
        if view_box:
            values = view_box.replace(",", " ").split()
            if len(values) == 4:
                return round(float(values[2])), round(float(values[3]))
    raise ProfileError(f"Cannot determine icon dimensions: {path}")


def copy_icon(icon_value: str | None, spec_path: Path, images_dir: Path, dry_run: bool) -> str | None:
    if icon_value is None:
        return None
    source = (spec_path.parent / icon_value).resolve()
    if not source.is_file():
        raise ProfileError(f"Icon does not exist: {source}")
    suffix = source.suffix.lower()
    if suffix not in {".png", ".svg", ".gif"}:
        raise ProfileError(f"Unsupported icon format: {source.suffix}")
    data = source.read_bytes()
    dimensions = image_dimensions(source, data)
    if dimensions != (144, 144):
        raise ProfileError(f"Icon must be 144 x 144, got {dimensions[0]} x {dimensions[1]}: {source}")
    digest = hashlib.sha256(data).hexdigest()[:16].upper()
    destination_name = f"AGENT_{digest}{suffix}"
    if not dry_run:
        images_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, images_dir / destination_name)
    return f"Images/{destination_name}"


def build_button(item: dict, spec_path: Path, images_dir: Path, dry_run: bool) -> dict | None:
    kind = item.get("type")
    if kind == "remove":
        return None
    icon = copy_icon(item.get("icon"), spec_path, images_dir, dry_run)
    if kind == "text":
        text = item.get("text")
        if not isinstance(text, str):
            raise ProfileError("text action requires a string 'text'")
        return action_shell("Text", "com.elgato.streamdeck.system.text", {"isSendingEnter": False, "pastedText": text}, [state(icon)])
    if kind == "submit_text":
        text = item.get("text")
        if not isinstance(text, str):
            raise ProfileError("submit_text requires a string 'text'")
        routine = [build_step({"type": "text", "text": text}), build_step({"type": "hotkey", "key": "return"})]
        return action_shell("Multi Action", "com.elgato.streamdeck.multiactions.routine", {"Routine": routine, "RoutineAlt": []}, [state(icon)])
    if kind == "hotkey":
        return action_shell("Hotkey", "com.elgato.streamdeck.system.hotkey", hotkey_settings(item.get("key", ""), item.get("modifiers")), [state(icon)])
    if kind == "url":
        url = item.get("url")
        if not isinstance(url, str) or not url:
            raise ProfileError("url action requires a non-empty string 'url'")
        return action_shell("Website", "com.elgato.streamdeck.system.website", {"openInBrowser": True, "path": url}, [state(icon)])
    if kind == "open":
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise ProfileError("open action requires a non-empty string 'path'")
        return action_shell("Open", "com.elgato.streamdeck.system.open", {"openInBrowser": True, "path": path}, [state(icon)])
    if kind == "sequence":
        actions = item.get("actions")
        if not isinstance(actions, list) or not actions:
            raise ProfileError("sequence requires a non-empty 'actions' array")
        return action_shell("Multi Action", "com.elgato.streamdeck.multiactions.routine", {"Routine": [build_step(step) for step in actions], "RoutineAlt": []}, [state(icon)])
    if kind == "toggle_sequence":
        on_actions = item.get("on")
        off_actions = item.get("off")
        if not isinstance(on_actions, list) or not on_actions or not isinstance(off_actions, list) or not off_actions:
            raise ProfileError("toggle_sequence requires non-empty 'on' and 'off' arrays")
        off_icon = copy_icon(item.get("off_icon"), spec_path, images_dir, dry_run)
        return action_shell(
            "Multi Action Switch",
            "com.elgato.streamdeck.multiactions.routine2",
            {"Routine": [build_step(step) for step in on_actions], "RoutineAlt": [build_step(step) for step in off_actions]},
            [state(icon), state(off_icon)],
        )
    raise ProfileError(f"Unsupported button type: {kind!r}")


def make_backup(bundle: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    destination = backup_dir / f"{bundle.stem}-before-agent-edit-{timestamp}.sdProfile"
    counter = 1
    while destination.exists():
        destination = backup_dir / f"{bundle.stem}-before-agent-edit-{timestamp}-{counter}.sdProfile"
        counter += 1
    shutil.copytree(bundle, destination)
    return destination


def stop_stream_deck() -> None:
    subprocess.run(["pkill", "-TERM", "-x", "Stream Deck"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start_stream_deck() -> None:
    for _ in range(10):
        result = subprocess.run(["pgrep", "-x", "Stream Deck"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            return
        time.sleep(0.25)
    subprocess.run(["open", "-a", "Elgato Stream Deck"], check=False)


def atomic_write(path: Path, data: dict, restart_app: bool) -> None:
    temporary = path.with_name(f"{path.name}.agent-new")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, separators=(",", ":"), ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
    load_json(temporary)
    if restart_app:
        stop_stream_deck()
    os.replace(temporary, path)
    if restart_app:
        start_stream_deck()


def apply_spec(args: argparse.Namespace) -> int:
    manifest = Path(args.manifest).expanduser().resolve()
    spec_path = Path(args.spec).expanduser().resolve()
    data = load_json(manifest)
    spec = load_json(spec_path)
    buttons = spec.get("buttons")
    if not isinstance(buttons, dict) or not buttons:
        raise ProfileError("Spec requires a non-empty 'buttons' object")
    for coordinate, item in buttons.items():
        if not COORDINATE_RE.fullmatch(coordinate):
            raise ProfileError(f"Invalid coordinate {coordinate!r}; expected column,row")
        if not isinstance(item, dict):
            raise ProfileError(f"Button {coordinate} must be an object")
    actions = keypad_actions(data)
    before = {key: action_summary(value) for key, value in sorted(actions.items())}
    images_dir = manifest.parent / "Images"
    for coordinate, item in buttons.items():
        built = build_button(item, spec_path, images_dir, True)
        if built is None:
            actions.pop(coordinate, None)
        else:
            actions[coordinate] = built
    after = {key: action_summary(value) for key, value in sorted(actions.items())}
    changed = sorted(buttons)
    untouched_changed = [key for key in set(before) | set(after) if key not in buttons and before.get(key) != after.get(key)]
    if untouched_changed:
        raise ProfileError(f"Refusing edit because untouched coordinates changed: {', '.join(untouched_changed)}")
    output = {"manifest": str(manifest), "changed_coordinates": changed, "before": before, "after": after}
    if args.dry_run:
        output["dry_run"] = True
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    bundle = find_profile_bundle(manifest)
    backup_dir = Path(args.backup_dir).expanduser().resolve()
    backup = make_backup(bundle, backup_dir)
    try:
        for item in buttons.values():
            copy_icon(item.get("icon"), spec_path, images_dir, False)
            copy_icon(item.get("off_icon"), spec_path, images_dir, False)
        atomic_write(manifest, data, args.restart_app)
    except Exception:
        if manifest.exists():
            shutil.copy2(backup / manifest.relative_to(bundle), manifest)
        raise
    output["backup"] = str(backup)
    output["dry_run"] = False
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="List profile bundles, pages, and button summaries")
    discover_parser.add_argument("--root", default=str(DEFAULT_ROOT))
    discover_parser.set_defaults(func=discover)

    inspect_parser = subparsers.add_parser("inspect", help="Summarize one page manifest")
    inspect_parser.add_argument("--manifest", required=True)
    inspect_parser.set_defaults(func=inspect_manifest)

    apply_parser = subparsers.add_parser("apply", help="Apply a declarative button spec")
    apply_parser.add_argument("--manifest", required=True)
    apply_parser.add_argument("--spec", required=True)
    apply_parser.add_argument("--backup-dir", default=str(Path.home() / "Documents/Stream Deck Backups"))
    apply_parser.add_argument("--dry-run", action="store_true")
    apply_parser.add_argument("--restart-app", action="store_true")
    apply_parser.set_defaults(func=apply_spec)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except ProfileError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    sys.exit(main())
