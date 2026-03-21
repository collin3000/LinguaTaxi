#!/usr/bin/env python3
"""
generate_translations.py — Translate locales/en.json into 29 languages via DeepL API.

Usage:
    python scripts/generate_translations.py --api-key YOUR_KEY
    python scripts/generate_translations.py --api-key YOUR_KEY --languages ES,FR,DE
    DEEPL_AUTH_KEY=YOUR_KEY python scripts/generate_translations.py

{variable} placeholders are protected as XML tags before translation and restored
after, so they survive DeepL's translation without being mangled.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"
BATCH_SIZE = 50
BATCH_SLEEP = 0.5  # seconds between batches

# Maps our internal 2-letter code → DeepL target_lang code.
# Codes not listed here are passed through unchanged.
DEEPL_TARGET_MAP = {
    "PT": "PT-PT",
    "ZH": "ZH-HANS",
    # NB is already correct for Norwegian Bokmål.
}

# All 29 non-English languages (keys from languages.json, excluding EN).
ALL_LANGUAGES = [
    "AR", "BG", "CS", "DA", "DE", "EL", "ES", "ET", "FI", "FR",
    "HU", "ID", "IT", "JA", "KO", "LT", "LV", "NB", "NL", "PL",
    "PT", "RO", "RU", "SK", "SL", "SV", "TR", "UK", "ZH",
]

# ---------------------------------------------------------------------------
# Placeholder protection helpers
# ---------------------------------------------------------------------------

# Matches {word} or {word_with_underscores} — Python-style format placeholders.
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def protect_placeholders(text: str) -> str:
    """Replace {var} with sentinel strings that DeepL won't translate."""
    return _PLACEHOLDER_RE.sub(r'XPHR_\1_XPHR', text)


def restore_placeholders(text: str) -> str:
    """Restore XPHR_var_XPHR sentinels back to {var}."""
    return re.sub(r'XPHR_([A-Za-z_][A-Za-z0-9_]*)_XPHR', r'{\1}', text)


# ---------------------------------------------------------------------------
# DeepL API
# ---------------------------------------------------------------------------

