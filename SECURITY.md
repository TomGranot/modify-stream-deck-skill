# Security

## Supported scope

The current release supports local Stream Deck V3 profile changes on macOS. It does not connect to a remote service or require credentials.

## Sensitive data

Stream Deck profiles can contain application paths, URLs, account-specific plugin settings, device identifiers, and actions that submit or delete data. Do not upload a live profile when reporting a bug. Reproduce the problem with a synthetic manifest that contains only the affected action shape.

The helper creates a full backup before writing and preserves coordinates outside the submitted spec. Review the dry-run output before applying a change.

## Report a vulnerability

Open a private GitHub security advisory for command execution, path traversal, unsafe overwrite, backup, or privacy failures. Do not include credentials or a live profile bundle.
