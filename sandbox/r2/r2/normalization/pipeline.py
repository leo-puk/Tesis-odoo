"""Public entry point for reading and converting an acquisition session."""
from .readers import read_session
from .units import convert_units
from .schema import validate_collection


def normalize_session(inventory, bindings=None):
    # Inputs: inventory, bindings.
    # Does: Read, convert and validate an acquisition session.
    # Output: The normalized collection in memory.
    """Return converted records and exclusions without network or persistence.

    ``inventory`` and ``bindings`` are paths to the existing session inventory
    and processing configuration. Validation errors propagate to the caller.
    """
    units, excluded = read_session(inventory, bindings)
    converted = convert_units(units)
    validate_collection(converted)
    return {**converted, "excluded": excluded}
