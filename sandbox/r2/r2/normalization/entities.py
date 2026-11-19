"""Observed identifiers with evidence. No graph, cross-unit resolution or execution."""
import ast
import io
import re
import tokenize
from pathlib import PurePosixPath
from lxml import etree
from ..extract import FIELD_OPTIONS
from ..csv_entities import extract_csv_entities
from .anchors import partial_anchors

ENTITY_RULE_VERSION = 'observed_entities_v2_scopes'


def extract_entities(text, path, locator, origin='code', module=None, side=None, start=1):
    entities, warnings = [], []

    def add(name, kind, line, rule, context=None, lookup=None):
        if not isinstance(name,str) or not name:
            return
        location={**locator,'content_line':line}
        if side:
            location.update(side=side,code_line=start+line-1,code_path=path)
        else:
            location['artifact_line'] = locator.get('line_start',1)+line-1 if 'line_start' in locator else None
        item=dict(name=name,type=kind,location=location,rule=rule,
                  context={"origin":origin,"syntax":'python' if path.endswith('.py') else None,
                           "module":module,**(context or {})},lookup_keys=lookup or [])
        if item not in entities:
            entities.append(item)

    def mentions(value, line, mention_origin):
        for span in re.findall(r'`+([^`\n]+)`+',value):
            if re.fullmatch(r'(?:[\w.-]+/)+[\w.-]+',span):
                add(span,'path_mention',line,'backtick_path_mention_v1',dict(origin=mention_origin))
                continue
            for name in re.findall(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*',span):
                add(name,'identifier_mention',line,'backtick_mention_v1',dict(origin=mention_origin))

    if origin != 'code':
        for line,value in enumerate(text.splitlines(),1):
            mentions(value,line,origin)
        return entities,warnings

    if path.endswith('.py'):
        # Comments remain observations of comments, never Python declarations.
        stream=tokenize.generate_tokens(io.StringIO(text).readline)
        try:
            for token in stream:
                if token.type==tokenize.COMMENT:
                    mentions(token.string,token.start[0],'comment')
        except (tokenize.TokenError,IndentationError,SyntaxError):
            pass
        try:
            tree=ast.parse(text)
        except SyntaxError:
            warnings.append('Incomplete Python fragment; only explicit local token patterns recognized')
            for item in partial_anchors(text,path,module):
                add(item['name'],'field_option' if item['kind']=='property' else 'xml_attribute',item['line'],
                    'partial_python_tokens_v1',dict(scope='partial_no_owner_inferred'),[item['key']])
            return entities,warnings

        def literal(node):
            try:
                return ast.literal_eval(node)
            except (ValueError,TypeError,SyntaxError,RecursionError):
                return None

        def visit(node, model=None, class_name=None, scope='module', qualname=()):
            if isinstance(node,ast.ClassDef):
                declared,inherited=None,None
                for stmt in node.body:
                    if isinstance(stmt,ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target,ast.Name) and target.id=='_name': declared=literal(stmt.value)
                            if isinstance(target,ast.Name) and target.id=='_inherit': inherited=literal(stmt.value)
                owner=declared if isinstance(declared,str) else inherited if isinstance(inherited,str) else None
                class_path=(*qualname,node.name)
                add(node.name,'class',node.lineno,'python_class_v2_scopes',
                    dict(model=owner,role='declaration',scope='class',qualified_name='.'.join(class_path)))
                for stmt in node.body:
                    visit(stmt,owner,node.name,'class',class_path)
                return
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                # Only definitions in a class namespace become methods. A
                # function defined inside a method belongs to a new local
                # namespace, even when it closes over the method's ``self``.
                is_method=scope=='class'
                function_path=(*qualname,node.name)
                declared_model=model if is_method else None
                keys=([f'method:{model}.{node.name}'] if is_method and model else
                      ['function:'+node.name] if scope=='module' else [])
                add(node.name,'method' if is_method else 'function',node.lineno,
                    'python_callable_declaration_v2_scopes',
                    dict(model=declared_model,role='declaration',
                         scope='class' if is_method else 'module' if scope=='module' else 'local',
                         qualified_name='.'.join(function_path)),keys)
                # Defaults, annotations and decorators are evaluated in the
                # surrounding namespace; the body has its own function scope.
                body=set(node.body)
                for child in ast.iter_child_nodes(node):
                    if child not in body:
                        visit(child,model,class_name,scope,qualname)
                for stmt in node.body:
                    visit(stmt,declared_model,class_name if is_method else None,
                          'function',(*function_path,'<locals>'))
                return
            if isinstance(node,ast.Lambda):
                visit(node.args,model,class_name,scope,qualname)
                visit(node.body,None,None,'function',(*qualname,'<lambda>','<locals>'))
                return
            context=dict(model=model,role='reference')
            if isinstance(node,ast.Assign) and scope=='class':
                for target in node.targets:
                    if isinstance(target,ast.Name) and target.id in {'_name','_inherit'}:
                        values=literal(node.value)
                        for value in values if isinstance(values,list) else [values]:
                            if isinstance(value,str):
                                add(value,'model',node.lineno,'odoo_model_literal_v1',context,['model:'+value])
                call=node.value
                if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and isinstance(call.func.value,ast.Name) and call.func.value.id=='fields':
                    for target in node.targets:
                        if isinstance(target,ast.Name):
                            keys=[f'field:{model}.{target.id}'] if model else []
                            add(target.id,'field',target.lineno,'odoo_field_assignment_v1',dict(model=model,role='declaration'),keys)
                    for kw in call.keywords:
                        if kw.arg in FIELD_OPTIONS:
                            add(kw.arg,'field_option',kw.lineno,'odoo_field_keyword_v1',context,['property:'+kw.arg])
                        value=literal(kw.value)
                        if kw.arg=='comodel_name' and isinstance(value,str):
                            add(value,'model',kw.value.lineno,'odoo_comodel_literal_v1',context,['model:'+value])
                        if kw.arg in {'compute','inverse'} and isinstance(value,str):
                            add(value,'method_reference',kw.value.lineno,'odoo_compute_literal_v1',context,
                                [f'method:{model}.{value}'] if model else [])
                        if kw.arg=='related' and isinstance(value,str):
                            add(value,'field_path',kw.value.lineno,'odoo_related_literal_v1',context)
                    if call.func.attr in {'Many2one','One2many','Many2many'} and call.args:
                        value=literal(call.args[0])
                        if isinstance(value,str): add(value,'model',call.lineno,'odoo_comodel_argument_v1',context,['model:'+value])
            if isinstance(node,ast.Import):
                for alias in node.names: add(alias.name,'module',node.lineno,'python_import_v1',context,['module:'+alias.name])
            if isinstance(node,ast.ImportFrom) and node.module:
                add(node.module,'module',node.lineno,'python_import_from_v1',context,['module:'+node.module])
            if isinstance(node,ast.Attribute) and isinstance(node.value,ast.Name) and node.value.id=='self':
                field_api=path in {'odoo/fields.py','odoo/orm/fields.py'} or class_name=='Field'
                if field_api and node.attr in FIELD_OPTIONS:
                    add(node.attr,'field_option',node.lineno,'odoo_field_self_attribute_v1',context,['property:'+node.attr])
                else:
                    add(node.attr,'attribute_reference',node.lineno,'python_self_attribute_v1',context)
            if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Attribute) and node.value.attr=='env':
                value=literal(node.slice)
                if isinstance(value,str): add(value,'model',node.lineno,'odoo_env_literal_v1',context,['model:'+value])
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.args:
                value=literal(node.args[0])
                if node.func.attr=='ref' and isinstance(value,str):
                    qualified=value if '.' in value else f'{module}.{value}' if module else None
                    add(value,'external_id',node.lineno,'odoo_ref_literal_v1',context,['xmlid:'+qualified] if qualified else [])
                if node.func.attr=='xpath' and isinstance(value,str):
                    add(value,'xpath_expression',node.lineno,'xpath_literal_v1',context)
                    for name in re.findall(r'@([A-Za-z_][\w:-]*)',value):
                        add(name,'xml_attribute',node.lineno,'xpath_attribute_v1',context,['xml-attribute:'+name])
            for child in ast.iter_child_nodes(node):
                visit(child,model,class_name,scope,qualname)
        visit(tree)
    elif path.endswith('.csv'):
        return extract_csv_entities(text,locator,module=module,side=side,start=start,path=path)
    elif path.endswith('.xml'):
        try:
            # text was already decoded losslessly from the documented encoding.
            # Override an original XML declaration when encoding this Unicode
            # representation as UTF-8 for lxml; otherwise identifiers get mojibake.
            parser=etree.XMLParser(encoding='utf-8',resolve_entities=False,load_dtd=False,no_network=True)
            root=etree.fromstring(text.encode('utf-8'),parser)
            if root.getroottree().docinfo.doctype:
                raise ValueError('DTD is not accepted')
            for node in root.iter():
                if not isinstance(node.tag,str): continue
                for key,value in sorted(node.attrib.items()):
                    add(key,'xml_attribute',node.sourceline,'xml_attribute_name_v1',lookup=['xml-attribute:'+key])
                    if key in {'id','ref','inherit_id','t-call','t-inherit','t-name'}:
                        qualified=value if '.' in value else f'{module}.{value}' if module else None
                        add(value,'external_id',node.sourceline,'xml_explicit_identifier_v1',lookup=['xmlid:'+qualified] if qualified else [])
                    if node.tag=='field' and key=='name': add(value,'field_reference',node.sourceline,'xml_field_name_v1')
                    if node.tag=='xpath' and key=='expr': add(value,'xpath_expression',node.sourceline,'xml_xpath_v1')
                if node.tag=='field' and node.get('name')=='model' and node.text:
                    value=node.text.strip()
                    add(value,'model',node.sourceline,'xml_model_field_v1',lookup=['model:'+value])
        except (etree.XMLSyntaxError,ValueError) as exc:
            entities=[]
            warnings.append('XML extraction failed: '+str(exc))
    else:
        warnings.append('No technical entity parser for this code format; original text retained')
    return entities,sorted(set(warnings))


def manifest_entities(value, locator, text):
    tree=ast.parse(text).body[0].value
    locations={ast.literal_eval(key):(key.lineno,node) for key,node in zip(tree.keys,tree.values)}
    result=[]
    for name in sorted(value):
        line,node=locations[name]
        result.append(dict(name=name,type='manifest_key',location={**locator,'artifact_line':line},rule='manifest_literal_key_v1',
                           context=dict(origin='code',role='declaration'),lookup_keys=['manifest:'+name]))
        if name in {'depends','data','demo'} and isinstance(value[name],(list,tuple)):
            for index,item in enumerate(value[name]):
                if isinstance(item,str):
                    item_line=node.elts[index].lineno if isinstance(node,(ast.List,ast.Tuple)) else line
                    result.append(dict(name=item,type='module' if name=='depends' else 'path',location={**locator,'artifact_line':item_line},
                        rule='manifest_literal_value_v1',context=dict(origin='code',manifest_key=name),
                        lookup_keys=[('module:' if name=='depends' else 'file:')+item]))
    return result
