"""Decode captured bytes without guessing encodings or replacing evidence."""
import codecs
from email.message import Message


def decode_artifact(raw, metadata):
    # Inputs: raw, metadata.
    # Does: Decode stored bytes and keep any conversion diagnostics.
    # Output: The available text and decoding metadata.
    message = Message()
    message["Content-Type"] = metadata.get("content_type", "text/plain")
    declared = message.get_content_charset()
    encoding = None
    for markers, candidate in (
        ((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE), "utf-32"),
        ((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE), "utf-16"),
        ((codecs.BOM_UTF8,), "utf-8-sig"),
    ):
        if raw.startswith(markers):
            encoding = candidate
            break
    # Acquisition records a successfully used screening codec, even when the
    # server supplied an invalid charset. Respect that documented choice.
    encoding = encoding or metadata.get("screening_encoding") or declared or "utf-8"
    try:
        text = raw.decode(encoding, errors="strict")
        if "\x00" in text:
            raise ValueError("Embedded NUL is not supported as textual evidence")
    except (LookupError, UnicodeError, ValueError) as exc:
        return None, dict(status="failed", encoding=encoding, error=type(exc).__name__,
                          message="Original retained; no lossless documented decoding available")
    return text, dict(status="decoded", encoding=encoding, declared_charset=declared)
