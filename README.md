<p align="center">
  <img src="docs/assets/banner.svg" alt="A six-key Stream Deck with programmable actions flowing into desktop apps" width="100%">
</p>

<h1 align="center">Modify Stream Deck</h1>

<p align="center"><strong>Let your coding agent configure Stream Deck buttons without gambling with your profile.</strong></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2563EB.svg" alt="MIT license"></a>
  <a href="https://github.com/TomGranot/modify-stream-deck-skill/actions/workflows/validate.yml"><img src="https://github.com/TomGranot/modify-stream-deck-skill/actions/workflows/validate.yml/badge.svg" alt="Validation status"></a>
  <a href=".agents/skills/modify-stream-deck/SKILL.md"><img src="https://img.shields.io/badge/Agent%20Skill-Codex%20%7C%20Claude%20Code%20%7C%20Cursor-7C3AED.svg" alt="Compatible with Codex, Claude Code, and Cursor"></a>
  <img src="https://img.shields.io/badge/tested-Stream%20Deck%20Mini%20%7C%207.4.1%20%7C%20macOS-111827.svg" alt="Tested with Stream Deck Mini and Stream Deck 7.4.1 on macOS">
</p>

<p align="center">
  <a href="#install-the-skill"><strong>Install</strong></a> ·
  <a href="#configure-a-button">Use it</a> ·
  <a href="#four-button-coding-starter">Starter layout</a> ·
  <a href=".agents/skills/modify-stream-deck/references/spec-format.md">Spec reference</a> ·
  <a href="SECURITY.md">Safety</a>
</p>

This portable Agent Skill lets Codex, Claude Code, Cursor, and other Agent Skills hosts inspect and modify Elgato Stream Deck profiles. It finds the right page, preserves unrelated keys, creates a full backup, installs icons, writes the replacement atomically, and restarts Stream Deck.

The bundled helper supports text, physical hotkeys, URLs, application paths, ordered Multi Actions, and two-state Multi Action Switches. It uses an explicit Return hotkey for “type and submit,” which works in prompt and terminal fields that ignore Stream Deck's Text-action Enter flag.

## Requirements

- macOS with Elgato Stream Deck 7.x;
- Python 3.10 or newer;
- a coding agent that supports the open Agent Skills format.

The profile helper uses only Python's standard library. We tested it on an Elgato Stream Deck Mini with Stream Deck 7.4.1 on macOS and against synthetic V3 fixtures. We have not tested another Stream Deck model or Windows.

## Install the skill

Install the portable skill with the open Skills CLI:

```bash
npx skills add TomGranot/modify-stream-deck-skill \
  --skill modify-stream-deck \
  -g
```

List the discovered package before installing:

```bash
npx skills add TomGranot/modify-stream-deck-skill --list
```

### Claude Code plugin

Add the repository as a marketplace and install the plugin:

```text
/plugin marketplace add TomGranot/modify-stream-deck-skill
/plugin install modify-stream-deck@stream-deck-skills
/reload-plugins
```

You can also clone the repository and test it without installation:

```bash
git clone https://github.com/TomGranot/modify-stream-deck-skill.git
cd modify-stream-deck-skill
claude --plugin-dir .
```

### Codex and Cursor from a clone

Both hosts discover the canonical project skill at `.agents/skills/modify-stream-deck/`. Clone the repository and work from its root, or copy that directory into your user-level Agent Skills folder.

## Configure a button

Ask your agent for the behavior, location, and icon:

```text
Use the modify-stream-deck skill. Back up my active profile, then make the
top-left key type "yes" and press a physical Return. Give it a green check icon.
Preserve every other button and show me the validation result.
```

The skill guides the agent through discovery, a dry-run, backup, atomic replacement, app reload, and verification. It tells the agent not to test a submitting button in your active field.

To use the helper directly:

