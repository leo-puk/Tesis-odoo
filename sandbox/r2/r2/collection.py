"""Compatibility imports for the component implementation."""
from .conversion.storage import *
from .conversion import storage as _implementation
def __getattr__(name):
    return getattr(_implementation, name)
