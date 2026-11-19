"""Reproduce positive and negative exact crossing with synthetic HTTP captures."""
import argparse
import json
from pathlib import Path
from examples.run_normalization_demo import run as normalize_demo
from r2.crossing import cross_module


def run(output):
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a new crossing demo directory')
    output.mkdir(parents=True)
    normalized = normalize_demo(output/'normalized')
    database = output/'normalized/collection.sqlite'
    positive, negative = output/'partner', output/'unrelated'
    positive.mkdir(); negative.mkdir()
    (positive/'model.py').write_text(
        'class Partner:\n    _name="res.partner"\n    name=fields.Char(related="partner_id.name")\n',encoding='utf-8')
    (positive/'__manifest__.py').write_text("{'name':'Crossing fixture','depends':['base']}\n",encoding='utf-8')
    (negative/'model.py').write_text('class Other:\n    _name="x.unrelated"\n    name=fields.Char()\n',encoding='utf-8')
    matched = cross_module(database,positive,module_name='demo',output=output/'matches.json')
    absent = cross_module(database,negative,module_name='unrelated',output=output/'no-matches.json')
    assert matched == cross_module(database,positive,module_name='demo')
    assert matched['summary']['units_matched'] == 3
    assert absent['results'] == [] and absent['outcome'] == 'no_matches'
    report = dict(synthetic=True,http='mocked; no live upstream claims',
                  normalized_units=normalized['unit_count'],matched_units=matched['summary']['units_matched'],
                  negative_units=absent['summary']['units_matched'],reprocessing_identical=True,
                  matched_result_id=matched['result_id'],negative_result_id=absent['result_id'])
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(run(parser.parse_args().output),ensure_ascii=False,indent=2))
