"""Apply entity rules to a source part with its actual coordinate system."""
import textwrap
from ..selection import fingerprint
from .entities import extract_entities, manifest_entities


def part_entities(part, source, locator, artifact_path):
    """Return observations and limits, without trusting a unit's derived data."""
    entities, warnings = [], []
    module = source.get('binding', {}).get('module')
    if part['kind'] == 'manifest':
        entities = manifest_entities(part['data']['manifest'], locator, part['text'])
    elif part['kind'] == 'diff_hunk':
        data = part['data']
        for side in ('before', 'after'):
            path = data['old_path'] if side == 'before' else data['new_path']
            if path is None:
                continue
            observed, notes = extract_entities(
                textwrap.dedent(data[side]), path, locator, module=module,
                side=side, start=data[side + '_start'])
            entities.extend(observed)
            warnings.extend(notes)
    else:
        entities, warnings = extract_entities(
            part['text'], artifact_path, locator, origin=part['origin'], module=module)
    entities.sort(key=lambda e: (e['location'].get('content_line', 0),
                                e['name'], e['type'], fingerprint(e)))
    return entities, sorted(set(warnings))
