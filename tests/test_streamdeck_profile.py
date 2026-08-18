import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / ".agents/skills/modify-stream-deck/scripts/streamdeck_profile.py"


class StreamDeckProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bundle = self.root / "ProfilesV3/DEMO.sdProfile"
        self.page = self.bundle / "Profiles/PAGE"
        self.page.mkdir(parents=True)
        (self.bundle / "manifest.json").write_text(
            json.dumps(
                {
                    "Name": "Demo",
                    "Pages": {"Current": "PAGE", "Default": "PAGE", "Pages": ["PAGE"]},
                    "Version": "3.0",
                }
            ),
            encoding="utf-8",
        )
        self.original_action = {
            "ActionID": "keep-me",
            "LinkedTitle": True,
            "Name": "Next Page",
            "Resources": None,
            "Settings": {},
            "State": 0,
            "States": [{}],
            "UUID": "com.elgato.streamdeck.page.next",
        }
        self.manifest = self.page / "manifest.json"
        self.manifest.write_text(
            json.dumps(
                {
                    "Controllers": [
                        {"Type": "Keypad", "Actions": {"2,1": self.original_action}}
                    ],
                    "Icon": "",
                    "Name": "",
                }
            ),
            encoding="utf-8",
        )
        self.icon = self.root / "yes.svg"
        self.icon.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="144" height="144"></svg>',
            encoding="utf-8",
        )
        self.spec = self.root / "buttons.json"
        self.spec.write_text(
            json.dumps(
                {
                    "buttons": {
                        "0,0": {
                            "type": "submit_text",
                            "text": "yes",
                            "icon": "yes.svg",
                        },
                        "0,1": {
                            "type": "toggle_sequence",
                            "on": [{"type": "url", "url": "demo://start"}],
                            "off": [{"type": "url", "url": "demo://stop"}],
                            "icon": "yes.svg",
                            "off_icon": "yes.svg",
                        },
                        "1,0": {
                            "type": "hotkey",
                            "key": "fn",
                            "icon": "yes.svg",
                        },
                    }
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, check=True):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=check,
            capture_output=True,
            text=True,
        )

    def test_dry_run_does_not_write(self):
        before = self.manifest.read_bytes()
        result = self.run_cli(
            "apply",
            "--manifest",
            str(self.manifest),
            "--spec",
            str(self.spec),
            "--dry-run",
        )
        output = json.loads(result.stdout)
        self.assertTrue(output["dry_run"])
        self.assertEqual(before, self.manifest.read_bytes())
        self.assertFalse((self.page / "Images").exists())

    def test_apply_backs_up_and_preserves_untouched_button(self):
        backup_dir = self.root / "backups"
        result = self.run_cli(
            "apply",
            "--manifest",
            str(self.manifest),
            "--spec",
            str(self.spec),
            "--backup-dir",
            str(backup_dir),
        )
        output = json.loads(result.stdout)
        backup = Path(output["backup"])
        self.assertTrue(backup.is_dir())
        self.assertFalse((backup / "Profiles/PAGE/Images").exists())
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        actions = data["Controllers"][0]["Actions"]
        self.assertEqual(actions["2,1"], self.original_action)
        submit = actions["0,0"]
        self.assertEqual(submit["UUID"], "com.elgato.streamdeck.multiactions.routine")
        self.assertEqual(submit["Actions"][0]["Actions"][0]["Settings"]["pastedText"], "yes")
        return_key = submit["Actions"][0]["Actions"][1]["Settings"]["Hotkeys"][0]
        self.assertEqual(return_key["NativeCode"], 36)
        self.assertEqual(return_key["QTKeyCode"], 16777220)
        toggle = actions["0,1"]
        self.assertEqual(toggle["UUID"], "com.elgato.streamdeck.multiactions.routine2")
        self.assertEqual(len(toggle["Actions"][0]["Actions"]), 1)
        self.assertEqual(len(toggle["Actions"][1]["Actions"]), 1)
        self.assertEqual(len(toggle["States"]), 2)
        for state in (submit["States"][0], *toggle["States"]):
            self.assertTrue((self.page / state["Image"]).is_file())
        fn = actions["1,0"]["Settings"]["Hotkeys"][0]
        self.assertEqual(fn["NativeCode"], 63)
        self.assertEqual(fn["VKeyCode"], 63)

    def test_generated_v3_actions_include_runtime_plugin_metadata(self):
        self.run_cli(
            "apply",
            "--manifest",
            str(self.manifest),
            "--spec",
            str(self.spec),
            "--backup-dir",
            str(self.root / "backups"),
        )
        actions = json.loads(self.manifest.read_text(encoding="utf-8"))["Controllers"][0]["Actions"]
        expected = {
            "Name": "Multi Action",
            "UUID": "com.elgato.streamdeck.multiactions",
            "Version": "1.0",
        }
        self.assertEqual(actions["0,0"]["Plugin"], expected)
        self.assertEqual(actions["0,1"]["Plugin"], expected)

    def test_v3_multi_actions_use_action_lanes_with_complete_nested_shells(self):
        self.run_cli(
            "apply",
            "--manifest",
            str(self.manifest),
            "--spec",
            str(self.spec),
            "--backup-dir",
            str(self.root / "backups"),
        )
        actions = json.loads(self.manifest.read_text(encoding="utf-8"))["Controllers"][0]["Actions"]
        for coordinate in ("0,0", "0,1"):
            with self.subTest(coordinate=coordinate):
                action = actions[coordinate]
                self.assertEqual(action["Settings"], {})
                self.assertNotIn("Routine", action["Settings"])
                self.assertNotIn("RoutineAlt", action["Settings"])
                self.assertEqual(len(action["Actions"]), 2)
                for lane in action["Actions"]:
                    self.assertIn("Actions", lane)
                    for step in lane["Actions"]:
                        self.assertIn("ActionID", step)
                        self.assertIn("Plugin", step)
                        self.assertIn("Resources", step)

    def test_invalid_coordinate_refuses_write(self):
        self.spec.write_text(
            json.dumps({"buttons": {"left": {"type": "text", "text": "no"}}}),
            encoding="utf-8",
        )
        before = self.manifest.read_bytes()
        result = self.run_cli(
            "apply",
            "--manifest",
            str(self.manifest),
            "--spec",
            str(self.spec),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid coordinate", result.stderr)
        self.assertEqual(before, self.manifest.read_bytes())

    def test_missing_icon_refuses_before_backup(self):
        self.spec.write_text(
            json.dumps(
                {
                    "buttons": {
                        "0,0": {
                            "type": "submit_text",
                            "text": "yes",
                            "icon": "missing.png",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        backup_dir = self.root / "backups"
        before = self.manifest.read_bytes()
        result = self.run_cli(
            "apply",
            "--manifest",
            str(self.manifest),
            "--spec",
            str(self.spec),
            "--backup-dir",
            str(backup_dir),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Icon does not exist", result.stderr)
        self.assertEqual(before, self.manifest.read_bytes())
        self.assertFalse(backup_dir.exists())

    def test_wrong_icon_dimensions_refuse_write(self):
        self.icon.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72"></svg>',
            encoding="utf-8",
        )
        before = self.manifest.read_bytes()
        result = self.run_cli(
            "apply",
            "--manifest",
            str(self.manifest),
            "--spec",
            str(self.spec),
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Icon must be 144 x 144", result.stderr)
        self.assertEqual(before, self.manifest.read_bytes())

    def test_discover_lists_page_and_existing_button(self):
        result = self.run_cli("discover", "--root", str(self.root / "ProfilesV3"))
        output = json.loads(result.stdout)
        self.assertEqual(output["profiles"][0]["current_page"], "PAGE")
        self.assertEqual(
            output["profiles"][0]["pages"][0]["buttons"]["2,1"]["uuid"],
            "com.elgato.streamdeck.page.next",
        )

    def test_bundled_png_icons_are_144_square(self):
        icons = REPO_ROOT / ".agents/skills/modify-stream-deck/assets/icons"
        for path in icons.glob("*.png"):
            with self.subTest(icon=path.name):
                data = path.read_bytes()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                width, height = struct.unpack(">II", data[16:24])
                self.assertEqual((width, height), (144, 144))

    def test_bundled_dictation_buttons_do_not_open_a_wispr_url(self):
        spec = json.loads(
            (REPO_ROOT / ".agents/skills/modify-stream-deck/assets/four-button-coding.json").read_text(encoding="utf-8")
        )
        for coordinate in ("2,0", "0,1"):
            with self.subTest(coordinate=coordinate):
                button = spec["buttons"][coordinate]
                steps = button["on"] + button["off"]
                self.assertFalse(
                    any(step.get("type") == "url" for step in steps),
                    "Opening a Wispr URL can steal focus from the user's active text field",
                )
                hotkeys = [step for step in steps if step.get("type") == "hotkey"]
                self.assertTrue(hotkeys)
                for hotkey in hotkeys:
                    self.assertEqual(hotkey["key"], "space")
                    self.assertEqual(set(hotkey["modifiers"]), {"ctrl", "option"})

    def test_local_documentation_links_resolve(self):
        documents = [
            REPO_ROOT / "README.md",
            REPO_ROOT / ".agents/skills/modify-stream-deck/SKILL.md",
        ]
        markdown_link = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
        html_link = re.compile(r"(?:href|src)=\"([^\"]+)\"")
        for document in documents:
            text = document.read_text(encoding="utf-8")
            for raw in markdown_link.findall(text) + html_link.findall(text):
                target = raw.strip("<>").split("#", 1)[0]
                if not target or "://" in target or target.startswith(("mailto:", "/")):
                    continue
                with self.subTest(document=document.name, target=target):
                    self.assertTrue((document.parent / target).exists())


if __name__ == "__main__":
    unittest.main()
