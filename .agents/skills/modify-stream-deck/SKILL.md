---
name: modify-stream-deck
description: Inspect, back up, repair, and customize Elgato Stream Deck profiles, buttons, hotkeys, multi-actions, toggles, labels, and icons. Use when a user asks to configure Stream Deck keys, make a button type and submit text, launch an app or URL, trigger dictation, fix a button that behaves differently from a physical keypress, or package a repeatable Stream Deck layout. Skip Stream Deck SDK plugin development unless the task also requires profile wiring.
license: MIT
---

# Modify Stream Deck

Safely change the user's live Stream Deck profile while preserving unrelated buttons and a recoverable pre-change copy.

## Workflow

1. Confirm the requested device, page, button coordinates, and press behavior. Infer coordinates only after inspecting the active page.
2. Locate the profile root. On macOS, start at `~/Library/Application Support/com.elgato.StreamDeck/ProfilesV3`.
3. Inspect the bundle manifest and page manifests. Run `scripts/streamdeck_profile.py discover` or `inspect`; never choose a page from its UUID alone.
4. Translate each requested press into explicit actions. Use `submit_text` for “type text, then press Enter.” Do not rely on the Text action's `isSendingEnter` flag in terminal and coding-agent prompt fields.
5. For dictation, use the app's global keyboard shortcut. Do not open a dictation URL when the user wants to keep typing into the focused field.
6. Create or select a 144 × 144 icon with a short label and one dominant symbol. Give toggle states different colors or symbols.
7. Write a declarative spec and preview it with `apply --dry-run`. Read [references/spec-format.md](references/spec-format.md) for the accepted action types.
8. Apply with `--restart-app`. The helper copies the entire `.sdProfile` bundle before the atomic manifest replacement.
9. Validate JSON, preserved coordinates, installed image dimensions, V3 Multi Action lanes, and `Plugin` descriptors. Stream Deck can render a key's icon yet show ⚠️ when its runtime action shape is invalid.
10. Do not live-fire a button in a consequential field. Use a blank text editor or ask the user to press it. A successful JSON write does not prove the receiving app accepted the keystrokes.

## Safety rules

- Back up the full profile bundle before every write. Stop if a backup cannot be created.
- Preserve every coordinate outside the requested set. Compare before and after summaries.
- Treat button presses as real user input. Never test Enter, delete, send, publish, payment, or destructive shortcuts against the user's active app.
- Keep credentials, account identifiers, device serials, profile UUIDs, logs, and live manifests out of public examples.
- Prefer built-in Stream Deck actions. Add a custom plugin only when built-ins cannot express the behavior.
- Preserve the frontmost app and focused control when an action should type or dictate there. URL schemes can activate their owning app and move focus.
- Every generated V3 action, including steps inside a Multi Action lane, needs a complete action shell with `ActionID`, `Plugin`, and `Resources`.
- Prepare and validate the replacement manifest before stopping Stream Deck. Replace it atomically, then allow the app to reload.
- If the app rewrites the file, restore the backup and use the visible Stream Deck editor instead of racing the process.

## Action choices

- **Type only:** `text`.
- **Type and submit:** `submit_text`, which runs Text followed by a physical Return hotkey.
- **Single shortcut:** `hotkey`.
- **Open a page or app protocol:** `url` or `open`.
- **Several ordered actions:** `sequence`.
- **Alternate between start and stop:** `toggle_sequence` with separate icons.

Read [references/profile-format.md](references/profile-format.md) when diagnosing profile discovery, pages, image paths, or raw V3 action JSON. Read [references/spec-format.md](references/spec-format.md) before writing a new spec or adding an action type.

## ⚠️ on press

If generated keys render but show ⚠️ when pressed:

1. Check whether a V3 Multi Action incorrectly stores steps in the legacy `Settings.Routine` and `Settings.RoutineAlt` fields.
2. Move the two sequences into top-level `Actions` lanes. Each lane has an `Actions` array.
3. Give each nested step a complete V3 shell with `ActionID`, `Plugin`, `Resources`, `Settings`, `State`, `States`, and `UUID`.
4. Compare provider metadata against the installed Stream Deck version, restart Stream Deck, and ask the user to test one harmless key.

Stream Deck 7.4 rendered icons for legacy V2 `Routine` data inside a V3 profile, then rejected every affected key at execution time. The helper now writes V3 action lanes and complete nested steps.

## Focus-preserving dictation

Trigger dictation with the same global shortcut the user presses on their keyboard. A URL such as `wispr-flow://start-hands-free` can activate Wispr and move focus away from the intended text field.

Wispr Flow uses `Fn+Space` for hands-free mode on a standard Mac setup. This skill's hotkey recipe does not model Apple's Fn modifier, so add `Ctrl+Option+Space` as a second hands-free shortcut in Wispr Flow, then use that hotkey in both lanes of the Stream Deck toggle. Keep the user's existing Fn shortcut.

For a button that types before dictation, put the Text step first and the hands-free hotkey second. Do not add app activation, window selection, or textbox discovery.

## Bundled example

`assets/four-button-coding.json` demonstrates a privacy-safe layout:

- YES plus physical Return;
- NO plus physical Return;
- NO plus a hands-free dictation toggle;
- a standalone TALK/STOP toggle.

The example uses placeholder coordinates and `Ctrl+Option+Space` for Wispr Flow hands-free mode. Add that combination as a secondary Wispr shortcut before applying the example. Inspect the user's page and adjust coordinates to avoid overwriting buttons they want to keep.

## Commands

```bash
python3 scripts/streamdeck_profile.py discover
python3 scripts/streamdeck_profile.py inspect --manifest /path/to/page/manifest.json
python3 scripts/streamdeck_profile.py apply \
  --manifest /path/to/page/manifest.json \
  --spec assets/four-button-coding.json \
  --dry-run
python3 scripts/streamdeck_profile.py apply \
  --manifest /path/to/page/manifest.json \
  --spec assets/four-button-coding.json \
  --restart-app
```

## Completion gate

Finish only when:

- the pre-change `.sdProfile` backup exists;
- the edited manifest parses;
- requested coordinates contain the intended action UUIDs and settings;
- every generated action shell contains the matching runtime `Plugin` descriptor;
- Multi Actions use top-level V3 action lanes instead of legacy `Settings.Routine` fields;
- untouched coordinates match the pre-change manifest;
- every referenced icon exists and is 144 × 144;
- Stream Deck is running and its recent log has no profile-load error;
- the user has one safe, concrete button test to perform.
