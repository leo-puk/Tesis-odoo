"""Deprecated module. Use the final acquisition API explicitly."""
from .adquisition import capture_plan, delete_units, SourcePolicy

__all__ = ["capture_plan", "delete_units", "SourcePolicy"]
