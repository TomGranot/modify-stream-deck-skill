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

Use `open` to launch a local application bundle. The helper writes Stream Deck's
native **Open Application** action, including the bundle path and executable
metadata required by Stream Deck 7.5.

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

For focus-preserving hands-free dictation, first build two background app wrappers:

```bash
python3 scripts/create_background_protocol_app.py \
  --display-name "Dictation Start" \
  --url "example-dictation://start-hands-free" \
  --output-dir "$HOME/Applications"

python3 scripts/create_background_protocol_app.py \
  --display-name "Dictation Stop" \
  --url "example-dictation://stop-hands-free" \
  --output-dir "$HOME/Applications"
```

Then open those app bundles from each toggle lane:

```json
{
  "type": "toggle_sequence",
  "on": [{"type":"open","path":"~/Applications/Dictation Start.app"}],
  "off": [{"type":"open","path":"~/Applications/Dictation Stop.app"}],
  "icon": "icons/talk.png",
  "off_icon": "icons/stop.png"
}
```

The wrapper uses `open -g -u`, so macOS delivers the registered URL without
bringing its owner to the foreground. Replace the example protocol with the
one documented by the dictation application.

## Removal

```json
{"type":"remove"}
```

Removal deletes only the named coordinate. The backup remains the recovery path.
