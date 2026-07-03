# Security

## Reporting a vulnerability

Found a security issue? Please open a private report through GitHub's Security
advisories ("Report a vulnerability" on the repo's Security tab) rather than a
public issue. Include what you found and how to reproduce it. I'll respond as
soon as I can.

If instead a save file of yours was damaged or behaved unexpectedly after using
Dragonscribe, that's not a security report; please open a normal issue (see
the README) so it can be looked into.

## What the app can access

- Reads and writes RuneScape: Dragonwilds save files in your local save folder
  (`%LOCALAPPDATA%\RSDragonwilds\Saved`). Nothing else is touched.
- Makes a timestamped backup of any file before changing it, in an
  `editor_backups` folder beside the original.
- Refuses to write while the game is running.
- No network access. Nothing is uploaded, and there is no telemetry.

## How writes are kept safe

Every edit changes only the specific bytes it must (two for a world mode, one
for a character's compatibility flag), then re-reads the file from disk to
confirm the change took and that nothing else moved. If that check fails, the
edit is rolled back from the backup automatically.

## Secrets

No API keys, tokens, or credentials are used or committed. The app has no
accounts and talks to no servers.
