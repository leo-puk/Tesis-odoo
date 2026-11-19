"""Compatibility imports; unified-diff parsing lives in normalization."""
from ..normalization.diff import HEADER, filename, parse_diff

__all__ = ["HEADER", "filename", "parse_diff"]
