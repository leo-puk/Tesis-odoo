"""Compatibility imports for the component implementation."""
from .filter_ordering.review import *
from .filter_ordering import review as _implementation
def __getattr__(name):
    return getattr(_implementation, name)
