#!/usr/bin/env python3
"""Install claude-anki-flashcards into an Obsidian vault.

    python3 install.py /path/to/vault

What it does (each step is skipped when already done):
  1. installs the AnkiConnect add-on in Anki and allows Obsidian to talk to it;
  2. waits for AnkiConnect, then detects your Anki note types (any Anki language);
  3. installs the Obsidian_to_Anki plugin (marqp fork) in the vault and configures it;
  4. installs the /anki-deck Claude Code skill in <vault>/.claude/skills/anki-deck/.

Only the Python standard library is used.
"""
import argparse
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Repo layout (skill/anki-deck/) or flat skill package (install.py next to SKILL.md).
SKILL_SRC = HERE / "skill" / "anki-deck" if (HERE / "skill" / "anki-deck").is_dir() else HERE
ANKICONNECT_ID = "2055492159"
ANKICONNECT_URL = f"https://ankiweb.net/shared/download/{ANKICONNECT_ID}?v=2.1&p=250000"
PLUGIN_ID = "obsidian-to-anki-plugin"
PLUGIN_REPO = "marqp/Obsidian_to_Anki"
OBSIDIAN_ORIGIN = "app://obsidian.md"
ANKI_URL = "http://127.0.0.1:8765"


def say(msg=""):
    print(msg, flush=True)


def step(msg):
    say(f"\n==> {msg}")


def fail(msg):
    sys.exit(f"\nError: {msg}")


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "claude-anki-flashcards-installer"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- Anki side

def anki_dirs():
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        return [home / "Library/Application Support/Anki2"]
    if system == "Windows":
        return [Path(os.environ.get("APPDATA", home / "AppData/Roaming")) / "Anki2"]
    xdg = Path(os.environ.get("XDG_DATA_HOME", home / ".local/share"))
    return [xdg / "Anki2", home / ".var/app/net.ankiweb.Anki/data/Anki2"]


def find_anki_dir(override):
    if override:
        d = Path(override).expanduser()
        if not d.is_dir():
            fail(f"{d} does not exist")
        return d
    for d in anki_dirs():
        if d.is_dir():
            return d
    fail("Anki data folder not found. Install Anki (https://apps.ankiweb.net), start it once, "
         "then run this again (or pass --anki-dir).")


