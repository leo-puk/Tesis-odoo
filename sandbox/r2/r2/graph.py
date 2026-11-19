"""Compatibility imports for the component implementation."""
from .relations.legacy_graph import *
from .relations import legacy_graph as _implementation
def __getattr__(name):
    return getattr(_implementation, name)
