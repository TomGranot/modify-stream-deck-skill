# Contributing

Contributions should make Stream Deck profile changes safer, more portable, or easier to verify.

## Add or change an action recipe

1. Update the high-level spec parser and its reference entry.
2. Add a synthetic fixture test for the generated action JSON.
3. Test invalid input and confirm the helper refuses to write.
4. Keep examples free of device serials, profile UUIDs, account identifiers, credentials, and copied live manifests.
5. Run the repository validation commands from the README.

Use built-in Stream Deck actions when they can express the behavior. Scope platform-specific key codes and paths in both code and documentation.

## Pull requests

Explain the user behavior, the generated profile change, recovery behavior, and tests. Do not attach a live profile bundle unless you have replaced every identifying value with a synthetic fixture.
