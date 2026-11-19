"""Shared Odoo CSV observations: explicit XML IDs only, never security edges."""
import csv
import io
import re

XML_ID = re.compile(r'[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*\Z')


def extract_csv_entities(text, locator, module=None, side=None, start=1, path=None):
    entities, warnings = [], []
    if side is not None and start != 1:
        return [], ['CSV fragment has no verified file header; no identifiers inferred']
    reader = csv.reader(io.StringIO(text, newline=''), strict=True)
    try:
        header = next(reader, None)
        if not header:
            return [], ['CSV has no header']
        if len(set(header)) != len(header) or any(not name for name in header):
            return [], ['CSV header has duplicate or empty columns']
        selected = [(i,name) for i,name in enumerate(header) if name == 'id' or name.endswith(':id')]
        if not selected:
            return [], ['CSV has no explicit id or :id columns']
        previous_end = reader.line_num
        for row_number, row in enumerate(reader, 2):
            first, last = previous_end + 1, reader.line_num
            previous_end = last
            if not row:
                continue
            if len(row) != len(header):
                warnings.append(f'CSV row {row_number} lines {first}-{last}: column count differs from header')
                continue
            for index, column in selected:
                value = row[index]
                if not value:
                    continue
                if not XML_ID.fullmatch(value):
                    warnings.append(f'CSV row {row_number} column {index+1}: invalid external identifier')
                    continue
                location = dict(locator, content_line=first, content_end_line=last,
                                csv_row=row_number,csv_column=index+1,csv_column_name=column)
                if side is not None:
                    location.update(side=side,code_line=start+first-1,code_path=path)
                else:
                    location['artifact_line'] = locator['line_start']+first-1 if 'line_start' in locator else None
                    location['artifact_end_line'] = locator['line_start']+last-1 if 'line_start' in locator else None
                qualified = value if '.' in value else module+'.'+value if isinstance(module,str) and module else None
                entities.append(dict(name=value,type='external_id',location=location,
                    rule='odoo_csv_id_column_v1' if column=='id' else 'odoo_csv_reference_column_v1',
                    context=dict(origin='code',syntax='csv',module=module,
                                 role='declaration' if column=='id' else 'reference',
                                 original_value=value,column=column),
                    lookup_keys=['xmlid:'+qualified] if qualified else []))
    except csv.Error as exc:
        warnings.append(f'CSV parse error near physical line {reader.line_num}: {exc}')
    return entities, warnings
