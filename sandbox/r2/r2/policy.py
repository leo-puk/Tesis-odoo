"""Compatibility imports for the component implementation."""
from .adquisition.legacy_policy import *
from .adquisition import legacy_policy as _implementation
def __getattr__(name):
    # Inputs: name.
    # Does: Resolve an attribute from the implementation behind this facade.
    # Output: The requested legacy attribute.
    return getattr(_implementation, name)
