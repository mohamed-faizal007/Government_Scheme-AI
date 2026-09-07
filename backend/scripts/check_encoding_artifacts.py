"""
Scan dataset/gov_myscheme/json_output/*.json for UTF-8-decoded-as-Latin-1
mojibake artifacts (e.g. a currency sign or curly quote that got double-
decoded into a short run of Latin-1 "accented" characters).

Uses explicit Unicode codepoints rather than literal mojibake characters
embedded in source, since typing/copying those characters through
multiple encoding layers is itself unreliable.
"""

import json
import sys
from pathlib import Path

# U+00C2 (Â) and U+00E2 (â) are the two lead bytes (0xC2, 0xE2) that appear
# whenever a UTF-8 multi-byte sequence gets misdecoded one byte at a time
# as Latin-1 / cp1252. Genuine, correctly-encoded Indian-government-scheme
# text has no legitimate reason to contain either character.
MOJIBAKE_MARKERS = ("Â", "â")
REPLACEMENT_CHAR = "�"  # literal U+FFFD, produced when bytes are unrecoverable


def scan_file(path: Path):
    text = path.read_text(encoding="utf-8")
    hits = []

    for marker in MOJIBAKE_MARKERS:
        idx = 0
        while True:
            idx = text.find(marker, idx)
            if idx == -1:
                break
            snippet = text[max(0, idx - 5): idx + 8]
            hits.append((marker, snippet))
            idx += 1

    replacement_count = text.count(REPLACEMENT_CHAR)

    return hits, replacement_count


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dataset/gov_myscheme/json_output")

    files = sorted(folder.glob("*.json"))
    contaminated = []
    clean = []

    for f in files:
        hits, repl_count = scan_file(f)
        if hits or repl_count:
            contaminated.append((f.name, hits, repl_count))
        else:
            clean.append(f.name)

    print("=" * 80)
    print("MOJIBAKE / ENCODING ARTIFACT SCAN")
    print("=" * 80)
    print(f"Folder        : {folder.resolve()}")
    print(f"Total files   : {len(files)}")
    print(f"Contaminated  : {len(contaminated)}")
    print(f"Clean         : {len(clean)}")
    print("=" * 80)

    for name, hits, repl_count in contaminated:
        print(f"\n{name}  ({len(hits)} mojibake hits, {repl_count} U+FFFD replacement chars)")
        for marker, snippet in hits[:5]:
            print(f"    marker={marker!r}  context={snippet!r}")
        if len(hits) > 5:
            print(f"    ... and {len(hits) - 5} more")

    print("\nClean files:")
    for name in clean:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
