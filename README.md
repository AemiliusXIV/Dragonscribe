# Dragonscribe

A desktop save editor for **RuneScape: Dragonwilds**. It flips a world between
Standard, Hard, and Custom difficulty, and switches a character between Standard
and Custom compatibility so it can join the matching world. No terminal, no
Python install: download the app and run it.

Custom worlds unlock all the difficulty sliders. The catch the game doesn't spell
out: achievements stop unlocking while a world is Custom, and start again once
it's reverted to Standard. Dragonscribe makes hopping between the two a couple of
clicks.

## What it does

- **World mode.** Convert a world to Custom (to use difficulty sliders) or back
  to Standard/Hard (to earn achievements again).
- **Character compatibility.** Set a character to Custom (`char_type 3`) or
  Standard (`char_type 0`). A character can only join worlds of the matching
  type; the two always move together.
- **Safe by default.** Backs up every file before writing, changes only the
  bytes it must, verifies the result, and rolls back if anything looks wrong.
  It won't write while the game is open.
- **Skill levels (Advanced).** An optional, gated page for setting a character's
  skill levels (1 to 99). It's walled off behind a risk acceptance because it edits
  gameplay values; see below.

## Advanced: skill editing

There's a separate "Advanced: Skills" tab, behind a one-time acceptance screen.
It lets you set any skill's level from 1 to 99, with a confirm on every change
that spells out the exact before and after ("Set Attack from 7 to 99?"). Each
edit writes the precise XP for that level and touches only that one skill.

This is a different kind of change from world/character mode: it alters gameplay
values, so it may breach the game's Terms of Service and can get you **banned on
multiplayer or shared servers**. Use it on your own singleplayer worlds only,
and at your own risk. As always, a backup is written first.

## Installation

1. Download the latest `Dragonscribe-x.x.x.x.zip` from the
   [Releases page](https://github.com/AemiliusXIV/Dragonscribe/releases).
2. Unzip it anywhere.
3. Run `Dragonscribe.exe`.

The app is unsigned, so on first launch Windows SmartScreen may warn about an
"unknown publisher." Click **More info → Run anyway**. Some antivirus tools also
flag freshly built PyInstaller apps as a false positive; the source is here if
you'd rather build it yourself.

## How to use it

1. **Close the game completely.** It caches saves in memory and will overwrite
   your changes (or corrupt the file) if it's running. Dragonscribe blocks edits
   while it detects the game.
2. Open Dragonscribe. Your worlds and characters are listed automatically.
3. Set a world's mode, and set the characters that will join it to the matching
   compatibility.
4. Launch the game.

A quick reminder on the trade-offs, shown in the app too:

- Custom worlds disable achievements; Standard/Hard worlds allow them.
- Converting a world can disturb locked chests, protection totems, and privacy
  settings. Clear those in-game before converting.

## If a save gets damaged

Dragonscribe keeps a timestamped backup of every file it touches, in an
`editor_backups` folder next to the save, and you can restore the latest one from
inside the app. If something still goes wrong (a save won't load, an edit didn't
behave as expected), please [open an issue](https://github.com/AemiliusXIV/Dragonscribe/issues)
with what you did and what happened, and it'll be looked into. The more detail,
the better.

## Privacy

Everything stays on your machine. Dragonscribe only reads and writes your local
Dragonwilds saves. No network access, no uploads, no telemetry.

## License

Copyright (c) 2026 AemiliusXIV

Source-available. You may fork and modify it, but the source may not be copied
into other projects, in source or compiled form, without explicit written
permission. Forks must preserve this license and credit the original author. See
[LICENSE](LICENSE) for the full terms.

This project is not affiliated with or endorsed by Jagex Limited. Editing saves
with third-party tools may breach the RuneScape: Dragonwilds Terms of Service;
use is entirely at your own risk. RuneScape and RuneScape: Dragonwilds are
trademarks of Jagex Limited.
