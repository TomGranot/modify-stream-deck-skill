# Declarative button spec

Use this format with `scripts/streamdeck_profile.py apply`.

```json
{
  "buttons": {
    "0,0": {
      "type": "submit_text",
      "text": "yes",
      "icon": "icons/yes.png"
    }
  }
}
```

Paths are relative to the spec file. The helper copies icons into the page's `Images/` directory under a content-derived name.

## Button types

### `text`

```json
{"type":"text","text":"hello","icon":"icons/hello.png"}
```

Types text without submitting it.

### `submit_text`

```json
{"type":"submit_text","text":"yes","icon":"icons/yes.png"}
```

Creates a Multi Action containing Text and an explicit Return hotkey.

### `hotkey`

```json
{"type":"hotkey","key":"return","modifiers":[],"icon":"icons/return.png"}
```

Supported keys are `return`, `space`, `tab`, and `escape`. Supported modifiers are `cmd`, `ctrl`, `option`, and `shift`.

### `url`

```json
{"type":"url","url":"https://example.com","icon":"icons/web.png"}
```

The URL may use a registered application protocol such as `my-app://start`.

Use `hotkey` when the destination app must keep keyboard focus. Opening an application protocol can activate its owner and move focus.

### `open`

```json
{"type":"open","path":"/Applications/Example.app","icon":"icons/app.png"}
```

### `sequence`

```json
{
  "type": "sequence",
  "actions": [
    {"type":"text","text":"no "},
    {"type":"url","url":"my-app://start"}
  ],
  "icon": "icons/run.png"
}
```

Sequence steps support `text`, `hotkey`, `url`, and `open`.

### `toggle_sequence`

```json
{
  "type": "toggle_sequence",
  "on": [{"type":"url","url":"my-app://start"}],
  "off": [{"type":"url","url":"my-app://stop"}],
  "icon": "icons/start.png",
  "off_icon": "icons/stop.png"
}
```

A toggle changes state only when the Stream Deck button runs. If another keyboard shortcut changes the external application, the displayed state may become stale.

For focus-preserving Wispr Flow hands-free dictation, configure `Ctrl+Option+Space` as a secondary hands-free shortcut and use the same hotkey in both lanes:

```json
{
  "type": "toggle_sequence",
  "on": [{"type":"hotkey","key":"space","modifiers":["ctrl","option"]}],
  "off": [{"type":"hotkey","key":"space","modifiers":["ctrl","option"]}],
  "icon": "icons/talk.png",
  "off_icon": "icons/stop.png"
}
```

## Removal

```json
{"type":"remove"}
```

Removal deletes only the named coordinate. The backup remains the recovery path.
