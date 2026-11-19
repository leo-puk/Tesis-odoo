"""Compatibility imports for the component implementation."""
from .relations.legacy_graph import *
from .relations import legacy_graph as _implementation
def __getattr__(name):
    # Inputs: name.
    # Does: Resolve an attribute from the implementation behind this facade.
    # Output: The requested legacy attribute.
    return getattr(_implementation, name)
