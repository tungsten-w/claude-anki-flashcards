#!/usr/bin/env python3
"""Helper for the /anki-deck Claude Code skill: vault notes -> Obsidian_to_Anki card files.

Cards for the note `a/b/c/note.md` live in `<cards_dir>/a/b/c/note.md`
and go to the Anki deck `a::b::c`.

Commands (run from the vault root):
  status <folder>   list notes in the folder: new / changed / ok, plus orphan card files
  info <note.md>    card file path, deck, tags and hash of a note
  stamp <note.md>   store the note's current hash in its card file
  check [folder]    validate card file syntax (START/END, note types, fields, deck line)
  models            show the Anki note types (and field names) to use in card files
  anki              check that AnkiConnect answers (start Anki if needed)
  sync              run the plugin's "Scan Vault" command through the Obsidian CLI
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
VAULT = Path(os.environ.get("ANKI_DECK_VAULT") or HERE.parents[2]).resolve()
DEFAULT_CONFIG = {
    "cards_dir": "flashcards",
    "anki_url": "http://127.0.0.1:8765",
    "models": {
        "basic": {"name": "Basic", "fields": ["Front", "Back"]},
        "reversed": {"name": "Basic (and reversed card)", "fields": ["Front", "Back"]},
        "cloze": {"name": "Cloze", "fields": ["Text", "Back Extra"]},
    },
}
try:
    CONFIG = DEFAULT_CONFIG | json.loads((HERE / "config.json").read_text(encoding="utf-8"))
except FileNotFoundError:
    CONFIG = DEFAULT_CONFIG
CONFIG["models"] = CONFIG.get("models") or DEFAULT_CONFIG["models"]
CARDS_DIR = CONFIG["cards_dir"].strip("/")
CARDS_ROOT = VAULT / CARDS_DIR
MODELS = {m["name"]: m["fields"] for m in CONFIG["models"].values()}
CLOZE_MODEL = CONFIG["models"].get("cloze", {}).get("name")
SKIP_DIRS = {CARDS_DIR.split("/")[0], ".trash"}
OBSIDIAN_PROCESS = r"obsidian/app\.asar|Obsidian\.app/|md\.obsidian\.Obsidian|\.mount_[Oo]bsidi"


def rel(p: Path) -> Path:
    p = p if p.is_absolute() else VAULT / p
    return p.resolve().relative_to(VAULT)


def note_hash(note: Path) -> str:
    return hashlib.sha256((VAULT / note).read_bytes()).hexdigest()[:16]


def cards_path(note: Path) -> Path:
    return CARDS_ROOT / note


def deck_name(note: Path) -> str:
    parts = [p.strip() for p in note.parent.parts if p.strip()]
    return "::".join(parts) or "Default"


def tag_of(part: str) -> str:
    t = unicodedata.normalize("NFKD", part.strip().lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9_+-]+", "-", t).strip("-")


def file_tags(note: Path) -> str:
    return " ".join(t for t in (tag_of(p) for p in note.parent.parts) if t)


def stored_hash(card_file: Path):
    if not card_file.exists():
        return None
    m = re.search(r"^source_hash:\s*\"?([0-9a-f]+)", card_file.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else ""


def iter_notes(folder: Path):
    for p in sorted((VAULT / folder).rglob("*.md")):
        r = p.relative_to(VAULT)
        if any(part in SKIP_DIRS or part.startswith(".") for part in r.parts):
            continue
        if p.name.endswith(".excalidraw.md"):
            continue
        yield r


def cmd_status(folder):
    folder = rel(Path(folder))
    rows = {"new": [], "changed": [], "ok": []}
    for n in iter_notes(folder):
        h, s = note_hash(n), stored_hash(cards_path(n))
        state = "new" if s is None else ("ok" if s == h else "changed")
        rows[state].append(str(n))
    orphans = []
    cf = CARDS_ROOT / folder
    if cf.exists():
        for c in sorted(cf.rglob("*.md")):
            if not (VAULT / c.relative_to(CARDS_ROOT)).exists():
                orphans.append(str(c.relative_to(VAULT)))
    print(json.dumps({"folder": str(folder), **rows, "orphans": orphans,
                      "summary": {k: len(v) for k, v in rows.items()} | {"orphans": len(orphans)}},
                     ensure_ascii=False, indent=1))


def cmd_info(note):
    n = rel(Path(note))
    print(json.dumps({"note": str(n), "cards_file": str(cards_path(n).relative_to(VAULT)),
                      "deck": deck_name(n), "tags": file_tags(n), "source_hash": note_hash(n),
                      "stored_hash": stored_hash(cards_path(n))}, ensure_ascii=False, indent=1))


def cmd_stamp(note):
    n = rel(Path(note))
    c = cards_path(n)
    if not c.exists():
        sys.exit(f"no card file: {c}")
    txt = c.read_text(encoding="utf-8")
    h = note_hash(n)
    new, k = re.subn(r"^source_hash:.*$", f'source_hash: "{h}"', txt, count=1, flags=re.M)
    if not k:
        sys.exit("no source_hash line in the frontmatter")
    c.write_text(new, encoding="utf-8")
    print(f"stamp {c.relative_to(VAULT)} -> {h}")


def cmd_check(folder=None):
    r = rel(Path(folder)) if folder else Path(CARDS_DIR)
    root = VAULT / (r if str(r).startswith(CARDS_DIR) else Path(CARDS_DIR) / r)
    errors, total = [], 0
    for c in sorted(root.rglob("*.md")) if root.exists() else []:
        txt = c.read_text(encoding="utf-8")
        name = c.relative_to(VAULT)
        if not re.search(r"^TARGET DECK: \S", txt, re.M):
            errors.append(f"{name}: missing 'TARGET DECK: ...' line")
        if len(re.findall(r"^START$", txt, re.M)) != len(re.findall(r"^END$", txt, re.M)):
            errors.append(f"{name}: unbalanced START/END")
        for m in re.finditer(r"^START\n([\s\S]*?)\nEND$", txt, re.M):
            total += 1
            lines = m.group(1).split("\n")
            model = lines[0].strip()
            if model not in MODELS:
                errors.append(f"{name}: unknown note type '{model}' (see `models`)")
                continue
            body = "\n".join(lines[1:])
            first = MODELS[model][0]
            if not re.search(rf"^{re.escape(first)}:", body, re.M):
                errors.append(f"{name}: '{model}' card without a '{first}:' field")
            cloze = r"\{\{c\d+::" + (r"|\{[^{}]+\}" if CONFIG.get("curly_cloze") else "")
            if model == CLOZE_MODEL and not re.search(cloze, body):
                errors.append(f"{name}: cloze card without any {{{{c1::...}}}} deletion")
    print(f"{total} cards checked, {len(errors)} error(s)")
    for e in errors:
        print("  -", e)
    sys.exit(1 if errors else 0)


def cmd_models():
    print(json.dumps(CONFIG["models"], ensure_ascii=False, indent=1))


def anki(action, **params):
    req = urllib.request.Request(CONFIG["anki_url"],
                                 json.dumps({"action": action, "version": 6, "params": params}).encode())
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.load(r)


def anki_version():
    try:
        return anki("version")["result"]
    except Exception:
        return None


def cmd_anki():
    if (v := anki_version()) is not None:
        print("AnkiConnect OK, version", v)
        return
    launcher = shutil.which("anki") or ("/Applications/Anki.app" if Path("/Applications/Anki.app").exists() else None)
    if not launcher:
        sys.exit("AnkiConnect does not answer and Anki was not found: start Anki manually.")
    print("Anki is not running: starting it...")
    cmd = ["open", "-a", "Anki"] if launcher.endswith(".app") else [launcher]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(60):
        time.sleep(0.5)
        if (v := anki_version()) is not None:
            print("AnkiConnect OK, version", v)
            return
    sys.exit("AnkiConnect does not answer (is the add-on 2055492159 installed?)")


def cmd_sync():
    cmd_anki()
    manual = "click the Anki icon in Obsidian's ribbon (or run 'Obsidian_to_Anki: Scan Vault' from the command palette)."
    if not shutil.which("obsidian"):
        sys.exit("Obsidian CLI not found: " + manual)
    if shutil.which("pgrep") and not subprocess.run(["pgrep", "-f", OBSIDIAN_PROCESS], capture_output=True).stdout:
        sys.exit("Obsidian is not running: open it, then " + manual)
    r = subprocess.run(["obsidian", "command", "id=obsidian-to-anki-plugin:anki-scan-vault"],
                       capture_output=True, text=True, timeout=60)
    out = "\n".join(l for l in (r.stdout + r.stderr).splitlines() if "Gtk-WARNING" not in l and l.strip())
    print(out or "Scan Vault started in Obsidian (progress is shown in Obsidian's notices).")
    if r.returncode:
        sys.exit("The Obsidian CLI failed (is it enabled in Settings > General?). Otherwise " + manual)


if __name__ == "__main__":
    cmds = {"status": cmd_status, "info": cmd_info, "stamp": cmd_stamp, "check": cmd_check,
            "models": cmd_models, "anki": cmd_anki, "sync": cmd_sync}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](*sys.argv[2:])