```bash
python3 .agents/skills/modify-stream-deck/scripts/streamdeck_profile.py discover

python3 .agents/skills/modify-stream-deck/scripts/streamdeck_profile.py apply \
  --manifest "/path/to/page/manifest.json" \
  --spec ".agents/skills/modify-stream-deck/assets/four-button-coding.json" \
  --dry-run

python3 .agents/skills/modify-stream-deck/scripts/streamdeck_profile.py apply \
  --manifest "/path/to/page/manifest.json" \
  --spec ".agents/skills/modify-stream-deck/assets/four-button-coding.json" \
  --restart-app
```

The apply command refuses invalid coordinates, verifies every icon, copies the full `.sdProfile` bundle, preserves untouched coordinates, and writes complete V3 action lanes and runtime provider metadata.

## Four-button coding starter

<p align="center">
  <img src="docs/assets/four-button-preview.png" alt="Green YES and Return, red NO and Return, blue NO plus TALK, blue TALK, and purple STOP Stream Deck icons" width="760">
</p>

The sanitized starter spec at [four-button-coding.json](.agents/skills/modify-stream-deck/assets/four-button-coding.json) contains:

| Position | First press | Second press |
| --- | --- | --- |
| Top left | Type `yes`, then send a physical Return | Same action |
| Top middle | Type `no`, then send a physical Return | Same action |
| Top right | Type `no `, then start hands-free Wispr Flow dictation | Stop dictation |
| Bottom left | Start hands-free Wispr Flow dictation | Stop dictation |

Coordinates are examples, not assumptions about your hardware. The skill inspects the active page before applying them.

The dictation buttons send `Ctrl+Option+Space`, which Wispr Flow can use as a secondary hands-free shortcut. Add that shortcut in Wispr Flow before applying the starter. The buttons do not open Wispr, select an application, or search for a textbox, so your current text field keeps focus. Your existing Fn shortcut can remain in place.

## Supported button recipes

| Recipe | Use it for |
| --- | --- |
| `text` | Type without submitting |
| `submit_text` | Type, then send a physical Return |
| `hotkey` | Send Return, Space, Tab, Escape, or a supported modifier combination |
| `url` | Open a web page or registered app protocol |
| `open` | Open an application or file path |
| `sequence` | Run several actions in order |
| `toggle_sequence` | Alternate between start and stop routines with separate icons |
| `remove` | Clear one named coordinate |

Read the [spec reference](.agents/skills/modify-stream-deck/references/spec-format.md) for exact fields and examples.

## Safety model

Direct profile editing is powerful because a Stream Deck key can submit text, delete data, or trigger an external action. The skill therefore requires:

- a full pre-change profile backup;
- a dry-run before each write;
- atomic manifest replacement;
- preservation checks for untouched coordinates;
- no live testing in a consequential field;
- no credentials, device serials, profile UUIDs, account identifiers, or live manifests in public examples.

If Stream Deck rewrites a profile during the change, restore the backup and use the visible editor. Do not race repeated writes against the application.

## Known limitation

A Multi Action Switch tracks button presses, not the state of another app. If you stop dictation with a separate keyboard shortcut, the Stream Deck icon can remain on STOP until the next button press resets it.

Application protocol URLs may move focus to their owning app. Use a global hotkey for dictation or any workflow that must act on the current text field.

If an icon renders but the key shows ⚠️ when pressed, inspect the action's V3 shape. Multi Actions need top-level `Actions` lanes, and each nested step needs its own `ActionID`, `Plugin`, and `Resources`. Legacy `Settings.Routine` data can render but does not execute in the V3 profile format used by Stream Deck 7.4.

## Validate the repository

```bash
python3 -m unittest discover -s tests -v
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  .agents/skills/modify-stream-deck
uvx --from skills-ref agentskills validate \
  .agents/skills/modify-stream-deck
```

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before adding a recipe or platform. New action types need a fixture test, failure behavior, and a public example without live profile data.

## License

[MIT](LICENSE)
