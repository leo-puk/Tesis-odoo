"""Typed exact identities; shared words and unknown owners never suffice."""
from pathlib import PurePosixPath

RULE_VERSION = 'crossing-2'
FAMILIES = {
    'method': ('method','method_reference'),
    'field': ('field','field_reference'),
    'function': ('function',), 'class': ('class',),
    **{kind:(kind,) for kind in ('model','module','external_id','field_option','xml_attribute',
                                 'path','field_path','xpath_expression','manifest_key')},
}
FAMILY = {kind:family for family,kinds in FAMILIES.items() for kind in kinds}


def partner_identity(entity, module_name=None):
    # Inputs: entity, module_name.
    # Does: Apply the input-side rules for technical identities.
    # Output: A scoped identity or a rejection reason.
    """Only identifiers observed in partner instructions can become seeds."""
    if entity.get('context',{}).get('origin') != 'code':
        return None, 'non_code_mention'
    return technical_identity(entity,module_name)


def unit_identity(entity, module_name=None):
    # Inputs: entity, module_name.
    # Does: Apply the source-side rules for technical identities.
    # Output: A scoped identity or a rejection reason.
    """Typed observations can cross regardless of code/document/comment origin."""
    if entity.get('context',{}).get('origin') not in {'code','documentation','comment'}:
        return None, 'unknown_observation_origin'
    return technical_identity(entity,module_name)


def technical_identity(entity, module_name=None):
    # Inputs: entity, module_name.
    # Does: Construct an explicit type, name and scope identity.
    # Output: A typed identity or its unresolved reason.
    """Build identity from explicit type/scope; origin eligibility is side-specific."""
    context = entity.get('context',{})
    family = FAMILY.get(entity.get('type'))
    if family is None:
        return None, 'unresolved_identifier_type'
    name = entity['name']
    model = context.get('model')
    module = context.get('module') or module_name
    if context.get('scope') == 'local':
        return None, 'local_function_not_a_model_member'
    if family in {'method','field','field_path'}:
        if not model:
            return None, 'unknown_model_owner'
        return (family,model,name), None
    if family in {'function','class'}:
        scope = context.get('scope')
        expected = 'module' if family=='function' else 'class'
        path = entity.get('location',{}).get('code_path')
        qualname = context.get('qualified_name')
        if not module or scope != expected or not path or not qualname:
            return None, 'unknown_python_namespace_or_file'
        path = PurePosixPath(path).as_posix()
        prefix = 'addons/'+module+'/'
        if path.startswith(prefix):
            path = path[len(prefix):]
        return (family,module,path,qualname,name), None
    if family == 'external_id':
        if '.' not in name:
            if not module:
                return None, 'unknown_external_id_namespace'
            name = module+'.'+name
        return (family,name), None
    if family == 'path':
        if not module:
            return None, 'unknown_path_namespace'
        return (family,module,name), None
    if family == 'manifest_key':
        if not module:
            return None, 'unknown_manifest_owner'
        return (family,module,name), None
    return (family,name), None


def lookup_names(entity, module_name=None):
    # Inputs: entity, module_name.
    # Does: Derive indexed spellings for a technical observation.
    # Output: Sorted exact candidate names.
    """Exact spelling alternatives only for an explicitly known XML-ID namespace."""
    names = {entity['name']}
    if FAMILY.get(entity['type']) == 'external_id':
        name = entity['name']
        if '.' in name:
            names.add(name.split('.',1)[1])
        elif entity.get('context',{}).get('module') or module_name:
            names.add((entity.get('context',{}).get('module') or module_name)+'.'+name)
    return sorted(names)
