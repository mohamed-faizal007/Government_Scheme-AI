import re
from typing import Any

# ==========================================================
# MOJIBAKE REPAIR
# ==========================================================
# Some source PDFs store special characters (the rupee sign, curly
# quotes, ligatures like "fi", ...) in a way PyMuPDF extracts as UTF-8
# bytes that were themselves misdecoded one byte at a time as
# Windows-1252 -- e.g. the rupee sign (U+20B9, UTF-8 bytes E2 82 B9)
# comes out as three separate Latin-1-supplement/cp1252 characters
# instead of the single real rupee glyph.
#
# This is confirmed present in real extraction output (see
# WORK_REPORT.md) and reproduced directly from PyMuPDF's own output --
# it happens before any of our code runs, so it cannot be fixed by
# changing what text we send in; it has to be repaired after the fact.
# The repair below reverses the corruption: map each character back to
# the single cp1252 byte it came from, then decode that byte sequence
# as UTF-8.
#
# Safety: this is only attempted, token by token, on tokens containing
# at least one non-ASCII character, and any token where the round trip
# fails is left completely untouched. UTF-8's continuation-byte
# structure makes false positives very unlikely (a byte sequence that
# isn't genuinely mis-decoded UTF-8 almost never happens to also be
# valid UTF-8 once re-encoded), and genuine non-Latin script text (e.g.
# Devanagari/Hindi, present elsewhere in this dataset) simply can't be
# represented in cp1252 at all, so it fails the round trip and is left
# as-is rather than being corrupted.

_CP1252_TO_BYTE = {}
for _byte in range(256):
    try:
        _CP1252_TO_BYTE[bytes([_byte]).decode("cp1252")] = _byte
    except UnicodeDecodeError:
        pass


def _repair_token(token: str) -> str:
    if token.isascii():
        return token

    try:
        raw_bytes = bytes(_CP1252_TO_BYTE[ch] for ch in token)
        return raw_bytes.decode("utf-8")
    except (KeyError, UnicodeDecodeError):
        # Not actually mojibake (or contains characters cp1252 can't
        # represent at all) -- leave it exactly as it was.
        return token


def _fix_unrecoverable_residual(token: str) -> str:
    """
    Known unrecoverable case: a right double quotation mark (U+201D,
    UTF-8 bytes E2 80 9D) whose final byte (0x9D) has no cp1252 mapping
    at all -- some upstream step already replaced it with a zero-width
    space before this text ever reaches us, so _repair_token can never
    succeed on it (there is no byte left to recover). What's left is
    always the same residual signature: chr(0xE2) + chr(0x20AC) +
    optional zero-width space. In every real-data instance found, this
    immediately follows text already opened with a left curly quote, so
    mapping the leftover signature to the closing quote it clearly was
    is a safe, targeted cleanup rather than a guess about arbitrary
    content. Applied per-token (after whitespace-aware splitting) so it
    can never bleed into an unrelated, otherwise-repairable sequence.
    """

    marker = chr(0xE2) + chr(0x20AC)
    token = token.replace(marker + chr(0x200B), chr(0x201D))
    token = token.replace(marker, chr(0x201D))
    return token


def repair_mojibake(text: str) -> str:
    """
    Repair UTF-8-decoded-as-cp1252 mojibake, token by token, leaving any
    token that isn't genuinely mojibake untouched.

    Splits on runs of whitespace (not just plain spaces) while
    preserving the exact separators, since PDFs frequently glue two
    unrelated mojibake sequences together across a newline rather than
    a space -- treating that as a single token would let one
    unrecoverable byte poison an otherwise-repairable neighbor.
    """

    if text.isascii():
        return text

    pieces = re.split(r"(\s+)", text)

    for i, piece in enumerate(pieces):
        if i % 2 == 1:
            continue  # whitespace separator, keep exactly as-is

        repaired = _repair_token(piece)
        if repaired == piece:
            # The full round trip failed -- still try the narrow,
            # known-unrecoverable residual fix on its own.
            repaired = _fix_unrecoverable_residual(piece)

        pieces[i] = repaired

    return "".join(pieces)


def clean_string(text: str) -> str:
    """
    Clean unwanted characters from extracted strings.
    """

    if not isinstance(text, str):
        return text

    # Repair mojibake before anything else touches the text
    text = repair_mojibake(text)

    # Remove control characters
    text = re.sub(r"[\x00-\x1F\x7F]", "", text)

    # Remove zero-width characters
    text = text.replace(chr(0x200B), "")  # zero-width space
    text = text.replace(chr(0xFEFF), "")  # BOM / zero-width no-break space

    # Remove multiple spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_json(data: Any):
    """
    Recursively clean every string in a JSON object.
    """

    if isinstance(data, dict):
        return {
            key: clean_json(value)
            for key, value in data.items()
        }

    if isinstance(data, list):

        cleaned = []

        seen = set()

        for item in data:

            value = clean_json(item)

            key = str(value)

            if key not in seen:
                seen.add(key)
                cleaned.append(value)

        return cleaned

    if isinstance(data, str):
        return clean_string(data)

    return data
