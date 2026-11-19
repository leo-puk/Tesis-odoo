"""Compatibility imports for the component implementation."""
from .adquisition.legacy_policy import *
from .adquisition import legacy_policy as _implementation
def __getattr__(name):
    return getattr(_implementation, name)
