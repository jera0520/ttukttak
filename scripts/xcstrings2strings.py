#!/usr/bin/env python3
"""Localizable.xcstrings -> <lang>.lproj/Localizable.strings (+ Localizable.stringsdict).

Xcode compiles a string catalog (.xcstrings) into per-language .strings files.
Without Xcode, nothing reads the catalog, so build.sh runs this script instead.

What it does
  1. Reads the catalog. Plain translations go to Localizable.strings; plural
     variations go to Localizable.stringsdict (NSStringPluralRuleType).
  2. Fills every key a language lacks with its English text, so no .lproj is
     partial (a partial .lproj shows raw keys such as "settings.window.title").
  3. Overlays <lang>.json from --i18n (build.sh passes i18n/) when present. The overlay
     adds a language (e.g. ko) or overwrites single keys of an existing one.
       {"key": "text"}                              plain string
       {"key": {"one": "...", "other": "..."}}      plural variations
     {APP} and {PET} in overlay text become --app-name and --pet-name.
  4. --rename OLD=NEW (repeatable) replaces OLD in every catalog text, so the app
     shows its own name where Coucou's catalog says "Coucou" or "Mochi". Keys stay
     as they are (the code looks strings up by key). Catalog keys without an English
     value get the key itself as English text first, so they are renamed too.
     Overlay texts are not renamed (they use {APP} and {PET}).
  5. <lang>.InfoPlist.json in --i18n becomes <lang>.lproj/InfoPlist.strings
     (permission prompts and the bundle name), with the same {APP}/{PET} rule.
  6. Runs `plutil -lint` on every file it wrote.

Usage
  xcstrings2strings.py --xcstrings Resources/Localizable.xcstrings --out DIR \
      [--i18n DIR] [--app-name 뚝딱] [--pet-name 복슬깨비] [--rename Coucou=뚝딱 ...] \
      [--languages "en fr ..."] [--warn-regex REGEX]

--languages limits the catalog languages that are written (overlay languages
are always written). Without it, every language in the catalog is written.
--warn-regex prints a warning for every written translation whose TEXT matches REGEX
(entries whose text is just the key itself are ignored). build.sh uses it to catch
translations that still name files or paths that were renamed in the code.
"""
from __future__ import annotations

import argparse
import json
import plistlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

PLURAL_CATEGORIES = ("zero", "one", "two", "few", "many", "other")
SPEC_RE = re.compile(r"%(?:\d+\$)?(l{0,2}[dux])")


def die(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"xcstrings2strings: error: {msg}", file=sys.stderr)
    sys.exit(1)


def warn(msg: str) -> None:
    print(f"xcstrings2strings: warning: {msg}", file=sys.stderr)


# --- reading the catalog -----------------------------------------------------