def anki_request(action, origin=None, **params):
    headers = {"Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin
    req = urllib.request.Request(ANKI_URL, json.dumps({"action": action, "version": 6, "params": params}).encode(),
                                 headers=headers)
    with urllib.request.urlopen(req, timeout=5) as r:
        body = json.load(r)
        return body, r.headers.get("Access-Control-Allow-Origin")


def anki(action, **params):
    body, _ = anki_request(action, **params)
    if body.get("error"):
        raise RuntimeError(f"AnkiConnect {action}: {body['error']}")
    return body["result"]


def ankiconnect_state():
    """'down', 'no-origin' (running but Obsidian not allowed yet) or 'ready'."""
    try:
        _, allowed = anki_request("version", origin=OBSIDIAN_ORIGIN)
    except Exception:
        return "down"
    return "ready" if allowed in (OBSIDIAN_ORIGIN, "*") else "no-origin"


def install_ankiconnect(anki_dir):
    step("AnkiConnect add-on")
    addon = anki_dir / "addons21" / ANKICONNECT_ID
    changed = False
    if (addon / "__init__.py").exists():
        say(f"already installed in {addon}")
    else:
        say("downloading from AnkiWeb...")
        try:
            data = fetch(ANKICONNECT_URL)
            zipfile.ZipFile(io.BytesIO(data)).extractall(addon)
        except (urllib.error.URLError, zipfile.BadZipFile) as e:
            fail(f"could not download AnkiConnect ({e}). Install it from Anki instead: "
                 f"Tools > Add-ons > Get Add-ons > code {ANKICONNECT_ID}, then run this again.")
        say(f"installed in {addon}")
        changed = True

    # Anki keeps user-edited add-on settings in meta.json["config"]; defaults are in config.json.
    for path, key in ((addon / "meta.json", "config"), (addon / "config.json", None)):
        data = read_json(path)
        if data is None:
            continue
        cfg = data.get(key) if key else data
        if not isinstance(cfg, dict):
            continue
        origins = cfg.get("webCorsOriginList") or ["http://localhost"]
        if OBSIDIAN_ORIGIN not in origins:
            cfg["webCorsOriginList"] = origins + [OBSIDIAN_ORIGIN]
            write_json(path, data)
            say(f"allowed origin {OBSIDIAN_ORIGIN} in {path.name}")
            changed = True
    return changed


def wait_for_ankiconnect(wait_seconds):
    step("Connecting to AnkiConnect")
    state = ankiconnect_state()
    if state == "ready":
        say("AnkiConnect is running and accepts Obsidian.")
        return
    if state == "no-origin":
        say("Anki must be restarted to load the new AnkiConnect settings.\n"
            "    -> Close Anki completely (File > Exit / Quit), then start it again.")
        while ankiconnect_state() != "down":
            time.sleep(1)
        say("Anki closed, waiting for it to start again...")
    else:
        say("Anki is not running. -> Start Anki now (and open your profile).")
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        state = ankiconnect_state()
        if state == "ready":
            say("AnkiConnect is running and accepts Obsidian.")
            return
        time.sleep(1)
    fail(f"AnkiConnect did not answer within {wait_seconds}s (state: {state}). "
         "Start or restart Anki, then run this again.")


def detect_models():
    step("Detecting your Anki note types")
    names = anki("modelNames")
    models = anki("findModelsByName", modelNames=names)
    found = {}
    for m in models:
        fields = [f["name"] for f in m["flds"]]
        tmpls = m["tmpls"]
        if m["type"] == 1 and len(fields) == 2:
            found.setdefault("cloze", {"name": m["name"], "fields": fields})
        elif m["type"] == 0 and len(fields) == 2 and not any("{{type:" in t["qfmt"] for t in tmpls):
            role = "basic" if len(tmpls) == 1 else "reversed" if len(tmpls) == 2 else None
            if role:
                found.setdefault(role, {"name": m["name"], "fields": fields})
    if "basic" not in found:
        fail("no basic (front/back) note type found in Anki. Recreate Anki's stock 'Basic' note type "
             "(Tools > Manage Note Types > Add) and run this again.")
    for role in ("basic", "reversed", "cloze"):
        if role in found:
            say(f"{role:9} -> {found[role]['name']!r} {found[role]['fields']}")
        else:
            say(f"{role:9} -> not found (cards of this kind will not be generated)")
    fields_dict = {n: anki("modelFieldNames", modelName=n) for n in names}
    return found, names, fields_dict


# ------------------------------------------------------------ Obsidian side

def install_plugin(vault, version):
    step("Obsidian_to_Anki plugin (marqp fork)")
    pdir = vault / ".obsidian" / "plugins" / PLUGIN_ID
    current = (read_json(pdir / "manifest.json") or {}).get("version")
    api = f"https://api.github.com/repos/{PLUGIN_REPO}/releases/" + ("latest" if version == "latest" else f"tags/{version}")
    try:
        release = json.loads(fetch(api))
    except urllib.error.URLError as e:
        if current:
            say(f"could not reach GitHub ({e}); keeping installed version {current}")
            return
        fail(f"could not reach GitHub to download the plugin: {e}")
    tag = release["tag_name"]
    if current == tag.lstrip("v"):
        say(f"version {current} already installed")
        return
    assets = {a["name"]: a["browser_download_url"] for a in release["assets"]}
    pdir.mkdir(parents=True, exist_ok=True)
    for name in ("main.js", "manifest.json", "styles.css"):
        if name in assets:
            (pdir / name).write_bytes(fetch(assets[name]))
        elif name != "styles.css":
            fail(f"release {tag} has no {name}")
    say(f"installed {tag} in {pdir}" + (f" (was {current})" if current else ""))


DEFAULTS = {
    "Scan Directories": [], "Tag": "obsidian", "Deck": "Default", "Scheduling Interval": 0,
    "Add File Link": True, "Add Context": False, "CurlyCloze": False,
    "CurlyCloze - Highlights to Clozes": False, "ID Comments": True, "Add Obsidian Tags": False,
    "Anki API Key": "", "Sync to AnkiWeb": False, "Allow Note Type Changes": False,
    "Delete Removed Notes": True, "Auto-launch Anki": True, "Confirm Before Sync": False,
}
SYNTAX = {"Begin Note": "START", "End Note": "END", "Begin Inline Note": "STARTI", "End Inline Note": "ENDI",
          "Target Deck Line": "TARGET DECK", "File Tags Line": "FILE TAGS", "Delete Note Line": "DELETE",
          "Frozen Fields Line": "FROZEN"}


def configure_plugin(vault, cards_dir, names, fields_dict):
    step("Plugin settings")
    path = vault / ".obsidian" / "plugins" / PLUGIN_ID / "data.json"
    data = read_json(path)
    if data and "settings" in data:
        shutil.copy2(path, path.with_suffix(".json.bak"))
        s = data["settings"]
        dirs = s["Defaults"].get("Scan Directories")
        if isinstance(dirs, str):
            dirs = [dirs] if dirs.strip() else []
        if not dirs:
            say(f"existing settings scan the WHOLE vault: left as is (cards in {cards_dir}/ will be found). "
                f"To restrict the plugin to {cards_dir}/, set Scan Directories in its settings.")
        elif cards_dir not in dirs:
            s["Defaults"]["Scan Directories"] = dirs + [cards_dir]
            say(f"added {cards_dir} to Scan Directories {dirs}")
        for k, v in DEFAULTS.items():
            s["Defaults"].setdefault(k, v)
        for n in names:
            s["CUSTOM_REGEXPS"].setdefault(n, "")
            s["FILE_LINK_FIELDS"].setdefault(n, fields_dict[n][0])
        data["fields_dict"] = fields_dict
        write_json(path, data)
        say(f"existing settings updated (backup: {path.name}.bak)")
        return
    link = {n: (f[1] if len(f) > 1 else f[0]) for n, f in fields_dict.items()}
    settings = {
        "CUSTOM_REGEXPS": {n: "" for n in names}, "FILE_LINK_FIELDS": link, "CONTEXT_FIELDS": {},
        "FOLDER_DECKS": {}, "FOLDER_TAGS": {}, "Syntax": SYNTAX,
        "Defaults": DEFAULTS | {"Scan Directories": [cards_dir]},
        "IGNORED_FILE_GLOBS": ["**/*.excalidraw.md"],
    }
    write_json(path, {"settings": settings, "Added Media": [], "File Hashes": {}, "fields_dict": fields_dict})
    say(f"created {path} (scans only {cards_dir}/)")


def enable_plugin(vault):
    path = vault / ".obsidian" / "community-plugins.json"
    enabled = read_json(path, [])
    if PLUGIN_ID not in enabled:
        write_json(path, enabled + [PLUGIN_ID])
        say("plugin enabled in community-plugins.json")
    # Load it right away if this vault is open in Obsidian and its CLI is enabled.
    if not shutil.which("obsidian"):
        return False

    def obsidian_eval(code):
        try:
            r = subprocess.run(["obsidian", f"vault={vault.name}", "eval", f"code={code}"],
                               capture_output=True, text=True, timeout=30)
        except (subprocess.TimeoutExpired, OSError):
            return None
        lines = [l for l in r.stdout.splitlines() if l.startswith("=> ")]
        return lines[-1][3:].strip() if lines else None

    if obsidian_eval("app.vault.adapter.basePath") != str(vault):
        return False
    if obsidian_eval(f'app.plugins.loadManifests().then(()=>app.plugins.enablePluginAndSave("{PLUGIN_ID}"))'
                     f'.then(()=>app.plugins.enabledPlugins.has("{PLUGIN_ID}"))') == "true":
        say("plugin loaded in the running Obsidian")
        return True
    return False


# ---------------------------------------------------------------- skill

def install_skill(vault, cards_dir, models, keep_config):
    step("/anki-deck Claude Code skill")
    dest = vault / ".claude" / "skills" / "anki-deck"
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("SKILL.md", "anki_cards.py"):
        if (SKILL_SRC / name).resolve() != (dest / name).resolve():
            shutil.copy2(SKILL_SRC / name, dest / name)
    cfg_path = dest / "config.json"
    old = read_json(cfg_path, {})
    cfg = {"cards_dir": cards_dir, "anki_url": ANKI_URL, "curly_cloze": False, "models": models}
    if keep_config and old:
        cfg = old | {"cards_dir": old.get("cards_dir", cards_dir)}
    else:
        cfg["curly_cloze"] = old.get("curly_cloze", False)
    if not cfg.get("models"):
        cfg.pop("models", None)
    write_json(cfg_path, cfg)
    say(f"installed in {dest}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("vault", help="path to your Obsidian vault")
    ap.add_argument("--cards-dir", default="flashcards", help="vault folder holding the card files (default: flashcards)")
    ap.add_argument("--anki-dir", help="Anki data folder (auto-detected: the folder containing addons21/)")
    ap.add_argument("--plugin-version", default="latest", help="Obsidian_to_Anki (marqp) release tag (default: latest)")
    ap.add_argument("--wait", type=int, default=300, help="seconds to wait for Anki to (re)start (default: 300)")
    ap.add_argument("--skill-only", action="store_true", help="only (re)install the Claude Code skill files")
    ap.add_argument("--keep-skill-config", action="store_true", help="keep an existing skill config.json")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not (vault / ".obsidian").is_dir():
        fail(f"{vault} is not an Obsidian vault (no .obsidian folder). Open it once in Obsidian first.")
    cards_dir = args.cards_dir.strip("/")
    say(f"Vault: {vault}")

    if args.skill_only:
        install_skill(vault, cards_dir, read_json(SKILL_SRC / "config.json", {}).get("models") or {}, True)
        return

    install_ankiconnect(find_anki_dir(args.anki_dir))
    wait_for_ankiconnect(args.wait)
    models, names, fields_dict = detect_models()
    install_plugin(vault, args.plugin_version)
    configure_plugin(vault, cards_dir, names, fields_dict)
    loaded = enable_plugin(vault)
    install_skill(vault, cards_dir, models, args.keep_skill_config)
    (vault / cards_dir).mkdir(exist_ok=True)

    step("Done")
    if not loaded:
        say("-> Restart Obsidian (or run 'Reload app without saving' from the command palette)\n"
            "   and check that Obsidian_to_Anki is enabled in Settings > Community plugins.\n"
            "   Do this before toggling any other plugin, or Obsidian may overwrite the plugin list.")
    say(f"""
Next steps:
  cd "{vault}"
  claude
  /anki-deck <some/folder>

Cards are written to {cards_dir}/ and synced to Anki (Anki must be running).
Optional: enable Settings > General > Command line interface in Obsidian (1.12+)
so that /anki-deck can trigger the sync itself.""")


if __name__ == "__main__":
    main()
