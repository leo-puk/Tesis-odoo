import copy
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from r2.collection import build, connect, load
from r2.extract import extract, scan_module
from r2.review import apply_reviews, search_document
from r2.query import retrieve, validate_output
from r2.selection import sample_cases, freeze_protocol, CRITERIA
from r2.evaluation_sources import GitHubMetadata
from r2.evaluation_sources.http import HttpCapture
from r2.evaluate import checked_refs, evaluate
import test_r2 as base_tests
from test_r2 import CORE_OLD, CORE_NEW, OLD, review_event


class MethodologyTests(unittest.TestCase):
    setUp = base_tests.R2Tests.setUp
    tearDown = base_tests.R2Tests.tearDown
    def test_real_temporary_git_commits_are_fixed(self):
        repo = self.root/"repo"; repo.mkdir()
        def git(*args):
            return subprocess.check_output(["git", "-C", str(repo), *args], text=True, stderr=subprocess.DEVNULL).strip()
        git("init")
        (repo/"fields.py").write_text(CORE_OLD)
        git("add", "fields.py")
        git("-c", "user.name=synthetic-test", "-c", "user.email=fixture@example.invalid", "commit", "-m", "before")
        old = git("rev-parse", "HEAD")
        (repo/"fields.py").write_text(CORE_NEW)
        git("add", "fields.py")
        git("-c", "user.name=synthetic-test", "-c", "user.email=fixture@example.invalid", "commit", "-m", "after")
        new = git("rev-parse", "HEAD")
        self.manifest.write_text(json.dumps([{**self.records[0], "format":"git", "repo":str(repo), "from_revision":old,"to_revision":new}]))
        build(self.manifest, self.db)
        with connect(self.db) as con:
            source = load(con,"sources")[0]
            self.assertEqual(source["from_revision"],old)
            self.assertEqual(source["to_revision"],new)

    def test_xml_ids_roles_qweb_groups_and_security(self):
        xml = '''<odoo><template id="card" inherit_id="base.card"><t t-call="other" groups="group_local,base.group_user"/></template>
        <record id="rule" model="ir.rule"><field name="groups" eval="[(4,ref('group_local'))]"/></record></odoo>'''
        a,b = extract(xml,"views.xml","addon_a"),extract(xml,"views.xml","addon_b")
        self.assertIn("xmlid:addon_a.card", {e["key"] for e in a["elements"] if e["role"]=="declaration"})
        self.assertNotIn("xmlid:addon_a.card", {e["key"] for e in b["elements"]})
        triples={(e["source"],e["target"],e["kind"]) for e in a["relations"]}
        self.assertIn(("xmlid:addon_a.card","xmlid:addon_a.other","qweb_call"),triples)
        self.assertIn(("xmlid:addon_a.card","xmlid:base.card","inherits_or_references"),triples)
        self.assertIn(("xmlid:addon_a.card","xmlid:addon_a.group_local","requires_group"),triples)
        csv=extract("id,model_id:id,group_id:id\naccess_x,model_x,base.group_user\n","security/ir.model.access.csv","addon_a")
        self.assertIn("xmlid:base.group_user",{e["target"] for e in csv["relations"]})

    def test_self_attribute_is_not_automatically_a_method(self):
        data=extract('''from odoo import models,fields
class A(models.Model):
    _name="a.model"
    amount=fields.Float()
    def target(self): return 1
    def go(self): return self.amount+self.target()+self.unknown
''',"models/a.py","addon")
        targets={r["target"] for r in data["relations"] if r["kind"]=="self_reference"}
        self.assertIn("field:a.model.amount",targets)
        self.assertIn("method:a.model.target",targets)
        self.assertIn("unresolved:a.model.unknown",targets)
        self.assertNotIn("method:a.model.amount",targets)

    def test_xml_validator_rule_generalizes_beyond_pilot_names(self):
        data=extract('''class Validator:
    def check(self, arch):
        return arch.xpath("//*[@legacy_flag]")
''',"validator.py","core")
        self.assertIn("xml-attribute:legacy_flag", {e["key"] for e in data["elements"]})

    def test_many_changes_can_share_one_evidence(self):
        build(self.manifest,self.db)
        with connect(self.db) as con:
            original=load(con,"changes")[0]
        changes,evidence=apply_reviews({original["id"]:original}, [review_event(original,semantic_id=s,title=s,affected_elements=["property:states"]) for s in ("first","second")])
        reviewed=[c for c in changes.values() if c["status"]=="verified"]
        self.assertEqual(len(reviewed),2)
        self.assertEqual(reviewed[0]["evidence_ids"],reviewed[1]["evidence_ids"])
        self.assertEqual(len(evidence),1)

    def test_review_history_keeps_current_primary_evidence_consistent(self):
        build(self.manifest,self.db)
        with connect(self.db) as con:first=load(con,"changes")[0]
        second={**first,"id":"chg-synthetic-second","source_id":"synthetic-other-source", "file_path":"other.py"}
        changes,_=apply_reviews({first["id"]:first,second["id"]:second},[
            review_event(first,semantic_id="same-change"),review_event(second,semantic_id="same-change")])
        current=next(c for c in changes.values() if c["id"].startswith("sem-"))
        self.assertEqual(current["source_id"],"synthetic-other-source")
        self.assertEqual(current["file_path"],"other.py")
        self.assertEqual(len(current["review_history"]),2)

    def test_verified_requires_jump_validity_and_conditions(self):
        build(self.manifest,self.db)
        with connect(self.db) as con: c=load(con,"changes")[0]
        bad=review_event(c); bad["destination_validity"]["to_version"]="19.0"
        with self.assertRaises(ValueError): apply_reviews({c["id"]:c},[bad])
        bad=review_event(c); bad.pop("general_applicability")
        with self.assertRaises(ValueError): apply_reviews({c["id"]:c},[bad])

    def test_bm25_whitelist_excludes_admin_fields(self):
        build(self.manifest,self.db)
        with connect(self.db) as con: c=load(con,"changes")[0]
        c["source_id"]="secret-administrative-marker"; c["reviewer"]="do-not-index-reviewer"
        text=search_document(c)
        self.assertNotIn("secret-administrative-marker",text)
        self.assertNotIn("do-not-index-reviewer",text)
        self.assertIn("states is no longer supported",text)

    def test_original_and_normalized_byte_hashes_are_distinct(self):
        (self.root/"before"/"fields.py").write_bytes(CORE_OLD.replace("\n","\r\n").encode())
        build(self.manifest,self.db)
        with connect(self.db) as con: source=load(con,"sources")[0]
        self.assertNotEqual(source["original_byte_hashes"]["before"]["fields.py"],source["file_hashes"]["before"]["fields.py"])

    def test_excluded_content_is_not_opened(self):
        self.records[0].update(split="evaluation_reference",before_dir="not-present",after_dir="not-present")
        self.manifest.write_text(json.dumps(self.records))
        with patch("r2.collection.read_source",side_effect=AssertionError("reserved source read")):
            build(self.manifest,self.db)
        with connect(self.db) as con: self.assertEqual(load(con,"changes"),[])

    def test_assignment_registry_blocks_reserved_derivatives_before_read(self):
        parent={**self.records[0],"case_id":"OCA/repo#1","before_dir":"absent","after_dir":"absent"}
        child={**self.records[0],"id":"derived","kind":"derived","parent_ids":["core"],"before_dir":"absent","after_dir":"absent"}
        self.manifest.write_text(json.dumps([parent,child]))
        registry=self.root/"registry.json"
        registry.write_text(json.dumps(dict(reserved_cases=["OCA/repo#1"],assignments={
            "derived":dict(split="construction",reason="fixture provenance",evidence=["synthetic"])})))
        with patch("r2.collection.read_source",side_effect=AssertionError("reserved content read")):
            build(self.manifest,self.db,assignment_registry=registry)
        with connect(self.db) as con:self.assertEqual(load(con,"sources"),[])

    def test_multiple_edge_evidences_and_minimum_depth(self):
        old='''class A:
    _name="x.a"
    def target(self): return 1
    def caller(self): return self.target()
'''
        for name in ("one.py","two.py"):
            (self.root/"before"/name).write_text(old)
            (self.root/"after"/name).write_text(old.replace("return 1","return 2"))
        (self.root/"module"/"fields.py").write_text('''class Extension:
    _inherit="x.a"
    def ext(self): return self.caller()
''')
        build(self.manifest,self.db)
        result=retrieve(self.db,self.root/"module","16.0","17.0")
        matches=[r for r in result["results"] if r["path"] and r["path"][-1]=="method:x.a.target"]
        self.assertTrue(matches)
        self.assertEqual(matches[0]["depth"],1)
        self.assertGreaterEqual(len(matches[0]["relation_evidence"][0]["evidences"]),2)
        corrupted=copy.deepcopy(result); corrupted["results"][0]["to_version"]="19.0"
        self.assertFalse(validate_output(corrupted)["conformant"])

    def test_three_consecutive_jumps_are_separate(self):
        self.records=[{**self.records[0],"id":str(n),"from_version":f"{n}.0","to_version":f"{n+1}.0"} for n in (16,17,18)]
        self.manifest.write_text(json.dumps(self.records)); build(self.manifest,self.db)
        for n in (16,17,18):
            result=retrieve(self.db,self.root/"module",f"{n}.0",f"{n+1}.0")
            self.assertTrue(result["results"])
            self.assertEqual({c["from_version"] for c in result["results"]},{f"{n}.0"})

    def test_invalid_evaluator_correspondences(self):
        build(self.manifest,self.db)
        with connect(self.db) as con: c=load(con,"changes")[0]
        changes,_=apply_reviews({c["id"]:c},[review_event(c,affected_elements=["property:states"])])
        ref=dict(id="r",module_id="module",from_version="16.0",to_version="18.0",element="property:states",justification="fixture",covered_by=[c["id"]])
        with self.assertRaises(ValueError): checked_refs({"references":[ref]},changes)
        ref["to_version"]="17.0"; ref["element"]="field:wrong.name"
        with self.assertRaises(ValueError): checked_refs({"references":[ref]},changes)

    def test_format_difference_is_not_automatically_verified(self):
        (self.root/"before"/"fields.py").write_text("x = 1\n")
        (self.root/"after"/"fields.py").write_text("x=1\n")
        build(self.manifest,self.db)
        with connect(self.db) as con:
            changes=load(con,"changes")
        self.assertTrue(changes)
        self.assertEqual(changes[0]["status"],"candidate")
        self.assertIn("whitespace",changes[0]["classification"])


