"""Compatibility imports for the component implementation."""
from .extract_relations.csv_entities import *
from .extract_relations import csv_entities as _implementation
def __getattr__(name):
    return getattr(_implementation, name)
