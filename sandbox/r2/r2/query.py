"""Compatibility imports for the component implementation."""
from .filter_ordering.query import *
from .filter_ordering import query as _implementation
def __getattr__(name):
    # Inputs: name.
    # Does: Resolve an attribute from the implementation behind this facade.
    # Output: The requested legacy attribute.
    return getattr(_implementation, name)
