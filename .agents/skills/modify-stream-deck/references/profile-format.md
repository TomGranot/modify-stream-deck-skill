# Stream Deck V3 profile format

## Paths

The macOS profile root is usually:

```text
~/Library/Application Support/com.elgato.StreamDeck/ProfilesV3/
```

Each `*.sdProfile` bundle contains a root `manifest.json` and page or folder manifests under `Profiles/<page-id>/manifest.json`.

The root manifest identifies current, default, and available pages. A page manifest contains one Keypad controller with an `Actions` object keyed by zero-based `column,row` coordinates such as `0,0`.

## Action shell

A V3 action normally includes:

```json
{
  "ActionID": "generated-uuid",
  "LinkedTitle": true,
  "Name": "Text",
  "Resources": null,
  "Settings": {},
  "State": 0,
  "States": [{}],
  "UUID": "com.elgato.streamdeck.system.text"
}
```

Profile versions differ. Copy the shape of a working local action when a built-in action is not covered by the bundled helper.

## Built-in action UUIDs

| Behavior | UUID |
| --- | --- |
| Text | `com.elgato.streamdeck.system.text` |
| Hotkey | `com.elgato.streamdeck.system.hotkey` |
| Website or protocol URL | `com.elgato.streamdeck.system.website` |
| Open file or application | `com.elgato.streamdeck.system.open` |
| Multi Action | `com.elgato.streamdeck.multiactions.routine` |
| Multi Action Switch | `com.elgato.streamdeck.multiactions.routine2` |

Multi Action steps live in `Settings.Routine`. A switch stores its second path in `Settings.RoutineAlt` and has two visual states.

## macOS Return key

A physical Return hotkey uses:

```json
{
  "KeyCmd": false,
  "KeyCtrl": false,
  "KeyModifiers": 0,
  "KeyOption": false,
  "KeyShift": false,
  "NativeCode": 36,
  "QTKeyCode": 16777220,
  "VKeyCode": 36
}
```

Use this explicit hotkey after a Text step for coding-agent prompts and terminals. Their input controls may ignore the Text action's built-in send-Enter option.

## Images

Custom key images should be 144 × 144 PNGs for a Stream Deck Mini's high-density state image. Store them in the page's `Images/` directory and reference them as `Images/<filename>`.

## App lifecycle

Stream Deck may overwrite a live manifest when it exits or saves the profile. Prepare the replacement first, terminate the app, atomically replace the manifest, and relaunch or wait for the background service to return.
