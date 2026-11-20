from __future__ import annotations

import ast
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'sandbox/control'))
from odoolab import experiment as ex, migration_plan as plan, batch


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = ROOT / 'sandbox/research/migration-plan/plan.json'
        cls.data = plan.load(cls.path)

    def test_exact_32_cases_2_historical_and_30_new(self):
        self.assertEqual(len(self.data['groups']), 32)
        self.assertEqual(len(plan.selected(self.data, new_only=True)), 30)
        self.assertEqual({g['id'] for g in self.data['groups'][:2]}, {'g01', 'g02'})

    def test_legacy_metadata_addons_unchanged(self):
        for case in self.data['groups'][:2]:
            metadata = json.loads((ROOT / f"sandbox/research/experiments/{case['id']}/meta.json").read_text())
            plan.assert_metadata(case, metadata)

    def test_50_distinct_new_addons_5_per_variant(self):
        first_steps = [g for g in self.data['groups'][2:] if g['version_from'] == '16.0']
        self.assertEqual(len({m['module'] for c in first_steps for m in c['modules']}), 50)

    def test_id_encodes_variant_and_step(self):
        self.assertEqual(self.data['groups'][2]['id'], 'oca_v01_1617')
        self.assertEqual(self.data['groups'][-1]['id'], 'oca_v10_1819')

    def test_reject_addon_drift_between_steps(self):
        data = deepcopy(self.data)
        data['groups'][3]['modules'] = deepcopy(data['groups'][3]['modules'])
        data['groups'][3]['modules'][0]['module'] = 'different_addon'
        with self.assertRaisesRegex(ValueError, 'cambian'):
            plan.validate(data)

    def test_reject_duplicate_id(self):
        data = deepcopy(self.data)
        data['groups'][3]['id'] = data['groups'][2]['id']
        with self.assertRaisesRegex(ValueError, 'repetido'):
            plan.validate(data)

    def test_reject_duplicate_module(self):
        data = deepcopy(self.data)
        data['groups'][0]['modules'][1] = data['groups'][0]['modules'][0]
        with self.assertRaisesRegex(ValueError, 'cinco'):
            plan.validate(data)

    def test_reject_unknown_case_instead_of_running_nothing(self):
        with self.assertRaisesRegex(ValueError, 'desconocidos'):
            plan.selected(self.data, ['typo'])

    def test_reject_nonadjacent_steps_and_traversal_ids(self):
        for pair in [('16.0', '18.0'), ('18.0', '20.0'), ('15.0', '16.0')]:
            with self.assertRaises(ValueError):
                ex.validate_step(*pair)
        with self.assertRaises(ValueError):
            ex.validate_gid('../g01')

    def test_metadata_selects_each_version_without_global_mutation(self):
        cases = self.data['groups']
        def metadata(gid):
            c = next(c for c in cases if c['id'] == gid)
            return {'step': f"{c['version_from']}->{c['version_to']}"}
        with patch.object(ex, 'meta', side_effect=metadata):
            with ThreadPoolExecutor(max_workers=4) as pool:
                pairs = list(pool.map(ex.versions_of, [c['id'] for c in cases]))
        self.assertEqual(pairs[0], ('16.0', '17.0'))
        self.assertEqual(pairs[-1], ('18.0', '19.0'))
        self.assertEqual((ex.SRC, ex.DST), ('16.0', '17.0'))

    def test_reject_metadata_version_conflict(self):
        with patch.object(ex, 'meta', return_value={'step': '18.0->19.0', 'version_from': '16.0'}):
            with self.assertRaisesRegex(ValueError, 'inconsistentes'):
                ex.versions_of('oca_v01_1819')

    def test_reject_ambiguous_repository_for_addon(self):
        with self.assertRaisesRegex(ValueError, 'ambiguo'):
            ex.dependency_index([{'repo': 'a', 'module': 'same'}, {'repo': 'b', 'module': 'same'}])

    def test_prepare_keeps_existing_evidence(self):
        case = self.data['groups'][0]
        with patch.object(ex, '_root', return_value=ROOT / 'sandbox'), patch.object(ex, 'prepare') as prepare:
            result = plan.prepare_case(case)
        self.assertEqual(result['id'], 'g01')
        prepare.assert_not_called()

    def test_prepare_passes_versions_and_does_not_use_force_by_default(self):
        case = self.data['groups'][-1]
        with tempfile.TemporaryDirectory() as temp, patch.object(ex, '_root', return_value=Path(temp)), \
             patch.object(ex, 'prepare', return_value={}) as prepare:
            plan.prepare_case(case)
            self.assertEqual(prepare.call_args.kwargs, {'force': False, 'source': '18.0', 'target': '19.0'})

    def test_source_validation_failure_cannot_reach_prepare(self):
        case = self.data['groups'][-1]
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'plan.json'
            p.write_text(json.dumps(self.data))
            with patch.object(plan, 'check_sources', side_effect=ValueError('missing addon')), \
                 patch.object(plan, 'prepare_case') as prepare:
                result = plan.run(p, [case['id']])
            prepare.assert_not_called()
            self.assertEqual(result[0]['status'], 'blocked')
            self.assertIn('missing addon', result[0]['reason'])

    def test_run_marks_failed_phase_as_failed_not_ok(self):
        case = self.data['groups'][-1]
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'plan.json'
            p.write_text(json.dumps(self.data))
            with patch.object(plan, 'check_sources'), patch.object(plan, 'prepare_case'), \
                 patch.object(ex, 'seed'), patch.object(ex, 'baseline'), patch.object(ex, 'report'), \
                 patch.object(ex, 'auto', return_value={'install': 'max_iter'}):
                result = plan.run(p, [case['id']], phases=['install'])
            self.assertEqual(result[0]['status'], 'failed')
            self.assertEqual(json.loads(p.read_text()), self.data)

    def test_run_default_leaves_historical_cases_out(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / 'plan.json'
            p.write_text(json.dumps(self.data))
            with patch.object(plan, 'check_sources', side_effect=ValueError('pending')):
                results = plan.run(p)
            self.assertEqual(len(results), 30)
            self.assertFalse({'g01', 'g02'} & {r['id'] for r in results})

    def test_legacy_batch_dispatches_new_schema_without_replacements(self):
        with patch.object(plan, 'run', return_value=['dispatched']) as run:
            result = batch.run(self.path, parallel=1, only=['oca_v01_1617'])
        self.assertEqual(result, ['dispatched'])
        self.assertEqual(run.call_args.args[1], ['oca_v01_1617'])

    def test_legacy_batch_rejects_unsafe_multiversion_parallel_dispatch(self):
        with self.assertRaisesRegex(ValueError, 'parallel 1'):
            batch.run(self.path, parallel=2)

    def test_cli_checks_plan_without_odoo_or_network(self):
        self.assertEqual(plan.main(['check', '--plan', str(self.path)]), 0)
        self.assertEqual(plan.main(['prepare', '--plan', str(self.path)]), 1)

    def test_source_and_target_dependency_closure(self):
        rows = {'d': 'repo-d', 'old_dep': 'repo-old', 'new_dep': 'repo-new'}
        def manifest(gd, version, module):
            return {'depends': ['old_dep'] if module == 'd' and version == '17.0'
                    else ['new_dep'] if module == 'd' else []}
        with patch.object(ex.census, 'sync_repo', return_value=Path('.')), patch.object(ex, 'manifest', side_effect=manifest):
            deps = ex._resolve_oca_deps(['d'], rows, set(), source='17.0', target='18.0')
        self.assertEqual(set(deps), {'d', 'old_dep', 'new_dep'})
        self.assertEqual(deps[-1], 'd')

    def test_python_sources_compile(self):
        for path in (ROOT / 'sandbox/control/odoolab').glob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'), filename=str(path))


if __name__ == '__main__':
    unittest.main()

