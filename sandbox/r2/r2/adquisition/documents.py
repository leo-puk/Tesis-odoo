"""Lossless admission decoding; raw downloads are not converted into documents."""
import codecs
from email.message import Message


class ScreeningDecodeError(ValueError):
    """Keep original bytes isolated when admission cannot inspect their text."""

    def __init__(self, details):
        super().__init__("Cannot decode for admission; original retained in quarantine")
        self.details = details


def decode_for_screening(raw, content_type=""):
    message = Message()
    message["Content-Type"] = content_type or "text/plain"
    declared = message.get_content_charset()
    candidates = []
    # UTF-32 signatures precede their overlapping UTF-16 prefixes.
    for markers, encoding in (
        ((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE), "utf-32"),
        ((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE), "utf-16"),
        ((codecs.BOM_UTF8,), "utf-8-sig"),
    ):
        if raw.startswith(markers):
            candidates.append(encoding)
            break
    if declared:
        candidates.append(declared)
    candidates.append("utf-8")
    attempted, errors = [], []
    for encoding in dict.fromkeys(candidates):
        attempted.append(encoding)
        try:
            text = raw.decode(encoding, errors="strict")
            if "\x00" in text:
                raise ValueError("Embedded NULs prevent reliable textual screening")
        except (LookupError, UnicodeError, ValueError) as exc:
            errors.append(dict(encoding=encoding, error=type(exc).__name__))
            continue
        return text, dict(decode_state="decoded", declared_charset=declared,
                          screening_encoding=encoding, attempted_encodings=attempted,
                          fallback_used=bool(errors), decode_errors=errors,
                          purpose="admission_only", text_conversion="not_performed")
    raise ScreeningDecodeError(dict(decode_state="unreadable", declared_charset=declared,
        attempted_encodings=attempted, decode_errors=errors, purpose="admission_only",
        text_conversion="not_performed"))


def document_text(raw, content_type=""):
    """Compatibility admission helper. HTML remains HTML; conversion is pending."""
    return decode_for_screening(raw, content_type)[0]