class SamplingTests(unittest.TestCase):
    def test_fixed_seed_selection_replacements_and_unknown_stop(self):
        candidates=[]
        for n in (17,18,19):
            for i in range(12):
                candidates.append(dict(case_id=f"repo#{n*100+i}",number=n*100+i,repository="OCA/repo",module=f"m{n}_{i}",
                    author="author",published_at="2026-01-01T00:00:00Z",from_version=f"{n-1}.0",to_version=f"{n}.0",
                    criteria={k:dict(status="pass",evidence="synthetic test evidence",reviewer="synthetic fixture reviewer",
                            maintainer="other",maintainer_identity_evidence="synthetic maintainer fixture") for k in CRITERIA}))
        spec=dict(seed=2026,cutoff=dict(date="2025-08-01T00:00:00Z",status="confirmed"),candidates=candidates,frame_evidence="synthetic")
        self.assertEqual(sample_cases(spec),sample_cases(spec)); self.assertTrue(sample_cases(spec)["complete"])
        first=sample_cases(spec)["orders"]["17.0"][0]
        next(c for c in candidates if c["case_id"]==first)["criteria"]={}
        result=sample_cases(spec)
        self.assertFalse(result["complete"])
        self.assertEqual(len([c for c in result["selected"] if c["to_version"]=="17.0"]),0)

    def test_freeze_refuses_missing_independent_cases(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): freeze_protocol({},"collection",Path(d)/"freeze.json",{})


