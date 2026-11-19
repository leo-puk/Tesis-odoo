"""Compatibility imports for the component implementation."""
from .evaluation.selection import *
from .evaluation import selection as _implementation
def __getattr__(name):
    return getattr(_implementation, name)