def read_catalog(path: Path):
    """Returns (source_language, simple, plural, keys).

    simple[lang][key] = text        plural[lang][key] = {category: text}
    keys = every key of the catalog, also those without any translation
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        die(f"cannot read {path}: {e}")
    source = data.get("sourceLanguage", "en")
    simple: dict[str, dict[str, str]] = {}
    plural: dict[str, dict[str, dict[str, str]]] = {}
    for key, entry in data.get("strings", {}).items():
        for lang, loc in (entry.get("localizations") or {}).items():
            unit = loc.get("stringUnit")
            if unit is not None and "value" in unit:
                simple.setdefault(lang, {})[key] = unit["value"]
                continue
            variations = loc.get("variations") or {}
            if "plural" in variations:
                forms = {}
                for cat, sub in variations["plural"].items():
                    value = (sub.get("stringUnit") or {}).get("value")
                    if value is not None:
                        forms[cat] = value
                if forms:
                    plural.setdefault(lang, {})[key] = forms
                continue
            if variations:
                warn(f"{key!r} [{lang}]: unsupported variation {list(variations)} skipped")
    return source, simple, plural, list(data.get("strings", {}))


# --- renaming ----------------------------------------------------------------

def rename_pair(arg: str) -> tuple[str, str]:
    old, sep, new = arg.partition("=")
    if not sep or not old:
        raise argparse.ArgumentTypeError(f"--rename needs OLD=NEW, got {arg!r}")
    return old, new


def make_renamer(pairs: list[tuple[str, str]]):
    """text -> text with every --rename pair applied."""
    def rename(text: str) -> str:
        for old, new in pairs:
            text = text.replace(old, new)
        return text
    return rename


# --- overlay -----------------------------------------------------------------

def read_overlay(path: Path, app_name: str, pet_name: str):
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        die(f"cannot read overlay {path}: {e}")
    if not isinstance(raw, dict):
        die(f"overlay {path} must be a JSON object")

    def sub(text: str) -> str:
        return text.replace("{APP}", app_name).replace("{PET}", pet_name)

    simple: dict[str, str] = {}
    plural: dict[str, dict[str, str]] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, str):
            simple[key] = sub(value)
        elif isinstance(value, dict) and value and all(isinstance(v, str) for v in value.values()):
            bad = [c for c in value if c not in PLURAL_CATEGORIES]
            if bad:
                die(f"overlay {path}: key {key!r} has unknown plural categories {bad}")
            if "other" not in value:
                die(f"overlay {path}: plural key {key!r} needs an 'other' form")
            plural[key] = {c: sub(v) for c, v in value.items()}
        else:
            warn(f"overlay {path.name}: key {key!r} skipped (value must be a string or a plural object)")
    return simple, plural


# --- writing -----------------------------------------------------------------

_ESCAPES = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}


def esc(text: str) -> str:
    out = []
    for ch in text:
        if ch in _ESCAPES:
            out.append(_ESCAPES[ch])
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append("\\U%04X" % ord(ch))
        else:
            out.append(ch)
    return "".join(out)


def write_strings(path: Path, table: dict[str, str]) -> None:
    lines = [f'"{esc(k)}" = "{esc(v)}";' for k, v in sorted(table.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plural_spec(forms: dict[str, str]) -> str:
    """The printf length/type of the counted argument, from the 'other' form."""
    m = SPEC_RE.search(forms.get("other", "")) or next(
        (m for m in (SPEC_RE.search(v) for v in forms.values()) if m), None
    )
    return m.group(1) if m else "lld"


def write_stringsdict(path: Path, table: dict[str, dict[str, str]]) -> None:
    root = {}
    for key, forms in table.items():
        var = {
            "NSStringFormatSpecTypeKey": "NSStringPluralRuleType",
            "NSStringFormatValueTypeKey": plural_spec(forms),
        }
        var.update(forms)
        root[key] = {"NSStringLocalizedFormatKey": "%#@arg1@", "arg1": var}
    with path.open("wb") as fh:
        plistlib.dump(root, fh, fmt=plistlib.FMT_XML, sort_keys=True)


def lint(paths: list[Path]) -> None:
    if not paths or shutil.which("plutil") is None:
        return
    for i in range(0, len(paths), 50):
        res = subprocess.run(["plutil", "-lint", *map(str, paths[i:i + 50])],
                             capture_output=True, text=True)
        if res.returncode != 0:
            die("plutil -lint failed:\n" + res.stdout + res.stderr)


# --- main --------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--xcstrings", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path, help="directory that receives <lang>.lproj")
    ap.add_argument("--i18n", type=Path, help="directory with <lang>.json overlays")
    ap.add_argument("--app-name", default="뚝딱")
    ap.add_argument("--pet-name", default="복슬깨비")
    ap.add_argument("--rename", action="append", default=[], type=rename_pair, metavar="OLD=NEW",
                    help="replace OLD in catalog texts (repeatable, applied in order)")
    ap.add_argument("--languages", default="", help="catalog languages to write (space or comma separated)")
    ap.add_argument("--warn-regex", default="", help="warn about written texts that match this regex")
    args = ap.parse_args()
    warn_re = re.compile(args.warn_regex) if args.warn_regex else None
    warned = 0

    source, simple, plural, keys = read_catalog(args.xcstrings)
    en_simple = simple.setdefault(source, {})
    en_plural = plural.setdefault(source, {})
    if args.rename:
        # A key without an English value is shown as the key itself; give it that text
        # explicitly so the rename reaches it (e.g. "Restart Coucou").
        for k in keys:
            if k not in en_simple and k not in en_plural:
                en_simple[k] = k
        rename = make_renamer(args.rename)
        for table in simple.values():
            for k, v in table.items():
                table[k] = rename(v)
        for table in plural.values():
            for forms in table.values():
                for cat, v in forms.items():
                    forms[cat] = rename(v)

    overlays: dict[str, tuple[dict, dict]] = {}
    if args.i18n and args.i18n.is_dir():
        for f in sorted(args.i18n.glob("*.json")):
            if "." in f.stem:  # ko.InfoPlist.json etc. are handled below
                continue
            overlays[f.stem] = read_overlay(f, args.app_name, args.pet_name)

    wanted = [x for x in re.split(r"[,\s]+", args.languages) if x]
    catalog_langs = sorted(set(simple) | set(plural))
    if wanted:
        skipped = [l for l in catalog_langs if l not in wanted and l not in overlays]
        if skipped:
            print(f"  skip (not in --languages): {' '.join(skipped)}")
        catalog_langs = [l for l in catalog_langs if l in wanted or l in overlays]
    langs = sorted(set(catalog_langs) | set(overlays))

    args.out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for lang in langs:
        # English first (so nothing is missing), then the language, then the overlay.
        table = dict(en_simple)
        table.update(simple.get(lang, {}))
        ptable = {k: dict(v) for k, v in en_plural.items()}
        ptable.update({k: dict(v) for k, v in plural.get(lang, {}).items()})
        ov_n = 0
        if lang in overlays:
            ov_simple, ov_plural = overlays[lang]
            table.update(ov_simple)
            ptable.update(ov_plural)
            ov_n = len(ov_simple) + len(ov_plural)
            # A key moves between .strings and .stringsdict with the overlay.
            for k in ov_plural:
                table.pop(k, None)
            for k in ov_simple:
                ptable.pop(k, None)
        for k in ptable:
            table.pop(k, None)  # a plural key must not also be a plain key

        if warn_re:
            for k, v in sorted(table.items()):
                if v != k and warn_re.search(v):
                    warned += 1
                    if warned <= 8:
                        warn(f"{lang}: {k[:40]!r} -> {v[:100]!r} matches --warn-regex")
            for k, forms in sorted(ptable.items()):
                for cat, v in forms.items():
                    if warn_re.search(v):
                        warned += 1
                        if warned <= 8:
                            warn(f"{lang}: {k[:40]!r} [{cat}] -> {v[:100]!r} matches --warn-regex")

        lproj = args.out / f"{lang}.lproj"
        lproj.mkdir(parents=True, exist_ok=True)
        strings = lproj / "Localizable.strings"
        write_strings(strings, table)
        written.append(strings)
        if ptable:
            sd = lproj / "Localizable.stringsdict"
            write_stringsdict(sd, ptable)
            written.append(sd)
        own = len(simple.get(lang, {})) + len(plural.get(lang, {}))
        tag = f"  overlay {ov_n}" if lang in overlays else ""
        print(f"  {lang:<8} {len(table):>4} strings, {len(ptable)} plural  (own {own}){tag}")

    if args.i18n and args.i18n.is_dir():
        for f in sorted(args.i18n.glob("*.InfoPlist.json")):
            lang = f.name.split(".", 1)[0]
            info, info_plural = read_overlay(f, args.app_name, args.pet_name)
            if info_plural:
                die(f"{f.name}: InfoPlist values must be plain strings")
            lproj = args.out / f"{lang}.lproj"
            lproj.mkdir(parents=True, exist_ok=True)
            write_strings(lproj / "InfoPlist.strings", info)
            written.append(lproj / "InfoPlist.strings")
            print(f"  {lang:<8} InfoPlist.strings, {len(info)} keys ({f.name})")

    lint(written)
    if warned:
        warn(f"{warned} translated text(s) match --warn-regex (first 8 shown above)")
    print(f"xcstrings2strings: {len(langs)} languages, {len(written)} files written, plutil -lint OK")


if __name__ == "__main__":
    main()
