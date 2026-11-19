"""Compatibility imports for the component implementation."""
from .filter_ordering.query import *
from .filter_ordering import query as _implementation
def __getattr__(name):
    return getattr(_implementation, name)
