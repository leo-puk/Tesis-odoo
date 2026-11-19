"""Compatibility imports for the component implementation."""
from .evaluation.selection import *
from .evaluation import selection as _implementation
def __getattr__(name):
    # Inputs: name.
    # Does: Resolve an attribute from the implementation behind this facade.
    # Output: The requested legacy attribute.
    return getattr(_implementation, name)
