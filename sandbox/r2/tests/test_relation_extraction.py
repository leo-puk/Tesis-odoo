"""G01-G12 acceptance and adversarial regression tests for per-search unit graphs."""
from contextlib import closing, contextmanager, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from r2.crossing import save_result
from r2.relations import extract_relations, execute_query,validate_graph,save_graph,load_graph,to_networkx
from r2.relations.engine import graph_counts
from r2.relations.rules import RULE_VERSION,rule_catalog
from relation_fixtures import entity,topology,collection,resign_crossing,resign_graph,update_metadata


class UnitRelationsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.sequence=0

    def fixture(self,units,**kwargs):
        self.sequence+=1
        return collection(self.root/str(self.sequence),units,**kwargs)

    def chain(self):
        return self.fixture(topology([('A','B'),('B','C'),('C','D'),('D','E')]))

    def pairs(self,graph):
        return {(e['left'],e['right']) for e in graph['edges']}

    def test_G01_real_crossing_handoff_and_all_seed_ids_are_validated(self):
        db,crossing=self.chain()
        self.assertEqual(crossing['status'],'complete')
        self.assertEqual(execute_query(crossing,db)['seeds'],['A'])
        bad=deepcopy(crossing);bad['matched_unit_ids']=['missing'];bad['results'][0]['information_unit_id']='missing'
        for evidence in bad['results'][0]['evidences']: evidence['information_unit_id']='missing'
        resign_crossing(bad)
        with self.assertRaisesRegex(ValueError,'not found'): execute_query(bad,db)
        bad=deepcopy(crossing);bad['schema_version']=1
        with self.assertRaises(ValueError): execute_query(bad,db)
        bad=deepcopy(crossing);bad['result_id']='forged'
        with self.assertRaises(ValueError): execute_query(bad,db)
        bad=deepcopy(crossing);bad['matched_unit_ids']=['A','A'];resign_crossing(bad)
        with self.assertRaises(ValueError): execute_query(bad,db)

    def test_G01_revision_normalization_and_missing_index_are_rejected(self):
        for key,value in [('collection_revision','different'),('normalization',{'rules_version':'normalization-old'}),
                          ('schema_version',3),('include_oca_migrations',True)]:
            with self.subTest(key=key):
                db,crossing=self.chain();update_metadata(db,key,value)
                with self.assertRaises(ValueError): execute_query(crossing,db)
        db,crossing=self.chain()
        with closing(sqlite3.connect(db)) as con, con: con.execute('DROP INDEX unit_entity_lookup')
        with self.assertRaisesRegex(ValueError,'index'): execute_query(crossing,db)

    def test_G01_partial_crossing_and_partial_units_are_preserved(self):
        db,crossing=self.chain()
        partial=deepcopy(crossing);partial['status']='partial';partial['input']['limitations'].append('Static analysis incomplete')
        resign_crossing(partial)
        graph=execute_query(partial,db)
        self.assertEqual(graph['status'],'partial');self.assertEqual(graph['construction_status'],'complete')
        self.assertEqual(graph['crossing']['status'],'partial')
        self.assertTrue(validate_graph(graph,database=db,crossing=partial))
        partial['status']='complete';resign_crossing(partial)
        with self.assertRaisesRegex(ValueError,'partial analysis'): execute_query(partial,db)
        db,crossing=self.fixture(topology([('A','B')]),partial_units=['B'])
        graph=execute_query(crossing,db)
        self.assertEqual(graph['status'],'partial');self.assertEqual(graph['partial_unit_ids'],['B'])

    def test_G01_empty_seeds_are_an_explicit_valid_result(self):
        db,crossing=self.fixture({'A':[]},seeds=())
        graph=execute_query(crossing,db)
        self.assertEqual(graph['outcome'],'no_seeds');self.assertEqual(graph['nodes'],[])
        self.assertEqual(graph['counts'],dict(node_count=0,relation_count=0,shared_attribute_count=0,raw_match_count=0))
        self.assertTrue(validate_graph(graph,database=db,crossing=crossing))

    def test_G02_catalog_is_exactly_the_eight_approved_versioned_families(self):
        catalog=rule_catalog()
        self.assertEqual({r['family'] for r in catalog},{'model','field','method','module','external_id','path','function','class'})
        self.assertTrue(all(r['scope'] and r['admitted_types'] and r['evidence'] and r['direction']=='undirected' for r in catalog))
        self.assertEqual(RULE_VERSION,'unit-relations-1')
        catalog[0]['scope'].append('must_not_mutate_versioned_rules')
        self.assertNotIn('must_not_mutate_versioned_rules',rule_catalog()[0]['scope'])

    def test_G03_each_family_links_only_a_complete_equal_identity(self):
        cases=[entity('res.partner'),entity('name','field',model='res.partner'),entity('write','method',model='res.partner'),
               entity('sale','module'),entity('demo.view_partner','external_id'),entity('views/form.xml','path',module='demo'),
               entity('helper','function',module='demo',scope='module',qualified_name='helper'),
               entity('Helper','class',module='demo',scope='class',qualified_name='Helper')]
        for observation in cases:
            with self.subTest(family=observation['type']):
                db,crossing=self.fixture({'A':[observation],'B':[deepcopy(observation)]})
                graph=extract_relations(crossing,db)
                self.assertEqual(self.pairs(graph),{('A','B')})
                self.assertEqual(graph['edges'][0]['shared_attribute_count'],1)

    def test_G03_homonymous_fields_methods_and_types_do_not_link(self):
        for kind in ('field','method'):
            with self.subTest(kind=kind):
                db,crossing=self.fixture({'A':[entity('same',kind,model='sale.order')],
                    'B':[entity('same',kind,model='res.partner')], 'C':[entity('same',kind)]})
                self.assertEqual(extract_relations(crossing,db)['edges'],[])
        db,crossing=self.fixture({'A':[entity('same','model')],'B':[entity('same','module')]})
        self.assertEqual(extract_relations(crossing,db)['edges'],[])

    def test_G03_functions_classes_require_module_file_and_qualified_scope(self):
        for kind,scope in [('function','module'),('class','class')]:
            original=entity('Helper',kind,module='demo',scope=scope,qualified_name='Helper')
            incompatible=[dict(module='other'),dict(path='models/other.py'),dict(qualified_name='Outer.Helper'),
                          dict(scope='local'),dict(scope='unknown')]
            for change in incompatible:
                with self.subTest(kind=kind,change=change):
                    arguments=dict(module='demo',scope=scope,qualified_name='Helper');arguments.update(change)
                    db,crossing=self.fixture({'A':[original],'B':[entity('Helper',kind,**arguments)]})
                    self.assertEqual(extract_relations(crossing,db)['edges'],[])
            db,crossing=self.fixture({'A':[original],'B':[entity('Helper',kind,scope=scope,qualified_name='Helper')]})
            self.assertEqual(extract_relations(crossing,db)['edges'],[])
            # unit_identity's explicit addon prefix convention is reused on both ends.
            db,crossing=self.fixture({'A':[original], 'B':[entity('Helper',kind,scope=scope,qualified_name='Helper',
                path='addons/demo/models/shared.py')]},modules={'B':'demo'})
            self.assertEqual(self.pairs(extract_relations(crossing,db)),{('A','B')})

    def test_G03_explicit_xml_id_namespace_and_path_owner(self):
        db,crossing=self.fixture({'A':[entity('demo.view_partner','external_id')],
            'B':[entity('view_partner','external_id')],'C':[entity('view_partner','external_id')]},modules={'B':'demo','C':'other'})
        self.assertEqual(self.pairs(extract_relations(crossing,db)),{('A','B')})
        db,crossing=self.fixture({'A':[entity('views/a.xml','path')],'B':[entity('views/a.xml','path')]},modules={'A':'one','B':'two'})
        self.assertEqual(extract_relations(crossing,db)['edges'],[])

    def test_G03_typed_documentation_can_link_but_generic_mentions_cannot(self):
        db,crossing=self.fixture({'A':[entity('name','field',model='res.partner')],
            'B':[entity('name','field_reference',model='res.partner',origin='documentation')],
            'C':[entity('name','identifier_mention',origin='documentation')],
            'D':[entity('name','field_reference',origin='documentation')]})
        self.assertEqual(self.pairs(extract_relations(crossing,db)),{('A','B')})

    def test_G03_excluded_families_and_shared_words_layer_version_never_link(self):
        for kind in ('field_path','field_option','xml_attribute','xpath_expression','manifest_key','identifier_mention'):
            with self.subTest(kind=kind):
                observation=entity('same',kind,model='res.partner',module='demo')
                db,crossing=self.fixture({'A':[observation],'B':[observation]})
                self.assertEqual(extract_relations(crossing,db)['edges'],[])
        db,crossing=self.fixture({'A':[],'B':[]})
        self.assertEqual(extract_relations(crossing,db)['edges'],[])

    def test_G04_index_used_without_top_five_or_text_scan(self):
        units={'A':[entity('shared.model')]}
        units.update({f'B{i:02}':[entity('shared.model')] for i in range(8)})
        db,crossing=self.fixture(units)
        from r2.relations import extraction
        real_connect=extraction.connect;statements=[]
        @contextmanager
        def traced(path):
            with real_connect(path) as con:
                con.set_trace_callback(statements.append)
                plan=con.execute("EXPLAIN QUERY PLAN SELECT unit_id FROM unit_entities INDEXED BY unit_entity_lookup WHERE name=? AND type IN (?)",('shared.model','model')).fetchall()
                self.assertTrue(any('SEARCH' in r[3] and 'unit_entity_lookup' in r[3] for r in plan))
                yield con
        with patch.object(extraction,'connect',traced): graph=extract_relations(crossing,db)
        self.assertEqual(len(graph['unit_ids']),9);self.assertEqual(len(graph['edges']),36)
        candidates=[s for s in statements if 'INDEXED BY unit_entity_lookup' in s and not s.startswith('EXPLAIN')]
        self.assertTrue(candidates)
        self.assertTrue(all('LIMIT' not in s.upper() and 'LIKE' not in s.upper() for s in candidates))
        self.assertFalse(any('unit_terms' in s or 'changes' in s or 'relations' in s for s in statements))
        self.assertTrue(all('WHERE id=' in s for s in statements if 'FROM information_units' in s))

    def test_G04_corrupt_or_incomplete_entity_index_is_rejected(self):
        db,crossing=self.chain()
        with closing(sqlite3.connect(db)) as con, con: con.execute("UPDATE unit_entities SET payload='{}' WHERE unit_id='B' AND ordinal=0")
        with self.assertRaisesRegex(ValueError,'index differs'): extract_relations(crossing,db)
        db,crossing=self.chain()
        with closing(sqlite3.connect(db)) as con, con: con.execute("DELETE FROM unit_entities WHERE unit_id='A' AND ordinal=0")
        with self.assertRaisesRegex(ValueError,'index is incomplete'): extract_relations(crossing,db)

    def test_G05_evidence_is_localized_on_both_sides_without_document_text(self):
        db,crossing=self.chain();graph=extract_relations(crossing,db)
        match=graph['edges'][0]['matches'][0]
        for side in ('left','right'):
            observation=match[side]['observation']
            self.assertTrue(observation['rule']);self.assertGreater(observation['location']['artifact_line'],0)
            self.assertEqual(match[side]['unit_id'],graph['edges'][0][side])
        self.assertNotIn('COMPLETE_DOCUMENT',json.dumps(graph))
        self.assertNotIn('terms',json.dumps(graph))
        for locator in ({'artifact_path':'capture/source.py'},dict(artifact_path='capture/source.py',artifact_line=-1)):
            bad=entity('link');bad['location']=locator
            db,crossing=self.fixture({'A':[bad],'B':[entity('link')]})
            with self.assertRaises(ValueError): extract_relations(crossing,db)

    def test_G06_distinct_identities_raw_pairs_and_unique_edges(self):
        a=[entity('res.partner',line=i) for i in (1,2)]
        b=[entity('res.partner',line=i) for i in (3,4,5)]
        db,crossing=self.fixture({'A':a,'B':b})
        graph=extract_relations(crossing,db);edge=graph['edges'][0]
        self.assertEqual(edge['shared_attribute_count'],1);self.assertEqual(edge['raw_match_count'],6)
        self.assertEqual(graph_counts(graph['unit_ids'],graph['edges']),dict(node_count=2,relation_count=1,shared_attribute_count=1,raw_match_count=6))
        db,crossing=self.fixture({'A':a+[entity('name','field',model='res.partner')],
                                'B':b+[entity('name','field',model='res.partner')], 'C':[entity('res.partner')]})
        graph=extract_relations(crossing,db)
        self.assertEqual(graph_counts(graph['unit_ids'],graph['edges']),dict(node_count=3,relation_count=3,shared_attribute_count=2,raw_match_count=12))
        edge=next(e for e in graph['edges'] if e['left']=='A' and e['right']=='B')
        self.assertEqual(edge['shared_attribute_count'],2);self.assertEqual(edge['raw_match_count'],7)

    def test_G07_chain_excludes_fourth_hop_and_supports_zero_through_three(self):
        db,crossing=self.chain()
        for limit in range(4):
            graph=execute_query(crossing,db,maximum_hops=limit)
            self.assertEqual({n['unit_id']:n['minimum_hops'] for n in graph['nodes']},
                             {chr(65+i):i for i in range(limit+1)})
            self.assertNotIn('E',[n['unit_id'] for n in graph['nodes']])
        for limit in (-1,4,True,1.5):
            with self.assertRaises(ValueError): execute_query(crossing,db,maximum_hops=limit)

    def test_G07_multiple_roots_use_minimum_distance_and_connect_seeds(self):
        db,crossing=self.fixture(topology([('A','B'),('B','C'),('C','D'),('D','E'),('A','E')]),seeds=('A','E'))
        graph=execute_query(crossing,db)
        self.assertEqual({n['unit_id']:n['minimum_hops'] for n in graph['nodes']},dict(A=0,B=1,C=2,D=1,E=0))
        self.assertIn(('A','E'),self.pairs(graph))
        zero=execute_query(crossing,db,maximum_hops=0)
        self.assertEqual(self.pairs(zero),{('A','E')})
        self.assertTrue(all(n['minimum_hops']==0 for n in zero['nodes']))

    def test_G08_cycles_lateral_and_third_boundary_connections_are_complete(self):
        links=[('A','B'),('A','C'),('B','C'),('B','D'),('C','E'),('D','F'),('E','G'),('F','G'),('G','H')]
        db,crossing=self.fixture(topology(links))
        graph=execute_query(crossing,db)
        self.assertEqual(self.pairs(graph),{tuple(sorted(pair)) for pair in links[:-1]})
        depths={n['unit_id']:n['minimum_hops'] for n in graph['nodes']}
        self.assertEqual(depths['F'],3);self.assertEqual(depths['G'],3);self.assertNotIn('H',depths)
        self.assertTrue(all(e['left']!=e['right'] for e in graph['edges']))
        self.assertTrue(validate_graph(graph,database=db,crossing=crossing))

    def test_G09_insertion_order_and_repeated_search_produce_identical_json(self):
        units=topology([('A','B'),('A','C'),('B','C'),('C','D')])
        db,crossing=self.fixture(units)
        db2,crossing2=self.fixture(units,reverse=True)
        # Crossing's input files have different absolute locations; the graph's
        # per-search provenance must retain them. Hold that legitimate handoff fixed.
        first=execute_query(crossing,db);second=execute_query(crossing,db2)
        self.assertEqual(first,second);self.assertEqual(first,execute_query(crossing,db))
        p=self.root/'one.json';q=self.root/'two.json'
        save_graph(first,p);save_graph(second,q)
        self.assertEqual(p.read_bytes(),q.read_bytes())
        self.assertEqual(first,load_graph(p,database=db,crossing=crossing))
        network=to_networkx(first)
        self.assertFalse(network.is_directed());self.assertEqual(network.number_of_edges(),first['counts']['relation_count'])
        self.assertEqual(network.graph['collection'],first['collection'])
        self.assertEqual(network.graph['seeds'],first['seeds'])

    def test_G10_tampered_counts_evidence_distances_and_endpoints_are_rejected(self):
        db,crossing=self.chain();original=execute_query(crossing,db)
        def falsify_count(g): g['counts']['raw_match_count']+=1
        def drop_evidence(g): g['edges'][0]['matches']=[]
        def false_depth(g): g['nodes'][1]['minimum_hops']=0
        def missing_step(g): g['nodes'][1]['predecessors']=[]
        def absent_endpoint(g): g['edges'][0]['right']='missing'
        def self_loop(g): g['edges'][0]['right']=g['edges'][0]['left']
        def partial_loss(g): g['crossing']['status']='partial'
        for mutation in (falsify_count,drop_evidence,false_depth,missing_step,absent_endpoint,self_loop,partial_loss):
            with self.subTest(mutation=mutation.__name__):
                graph=deepcopy(original);mutation(graph);resign_graph(graph)
                with self.assertRaises(ValueError): validate_graph(graph)

    def test_G10_replay_detects_omitted_lateral_edges_even_with_resigned_counts(self):
        db,crossing=self.fixture(topology([('A','B'),('A','C'),('B','C')]))
        graph=execute_query(crossing,db)
        graph['edges']=[e for e in graph['edges'] if (e['left'],e['right'])!=('B','C')]
        graph['counts']=graph_counts(graph['nodes'],graph['edges']);resign_graph(graph)
        self.assertTrue(validate_graph(graph))  # No corpus present: structural only.
        with self.assertRaisesRegex(ValueError,'incomplete'): validate_graph(graph,database=db,crossing=crossing)
        graph=execute_query(crossing,db);update_metadata(db,'collection_revision','stale')
        with self.assertRaisesRegex(ValueError,'revision'): validate_graph(graph,database=db)

    def test_G10_replay_detects_deleted_reachable_nodes(self):
        db,crossing=self.chain();graph=execute_query(crossing,db)
        graph['nodes']=[n for n in graph['nodes'] if n['unit_id']!='D']
        graph['edges']=[e for e in graph['edges'] if e['right']!='D']
        graph['counts']=graph_counts(graph['nodes'],graph['edges']);resign_graph(graph)
        self.assertTrue(validate_graph(graph))
        with self.assertRaisesRegex(ValueError,'incomplete'): validate_graph(graph,database=db)

    def test_G10_verified_reload_rejects_forged_observation_locations(self):
        from r2.selection import fingerprint
        db,crossing=self.fixture(topology([('A','B')]))
        graph=execute_query(crossing,db)
        match=graph['edges'][0]['matches'][0]
        match['left']['observation']['location']['artifact_line']=99999
        match['id']='unit-match-'+fingerprint([RULE_VERSION,{k:v for k,v in match.items() if k!='id'}])[:32]
        resign_graph(graph)
        self.assertTrue(validate_graph(graph))
        path=self.root/'forged-location.json';save_graph(graph,path)
        with self.assertRaisesRegex(ValueError,'differs'): load_graph(path,database=db,crossing=crossing)

    def test_G10_wrong_crossing_search_and_incomplete_construction_are_rejected(self):
        db,crossing=self.chain();graph=execute_query(crossing,db)
        other=deepcopy(crossing);other['input']['module_name']='another_search';resign_crossing(other)
        with self.assertRaisesRegex(ValueError,'supplied crossing'): validate_graph(graph,crossing=other)
        graph['construction_status']='incomplete';resign_graph(graph)
        with self.assertRaisesRegex(ValueError,'Incomplete'): validate_graph(graph)

    def test_G11_inputs_unchanged_no_partner_reanalysis_and_no_overwrite(self):
        db,crossing=self.chain();original=deepcopy(crossing)
        path=self.root/'crossing.json';save_result(crossing,path)
        before={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (db,path)}
        with patch('r2.crossing.engine.read_code',side_effect=AssertionError('partner code reread')):
            graph=execute_query(path,db,output=self.root/'graph.json')
        self.assertEqual(crossing,original)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (db,path)})
        for destination in (db,path,self.root/'graph.json'):
            with self.assertRaises(FileExistsError): save_graph(graph,destination)
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in (db,path)})

    def test_G11_proposed_cli_creates_only_a_separate_search_graph(self):
        from r2.cli import main
        db,crossing=self.chain();path=self.root/'crossing.json';save_result(crossing,path)
        destination=self.root/'cli-graph.json'
        from r2.relations import engine
        calls = []
        extract = engine.extract_relations
        traverse = engine.traverse_relations

        def capture_extraction(*args, **kwargs):
            extracted = extract(*args, **kwargs)
            calls.append(('extract', extracted))
            return extracted

        def capture_traversal(extracted):
            self.assertIs(calls[0][1], extracted)
            calls.append(('traverse', extracted))
            return traverse(extracted)

        with (patch.object(engine, 'extract_relations', capture_extraction),
              patch.object(engine, 'traverse_relations', capture_traversal),
              redirect_stdout(io.StringIO())):
            main(['extract-relations', str(path), '--db', str(db), '--max-hops', '3',
                  '--output', str(destination)])
        self.assertEqual([name for name, _ in calls], ['extract', 'traverse'])
        report = load_graph(destination, database=db, crossing=crossing)
        self.assertEqual(report['edges'], calls[0][1]['edges'])
        self.assertEqual(report['nodes'][1]['predecessors'],
                         [dict(unit_id='A', edge_id=report['edges'][0]['id'])])

    def test_G12_no_directed_dependency_or_inferred_roles(self):
        db,crossing=self.chain();graph=execute_query(crossing,db)
        self.assertTrue(all(e['type']=='shares_technical_identity' and e['directed'] is False for e in graph['edges']))
        self.assertNotIn('inherits_view',{r['id'] for r in graph['rule_catalog']})
        self.assertNotIn('references_xml_id',{r['id'] for r in graph['rule_catalog']})


if __name__=='__main__': unittest.main()