def deepl_translate(texts: list[str], target_lang: str, api_key: str) -> list[str]:
    """
    Translate a list of strings to target_lang via DeepL.

    Returns a list of translated strings in the same order.
    Raises urllib.error.HTTPError or ValueError on failure.
    """
    payload = json.dumps({
        "text": texts,
        "source_lang": "EN",
        "target_lang": target_lang,
        "preserve_formatting": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        DEEPL_API_URL,
        data=payload,
        headers={
            "Authorization": f"DeepL-Auth-Key {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    translations = body.get("translations", [])
    if len(translations) != len(texts):
        raise ValueError(
            f"DeepL returned {len(translations)} translations for {len(texts)} inputs"
        )
    return [t["text"] for t in translations]


# ---------------------------------------------------------------------------
# Core translation logic
# ---------------------------------------------------------------------------

def translate_language(
    keys: list[str],
    values: list[str],
    lang_code: str,
    api_key: str,
) -> dict[str, str]:
    """
    Translate all values for a single language.

    Returns a dict mapping key → translated value.
    """
    deepl_lang = DEEPL_TARGET_MAP.get(lang_code, lang_code)
    protected = [protect_placeholders(v) for v in values]
    translated: list[str] = []

    total_batches = (len(protected) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_idx in range(total_batches):
        start = batch_idx * BATCH_SIZE
        end = start + BATCH_SIZE
        batch = protected[start:end]

        print(
            f"  [{lang_code}] batch {batch_idx + 1}/{total_batches} "
            f"({len(batch)} strings)...",
            end=" ",
            flush=True,
        )
        results = deepl_translate(batch, deepl_lang, api_key)
        translated.extend(results)
        print("ok")

        if batch_idx < total_batches - 1:
            time.sleep(BATCH_SLEEP)

    # Restore placeholders and build result dict.
    result: dict[str, str] = {}
    for key, original, trans in zip(keys, values, translated):
        restored = restore_placeholders(trans)

        # Warn if translation is >50% longer than the English source.
        if len(original) > 0 and len(restored) > len(original) * 1.5:
            print(
                f"  WARNING [{lang_code}] '{key}': translation is "
                f"{len(restored)} chars vs {len(original)} English chars "
                f"(>{int(len(restored) / len(original) * 100 - 100)}% longer)"
            )

        result[key] = restored

    return result


# ---------------------------------------------------------------------------
# File I/O helpers
# ---------------------------------------------------------------------------

def load_json_ordered(path: Path) -> dict:
    """Load a JSON file preserving key insertion order (Python 3.7+ dicts do this)."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, data: dict) -> None:
    """Save a dict to JSON with Unicode characters, indentation, and a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Translate locales/en.json into multiple languages via DeepL."
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("DEEPL_AUTH_KEY", ""),
        help="DeepL API key (or set DEEPL_AUTH_KEY env var)",
    )
    parser.add_argument(
        "--languages",
        default="",
        help=(
            "Comma-separated list of language codes to translate "
            "(e.g. ES,FR,DE). Default: all 29 languages."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.api_key:
        print(
            "ERROR: No API key provided. "
            "Use --api-key or set DEEPL_AUTH_KEY environment variable.",
            file=sys.stderr,
        )
        return 1

    # Resolve paths relative to the repo root (one level up from scripts/).
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    locales_dir = repo_root / "locales"
    en_path = locales_dir / "en.json"
    overrides_dir = locales_dir / "overrides"

    if not en_path.exists():
        print(f"ERROR: Source file not found: {en_path}", file=sys.stderr)
        return 1

    # Determine which languages to translate.
    if args.languages.strip():
        requested = [c.strip().upper() for c in args.languages.split(",") if c.strip()]
        unknown = [c for c in requested if c not in ALL_LANGUAGES]
        if unknown:
            print(f"ERROR: Unknown language code(s): {', '.join(unknown)}", file=sys.stderr)
            print(f"Valid codes: {', '.join(ALL_LANGUAGES)}", file=sys.stderr)
            return 1
        target_languages = requested
    else:
        target_languages = list(ALL_LANGUAGES)

    # Load English source, preserving key order.
    en_data = load_json_ordered(en_path)

    # Separate _meta from translatable strings.
    meta_block = en_data.get("_meta", {})
    translatable_items = [(k, v) for k, v in en_data.items() if k != "_meta"]
    keys = [k for k, _ in translatable_items]
    values = [v for _, v in translatable_items]

    print(f"Loaded {len(keys)} strings from {en_path}")
    print(f"Target languages: {', '.join(target_languages)}")
    print()

    succeeded: list[str] = []
    failed: list[str] = []

    for lang in target_languages:
        print(f"--- {lang} ---")
        try:
            translated = translate_language(keys, values, lang, args.api_key)
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            print(f"  ERROR [{lang}]: HTTP {exc.code} — {exc.reason}. {body}")
            failed.append(lang)
            continue
        except Exception as exc:
            print(f"  ERROR [{lang}]: {exc}")
            failed.append(lang)
            continue

        # Load overrides if present (override keys take precedence).
        override_path = overrides_dir / f"{lang}.json"
        if override_path.exists():
            overrides = load_json_ordered(override_path)
            applied = 0
            for k, v in overrides.items():
                if k in translated:
                    translated[k] = v
                    applied += 1
                else:
                    print(f"  WARNING [{lang}]: override key '{k}' not in en.json — ignored")
            if applied:
                print(f"  Applied {applied} override(s) from {override_path.name}")

        # Build output preserving _meta at top, then keys in en.json order.
        lang_name_info = {}
        try:
            languages_path = locales_dir / "languages.json"
            if languages_path.exists():
                lang_data = load_json_ordered(languages_path)
                if lang in lang_data:
                    lang_name_info = lang_data[lang]
        except Exception:
            pass

        output: dict = {}
        output["_meta"] = {
            "locale": lang,
            "name": lang_name_info.get("name", lang),
            "version": meta_block.get("version", "1.0.0"),
            "generated": "deepl",
        }
        for k in keys:
            output[k] = translated[k]

        out_path = locales_dir / f"{lang.lower()}.json"
        save_json(out_path, output)
        print(f"  Saved -> {out_path.relative_to(repo_root)}")
        succeeded.append(lang)

    # Summary.
    print()
    print("=" * 50)
    print(f"Done. {len(succeeded)} succeeded, {len(failed)} failed.")
    if succeeded:
        print(f"  OK : {', '.join(succeeded)}")
    if failed:
        print(f"  FAIL: {', '.join(failed)}")

    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
