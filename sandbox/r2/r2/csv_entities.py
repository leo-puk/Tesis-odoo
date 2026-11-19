"""Compatibility imports for the component implementation."""
from .extract_relations.csv_entities import *
from .extract_relations import csv_entities as _implementation
def __getattr__(name):
    # Inputs: name.
    # Does: Resolve an attribute from the implementation behind this facade.
    # Output: The requested legacy attribute.
    return getattr(_implementation, name)
