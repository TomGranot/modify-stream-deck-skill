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
  "Plugin": {
    "Name": "Text",
    "UUID": "com.elgato.streamdeck.system.text",
    "Version": "1.0"
  },
  "Resources": null,
  "Settings": {},
  "State": 0,
  "States": [{}],
  "UUID": "com.elgato.streamdeck.system.text"
}
```

The `Plugin` object identifies the runtime provider. Stream Deck 7 may render an action's icon but show ⚠️ when pressed if the action shell is incomplete or points to the wrong provider.

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

V3 Multi Actions store their sequences in two top-level lanes:

```json
{
  "Actions": [
    { "Actions": [{ "ActionID": "step-uuid", "Plugin": {}, "Resources": null }] },
    { "Actions": [] }
  ],
  "Settings": {}
}
```

The first lane holds the primary sequence. The second holds the alternate sequence for a Multi Action Switch and stays empty for a one-way Multi Action. Each nested step uses a complete V3 action shell. Do not write V2 `Settings.Routine` or `Settings.RoutineAlt` fields into a V3 profile; Stream Deck 7.4 can render the icon and then show ⚠️ when pressed.

Both Multi Action shells use this provider descriptor:

```json
{
  "Name": "Multi Action",
  "UUID": "com.elgato.streamdeck.multiactions",
  "Version": "1.0"
}
```

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
