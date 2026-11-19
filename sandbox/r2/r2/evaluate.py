"""Compatibility imports for the component implementation."""
from .evaluation.evaluate import *
from .evaluation import evaluate as _implementation
def __getattr__(name):
    return getattr(_implementation, name)
