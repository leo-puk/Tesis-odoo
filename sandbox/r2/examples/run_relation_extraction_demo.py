"""Offline synthetic example through REAL normalization, SQLite and crossing.

No network requests, no partner code execution, no claim of live Odoo evidence.
"""
import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
from r2.collection import compatibility_views,write_collection,connect,load
from r2.crossing import cross_module
from r2.normalization.units import convert_units
from r2.relations import execute_query,load_graph,to_networkx


def run(destination):
    output=Path(destination)
    if output.exists(): raise ValueError('Choose a new example output directory')
    output.mkdir(parents=True)
    links=[('A','B'),('A','C'),('B','C'),('B','D'),('C','E'),('D','F'),('E','G'),('F','G'),('G','H')]
    references={uid:[] for uid in 'ABCDEFGH'}
    references['A'].append('seed.only')
    for i,(left,right) in enumerate(links):
        references[left].append('edge.'+str(i));references[right].append('edge.'+str(i))
    captured=[]
    for label,names in references.items():
        code=''.join('self.env['+repr(name)+']\n' for name in names)
        path='capture/'+label+'.py'
        local=output/path;local.parent.mkdir(parents=True,exist_ok=True);local.write_text(code,encoding='utf-8')
        captured.append(dict(source=dict(id='session:'+label,unit_id=label,plan_source_id='synthetic',
            kind='official_code',binding={},from_version=None,to_version=None,url='https://example.invalid/'+label),
            files=[dict(path=path,text=code,raw=code.encode(),metadata={},decoding=dict(encoding='utf-8'),
                        artifact_sha256=hashlib.sha256(code.encode()).hexdigest())]))
    normalized=convert_units(captured)
    if normalized['issues']: raise AssertionError(normalized['issues'])
    elements,changes,documents=compatibility_views(normalized)
    database=output/'collection.sqlite'
    with redirect_stdout(io.StringIO()):
        write_collection(normalized['sources'],elements,{},changes,database,None,None,[],False,[],0,
            normalized['artifacts'],documents,schema=4,normalized_units=normalized['units'],normalization=normalized['normalization'])
    partner=output/'partner';partner.mkdir()
    (partner/'models.py').write_text('class Partner:\n    _name="seed.only"\n',encoding='utf-8')
    crossing_path=output/'crossing.json'
    crossing=cross_module(database,partner,module_name='synthetic_partner',output=crossing_path)
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (database,crossing_path)}
    graph=execute_query(crossing,database,output=output/'graph.json')
    restored=load_graph(output/'graph.json',database=database,crossing=crossing_path)
    assert graph==restored
    network=to_networkx(restored)
    labels={u['id']:Path(u['source_locator']['artifact_path']).stem for u in normalized['units'].values()}
    depths={labels[n['unit_id']]:n['minimum_hops'] for n in graph['nodes']}
    assert depths==dict(A=0,B=1,C=1,D=2,E=2,F=3,G=3)
    assert network.number_of_edges()==8
    assert {tuple(sorted((labels[e['left']],labels[e['right']]))) for e in graph['edges']}=={tuple(sorted(p)) for p in links[:-1]}
    predecessors = {
        labels[node['unit_id']]: sorted(labels[step['unit_id']] for step in node['predecessors'])
        for node in graph['nodes']
    }
    assert predecessors == dict(A=[], B=['A'], C=['A'], D=['B'], E=['C'], F=['D'], G=['E'])
    after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (database,crossing_path)}
    assert before==after
    with connect(database) as con: assert load(con,'relations')==[]
    report=dict(synthetic=True,network_requests=0,pipeline=['convert_units','write_collection','cross_module','extract_relations','traverse_relations','load_graph'],
        depths=dict(sorted(depths.items())), predecessors=predecessors,excluded_fourth_hop='H',counts=graph['counts'],
        original_inputs_unchanged=before==after,input_sha256=before,labels=dict(sorted(labels.items())),
        crossing_status=crossing['status'],graph_status=graph['status'],reload_verified=True)
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(run(args.output),ensure_ascii=False,indent=2))
