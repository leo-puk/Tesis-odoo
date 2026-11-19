"""Synthetic schema-4 contract fixtures; the separate demo uses real normalization.

These fixtures deliberately support precise topologies and typed documentation.
They do not assert that the current normalizer recognizes new prose patterns.
Crossing handoffs themselves are always produced by the real cross_module().
"""
from copy import deepcopy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from r2.crossing import cross_module
from r2.normalization.schema import RULE_VERSION


def entity(name, kind='model', *, model=None, module=None, scope=None,
           qualified_name=None, path='models/shared.py', line=1, origin='code'):
    context=dict(origin=origin,role='reference')
    for key,value in dict(model=model,module=module,scope=scope,qualified_name=qualified_name).items():
        if value is not None: context[key]=value
    return dict(name=name,type=kind,rule='synthetic_explicit_identity_v1',context=context,
                location=dict(artifact_path='capture/source.py',code_path=path,
                              content_line=line,artifact_line=line,code_line=line))


def topology(links, isolated=()):
    units={uid:[] for uid in isolated}
    for number,(left,right) in enumerate(links):
        name='link.'+str(number)
        units.setdefault(left,[]).append(entity(name,line=number+1))
        units.setdefault(right,[]).append(entity(name,line=number+1))
    return units


def collection(root, units, seeds=('A',), *, modules=None, partial_units=(), reverse=False):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    database=root/'collection.sqlite'
    units=deepcopy(units)
    for seed in seeds: units[seed].append(entity('seed.'+seed,line=100))
    metadata=dict(schema_version=4,normalization=dict(rules_version=RULE_VERSION),
                  collection_revision='synthetic-contract-revision-1',include_oca_migrations=False)
    with closing(sqlite3.connect(database)) as con, con:
        con.executescript('''CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE sources(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE information_units(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE unit_entities(unit_id TEXT,ordinal INTEGER,name TEXT,type TEXT,payload TEXT,
                PRIMARY KEY(unit_id,ordinal));
            CREATE INDEX unit_entity_lookup ON unit_entities(name,type);''')
        con.executemany('INSERT INTO metadata VALUES (?,?)',[(k,json.dumps(v)) for k,v in metadata.items()])
        rows=list(units.items())
        if reverse: rows.reverse()
        for uid,observations in rows:
            source_id='source-'+uid
            source=dict(id=source_id,binding=dict(module=(modules or {}).get(uid)))
            unit=dict(id=uid,source_id=source_id,schema_version=1,rules_version=RULE_VERSION,
                      entities=observations,normalization_status='partial' if uid in partial_units else 'valid',
                      text='COMPLETE_DOCUMENT_MUST_NOT_BE_COPIED',terms=['not_a_link'],layers=['same'],version_from='16.0')
            con.execute('INSERT INTO sources VALUES (?,?)',(source_id,json.dumps(source)))
            con.execute('INSERT INTO information_units VALUES (?,?)',(uid,json.dumps(unit)))
            indexes=list(enumerate(observations))
            if reverse: indexes.reverse()
            con.executemany('INSERT INTO unit_entities VALUES (?,?,?,?,?)',
                [(uid,i,e['name'],e['type'],json.dumps(e)) for i,e in indexes])
    partner=root/'partner';partner.mkdir()
    code=''.join('class Seed'+str(i)+':\n    _name='+repr('seed.'+seed)+'\n' for i,seed in enumerate(seeds))
    (partner/'models.py').write_text(code or 'pass\n',encoding='utf-8')
    return database,cross_module(database,partner,module_name='synthetic_partner')


def resign_crossing(report):
    from r2.selection import fingerprint
    report['result_id']='cross-'+fingerprint({k:v for k,v in report.items() if k!='result_id'})[:32]
    return report


def resign_graph(report):
    from r2.relations.engine import graph_id
    report['graph_id']=graph_id(report)
    return report


def update_metadata(database,key,value):
    with closing(sqlite3.connect(database)) as con, con:
        con.execute('UPDATE metadata SET value=? WHERE key=?',(json.dumps(value),key))
