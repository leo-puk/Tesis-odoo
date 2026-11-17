import copy
import unittest
from audit.prepare_review_packets import packet
from r2.selection import CRITERIA


class ReviewPacketTests(unittest.TestCase):
    def fixture(self):
        case = dict(case_id="OCA/x#1", module=None, criteria={k:dict(status="pending",evidence=None,reviewer=None) for k in CRITERIA})
        metadata = dict(case_id=case["case_id"], pull=dict(author="author",merged_at="date",base=dict(ref="19.0"),
            head=dict(sha="head"),merge_commit_sha="merge"), files=[dict(filename="addon/__manifest__.py")],
            extracted_at="date",captures=[],reviews=[dict(id=1,reviewer="other",state="APPROVED",commit_id="old",submitted_at="2026-01-01"),
            dict(id=2,reviewer="other",state="APPROVED",commit_id="head",submitted_at="2026-01-02")])
        return case, metadata

    def test_metadata_does_not_mark_six_criteria_as_passed(self):
        case, metadata = self.fixture()
        result=packet(case,metadata)
        self.assertEqual(result["module"],"addon")
        self.assertEqual(len(result["metadata_observations"]["independent_head_approvals"]),1)
        self.assertTrue(all(c["status"]=="pending" for c in result["criteria"].values()))
        self.assertIsNone(case["module"])

    def test_dismissed_approval_and_multiple_modules_are_not_inferred(self):
        case, metadata = self.fixture()
        metadata["files"].append(dict(filename="other/__manifest__.py"))
        metadata["reviews"].append(dict(id=3,reviewer="other",state="DISMISSED",commit_id="head",submitted_at="2026-01-03"))
        result=packet(case,metadata)
        self.assertIsNone(result["module"])
        self.assertEqual(result["metadata_observations"]["independent_head_approvals"],[])

    def test_existing_review_decisions_are_preserved(self):
        case,metadata=self.fixture()
        case["criteria"]["single_module"]={"status":"fail","evidence":"synthetic prior review","reviewer":"synthetic fixture"}
        self.assertEqual(packet(case,metadata)["criteria"]["single_module"],case["criteria"]["single_module"])
