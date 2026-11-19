"""Per-search, read-only access with indexed candidates and payload consistency."""
import json
from ..normalization.schema import RULE_VERSION as NORMALIZATION_RULES, SCHEMA_VERSION
from ..records import fingerprint
from ..crossing.rules import FAMILY, FAMILIES
from .rules import identity_for, names_for, FAMILIES_ALLOWED


def collection_contract(metadata):
    normalization = metadata.get('normalization', {})
    if metadata.get('schema_version') != 4 or not isinstance(normalization, dict):
        raise ValueError('Unit relations require normalized SQLite schema 4')
    if normalization.get('rules_version') != NORMALIZATION_RULES:
        raise ValueError('Collection normalization rules differ from the supported version')
    if metadata.get('include_oca_migrations', False) is not False:
        raise ValueError('Collection contradicts fixed admission policy; there is no inclusion switch')
    revision = metadata.get('collection_revision')
    if not isinstance(revision, str) or not revision:
        raise ValueError('Collection revision is absent')
    return dict(revision=revision, schema_version=4, normalization_rules_version=NORMALIZATION_RULES)


class UnitStore:
    def __init__(self, con):
        self.con = con
        for table in ('information_units', 'unit_entities', 'sources'):
            if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
                raise ValueError('Missing normalized table: '+table)
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name='unit_entity_lookup'").fetchone():
            raise ValueError('Missing unit_entity_lookup index')
        self.units = {}
        self.modules = {}
        self.observations = {}
        self.lookup_cache = {}
        self.ignored = set()

    def unit(self, uid):
        if uid not in self.units:
            row = self.con.execute('SELECT payload FROM information_units WHERE id=?', (uid,)).fetchone()
            if row is None:
                raise ValueError('Unit ID not found in collection: '+uid)
            unit = json.loads(row[0])
            if (unit.get('id') != uid or unit.get('schema_version') != SCHEMA_VERSION
                    or unit.get('rules_version') != NORMALIZATION_RULES or not isinstance(unit.get('entities'), list)
                    or unit.get('normalization_status') not in {'valid','partial'}):
                raise ValueError('Inconsistent normalized unit: '+uid)
            source_id = unit.get('source_id')
            if source_id not in self.modules:
                source = self.con.execute('SELECT payload FROM sources WHERE id=?', (source_id,)).fetchone()
                if source is None:
                    raise ValueError('Unit source ID is absent')
                binding = json.loads(source[0]).get('binding', {})
                if not isinstance(binding, dict):
                    raise ValueError('Invalid source namespace metadata')
                module = binding.get('module')
                if module is not None and (not isinstance(module, str) or not module):
                    raise ValueError('Invalid source addon namespace')
                self.modules[source_id] = module
            self.units[uid] = unit
        return self.units[uid]

    def check_row(self, row):
        uid, ordinal = row['unit_id'], row['ordinal']
        unit = self.unit(uid)
        entity = json.loads(row['payload'])
        if (type(ordinal) is not int or not 0 <= ordinal < len(unit['entities'])
                or not isinstance(entity, dict) or fingerprint(entity) != fingerprint(unit['entities'][ordinal])
                or row['name'] != entity.get('name') or row['type'] != entity.get('type')):
            raise ValueError('Entity index differs from its normalized unit')
        return unit, entity, self.modules[unit['source_id']]

    def entities(self, uid):
        if uid not in self.observations:
            unit = self.unit(uid)
            rows = self.con.execute('SELECT unit_id,ordinal,name,type,payload FROM unit_entities '
                                    'WHERE unit_id=? ORDER BY ordinal', (uid,)).fetchall()
            if [r['ordinal'] for r in rows] != list(range(len(unit['entities']))):
                raise ValueError('Unit entity index is incomplete')
            eligible = []
            for row in rows:
                _, entity, module = self.check_row(row)
                identity, reason = identity_for(entity, module)
                if identity is None:
                    self.ignored.add((uid, row['ordinal'], reason))
                else:
                    eligible.append((row['ordinal'], entity, module, identity))
            self.observations[uid] = eligible
        return self.observations[uid]

    def candidates(self, entity, module):
        family = FAMILY.get(entity['type'])
        if family not in FAMILIES_ALLOWED:
            return
        kinds = FAMILIES[family]
        for name in names_for(entity, module):
            key = (name, kinds)
            if key not in self.lookup_cache:
                markers = ','.join('?' for _ in kinds)
                self.lookup_cache[key] = self.con.execute(
                    'SELECT unit_id,ordinal,name,type,payload FROM unit_entities INDEXED BY unit_entity_lookup '
                    f'WHERE name=? AND type IN ({markers}) ORDER BY unit_id,ordinal', (name, *kinds)).fetchall()
            yield from self.lookup_cache[key]
