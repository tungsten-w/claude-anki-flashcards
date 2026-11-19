# /anki-deck — Obsidian notes → Anki flashcards

Turn the notes of an Obsidian vault into Anki flashcards, folder by folder, with Claude Code.

```
/anki-deck courses/linux
```

Claude reads every note in `courses/linux/`, writes flashcards into `flashcards/courses/linux/`, and syncs them to the Anki deck `courses::linux`. Run it again later: only new or modified notes are processed, edited cards are updated in Anki (review history kept), removed cards are deleted. **Your notes are never modified.**

## Requirements

- Anki desktop, started at least once (tested with 26.09)
- Obsidian 1.12+ (for its command line interface)
- Claude Code
- Python 3.9+ (standard library only)

Tested on Linux. macOS and Windows paths are handled but not yet tested.

## Install (2 minutes)

This skill lives **inside your vault** (`<vault>/.claude/skills/anki-deck/`), not in `~/.claude/skills/`. The installer puts it there and sets up the rest of the pipeline:

```bash
cd anki-deck            # the folder from this zip
python3 install.py "/path/to/your/vault"
```

The installer is idempotent and:

1. installs the **AnkiConnect** add-on in Anki (downloaded from ankiweb.net) and allows the `app://obsidian.md` origin;
2. detects your Anki note types (basic / reversed / cloze), in any Anki language;
3. installs the **Obsidian_to_Anki** plugin (marqp fork, latest GitHub release) in `<vault>/.obsidian/plugins/` and points it at the `flashcards/` folder (your existing settings are backed up);
4. copies the skill into `<vault>/.claude/skills/anki-deck/` with a `config.json`.

Then restart Obsidian if needed, check that **Obsidian_to_Anki** is enabled (*Settings → Community plugins*), and enable *Settings → General → Command line interface* so `/anki-deck` can trigger the sync itself.

Options: `--cards-dir DIR`, `--anki-dir PATH`, `--plugin-version TAG`, `--wait SECONDS`, `--skill-only` (run `python3 install.py --help`).

## Usage

From your vault, in Claude Code:

```
/anki-deck courses/linux              # a folder (subfolders included)
/anki-deck "courses/linux/nvim.md"    # a single note
/anki-deck courses/linux --force      # regenerate notes already up to date
/anki-deck courses/linux --no-sync    # write the cards without syncing
```

Plain requests work too: *"make me an Anki deck from courses/biology"*.

## Network access

- `install.py` downloads AnkiConnect (ankiweb.net) and the Obsidian_to_Anki release (api.github.com / github.com), and talks to AnkiConnect on `127.0.0.1:8765`.
- `anki_cards.py` only talks to AnkiConnect on `127.0.0.1:8765` and runs the local `obsidian` CLI to start the sync.

Nothing else leaves your machine.