class HttpTests(unittest.TestCase):
    def test_pagination_projection_and_no_token_in_archive(self):
        class Response:
            def __init__(self,value,headers): self.data=json.dumps(value).encode(); self.headers=headers
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self): return self.data
        with tempfile.TemporaryDirectory() as d:
            responses=iter([Response([{"id":1,"body":"solution must not persist"}],{"Link":'<https://api.github.com/page2>; rel="next"'}),Response([{"id":2}],{})])
            client=GitHubMetadata(d,lambda *args,**kwargs: next(responses))
            with patch.dict(os.environ,{"GH_TOKEN":"SYNTHETIC_TEST_SECRET"}):
                rows=list(client.pages("/page1",lambda xs:[{"id":x["id"]} for x in xs]))
            self.assertEqual(len(rows),2)
            data="".join(p.read_text() for p in Path(d).glob("*.json"))
            self.assertNotIn("SYNTHETIC_TEST_SECRET",data); self.assertNotIn("solution must not persist",data)

    def test_search_rejects_incomplete_population(self):
        class Response:
            headers={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self):return json.dumps(dict(total_count=1001,items=[])).encode()
        with tempfile.TemporaryDirectory() as d:
            client=GitHubMetadata(d,lambda *a,**k:Response())
            with self.assertRaises(ValueError):client.search("org:OCA is:pr")
