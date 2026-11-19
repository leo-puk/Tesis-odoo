"""Compatibility imports for the component implementation."""
from .conversion.storage import *
from .conversion import storage as _implementation
def __getattr__(name):
    # Inputs: name.
    # Does: Resolve an attribute from the implementation behind this facade.
    # Output: The requested legacy attribute.
    return getattr(_implementation, name)
