"""Versioned symmetric identity rules; evidence is restricted to point observations."""
from copy import deepcopy
from ..crossing.rules import FAMILY, FAMILIES, unit_identity, lookup_names

RULE_VERSION = 'unit-relations-1'
EDGE_TYPE = 'shares_technical_identity'
FAMILIES_ALLOWED = ('class', 'external_id', 'field', 'function', 'method', 'model', 'module', 'path')
EXCLUDED = ('field_path', 'field_option', 'xml_attribute', 'xpath_expression', 'manifest_key', 'identifier_mention')
SCOPES = {
    'model': ['technical_model_name'], 'module': ['technical_module_name'],
    'field': ['owner_model', 'exact_name'], 'method': ['owner_model', 'exact_name'],
    'external_id': ['explicit_addon_namespace', 'exact_local_name'],
    'path': ['explicit_addon_namespace', 'exact_relative_path'],
    'function': ['addon', 'technical_file', 'module_scope', 'qualified_name', 'exact_name'],
    'class': ['addon', 'technical_file', 'class_scope', 'qualified_name', 'exact_name'],
}
LOCATION_FIELDS = ('artifact_path', 'line_start', 'line_end', 'content_line', 'content_end_line',
                   'artifact_line', 'artifact_end_line', 'side', 'code_line', 'code_path',
                   'json_pointer', 'lines_in', 'csv_row', 'csv_column', 'csv_column_name')
CONTEXT_FIELDS = ('origin', 'syntax', 'model', 'module', 'scope', 'qualified_name', 'role', 'manifest_key')


def rule_catalog():
    return [dict(id='shared_'+family+'_identity_v1', family=family,
                 admitted_types=list(FAMILIES[family]), scope=list(SCOPES[family]),
                 comparison='exact_case_sensitive_identity_tuple', direction='undirected',
                 evidence='one stored observation with locator and extraction rule at each endpoint')
            for family in FAMILIES_ALLOWED]


def identity_for(entity, module=None):
    family = FAMILY.get(entity.get('type'))
    if family not in FAMILIES_ALLOWED:
        return None, 'family_not_enabled'
    location = entity.get('location')
    if (not isinstance(location, dict) or not isinstance(location.get('artifact_path'), str)
            or not location['artifact_path'] or not isinstance(entity.get('rule'), str) or not entity['rule']):
        raise ValueError('Enabled entity lacks a source locator or extraction rule')
    for key in ('line_start', 'line_end', 'content_line', 'content_end_line', 'artifact_line',
                'artifact_end_line', 'code_line', 'csv_row', 'csv_column'):
        if key in location and location[key] is not None and (type(location[key]) is not int or location[key] < 1):
            raise ValueError('Entity has invalid localized evidence coordinates')
    has_coordinate = any(type(location.get(k)) is int for k in ('content_line', 'artifact_line', 'code_line'))
    has_pointer = isinstance(location.get('json_pointer'), str) and location['json_pointer'].startswith('/')
    if not has_coordinate and not has_pointer:
        raise ValueError('Enabled entity has no verifiable observation coordinate')
    identity, reason = unit_identity(entity, module)
    if identity is not None and any(not isinstance(part, str) or not part for part in identity):
        raise ValueError('Identity namespace and owner must be explicit nonempty strings')
    return identity, reason


def point_observation(unit_id, ordinal, entity, module):
    """Do not carry arbitrary context fields, unit text or corpus terms into a graph."""
    observation = dict(name=entity['name'], type=entity['type'], rule=entity['rule'],
        location={k: deepcopy(entity['location'][k]) for k in LOCATION_FIELDS if k in entity['location']},
        context={k: deepcopy(entity['context'][k]) for k in CONTEXT_FIELDS if k in entity['context']})
    return dict(unit_id=unit_id, entity_ordinal=ordinal, source_module=module, observation=observation)


def names_for(entity, module):
    return lookup_names(entity, module)
