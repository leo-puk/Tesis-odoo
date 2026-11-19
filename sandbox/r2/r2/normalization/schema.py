"""Explicit normalized-unit contract and deterministic identity (no graph)."""
import math
import re
import base64
import binascii
from pathlib import PurePosixPath
from lxml.etree import LxmlError
from ..selection import fingerprint
from .decoding import decode_artifact
from .observations import part_entities
from .parsers import parse_artifact

SCHEMA_VERSION = 1
RULE_VERSION = "normalization-3"
FIELDS = {"id", "source_id", "source_url", "source_locator", "kind", "text",
          "version_from", "version_to", "layers", "entities", "terms",
          "extraction_rule", "schema_version", "warnings"}
KINDS = {"diff_hunk", "markdown_section", "text", "manifest", "pr_description",
         "pr_comment", "pr_review", "pr_review_comment", "pr_commit", "code", "html_document", "rst_section"}
LAYERS = {"python", "xml", "data", "manifest", "documentation", "unknown"}


def unit_id(source_id, locator, rule):
    return "unit-" + fingerprint([source_id, locator, rule, SCHEMA_VERSION, RULE_VERSION])[:32]


def validate_units(units):
    seen = set()
    for unit in units:
        missing = FIELDS - unit.keys()
        if missing:
            raise ValueError("Normalized unit missing fields: " + ", ".join(sorted(missing)))
        if unit["schema_version"] != SCHEMA_VERSION or unit["kind"] not in KINDS:
            raise ValueError("Unknown unit schema or kind")
        for key in ("id", "source_id", "text", "extraction_rule"):
            if not isinstance(unit[key], str) or (key != "text" and not unit[key]):
                raise ValueError("Invalid unit field: " + key)
        if unit["id"] in seen:
            raise ValueError("Duplicate normalized unit ID")
        seen.add(unit["id"])
        if unit["id"] != unit_id(unit["source_id"], unit["source_locator"], unit["extraction_rule"]):
            raise ValueError("Unit ID does not match source, locator and rules")
        if unit["source_url"] is not None and not isinstance(unit["source_url"], str):
            raise ValueError("source_url must be a string or null")
        for key in ("version_from", "version_to"):
            if unit[key] is not None and (not isinstance(unit[key], str) or not re.fullmatch(r'\d+\.\d+',unit[key])):
                raise ValueError("Unknown versions must be null")
        locator = unit["source_locator"]
        if not isinstance(locator, dict) or not isinstance(locator.get("artifact_path"), str):
            raise ValueError("A locator must identify the captured artifact")
        path = PurePosixPath(locator["artifact_path"])
        if path.is_absolute() or ".." in path.parts or "\\" in str(path) or ":" in str(path):
            raise ValueError("Unsafe artifact locator")
        if "json_pointer" in locator and not isinstance(locator["json_pointer"], str):
            raise ValueError("JSON pointer must be text")
        if "line_start" in locator or "line_end" in locator:
            first, last = locator.get("line_start"), locator.get("line_end")
            if type(first) is not int or type(last) is not int or not 1 <= first <= last:
                raise ValueError("Invalid locator line range")
        if not isinstance(unit["layers"], list) or not unit["layers"] or not set(unit["layers"]) <= LAYERS:
            raise ValueError("Invalid layers; use unknown explicitly")
        if not isinstance(unit["warnings"], list) or not all(isinstance(w, str) for w in unit["warnings"]):
            raise ValueError("warnings must contain strings")
        if unit.get('normalization_status') not in {'valid','partial'}:
            raise ValueError('A failed normalization cannot be presented as a valid unit')
        if not isinstance(unit["entities"], list) or not isinstance(unit["terms"], list):
            raise ValueError("entities and terms must be lists")
        for entity in unit["entities"]:
            if not isinstance(entity, dict) or not {"name", "type", "location", "rule", "context"} <= entity.keys():
                raise ValueError("Entity lacks provenance or recognition rule")
            if not all(isinstance(entity[k], str) and entity[k] for k in ("name", "type", "rule")):
                raise ValueError("Invalid entity name, type or rule")
            if not isinstance(entity["location"], dict) or not isinstance(entity["context"], dict):
                raise ValueError("Entity location and context must be objects")
            if entity['context'].get('origin') not in {'code','documentation','comment'}:
                raise ValueError('Entities must distinguish code, documentation and comments')
            if entity["location"].get("artifact_path") != locator["artifact_path"]:
                raise ValueError("Entity points outside its source artifact")
            for coordinate in ('content_line', 'artifact_line', 'code_line', 'line_start', 'line_end'):
                if coordinate not in entity['location']:
                    continue
                value = entity['location'][coordinate]
                if coordinate == 'artifact_line' and value is None:
                    continue  # HTML/JSON content has no asserted artifact line.
                if type(value) is not int or value < 1:
                    raise ValueError('Entity coordinates must be positive integers')
        terms = []
        for term in unit["terms"]:
            if not isinstance(term.get("term"), str) or type(term.get("frequency")) is not int or term["frequency"] <= 0:
                raise ValueError("Invalid term or frequency")
            if not isinstance(term.get("tfidf"), (int, float)) or not math.isfinite(term["tfidf"]) or term["tfidf"] < 0:
                raise ValueError("Invalid TF-IDF weight")
            terms.append(term["term"])
        if terms != sorted(set(terms)):
            raise ValueError("Terms must be unique and sorted")
        if any(k in unit for k in ("relations", "edges", "neighbors", "graph")):
            raise ValueError("Normalization must not create search relationships")
    return True


def validate_collection(collection):
    """Verify content, format data and entity evidence against retained sources.

    Reparse each referenced artifact once. Canonical parts preserve the actual
    format transformations (HTML text, JSON strings, CRLF diff handling and
    no-newline markers); a raw substring check would reject valid evidence.
    This verifies fidelity to the retained artifact, not upstream authenticity.
    """
    validate_units(list(collection['units'].values()))
    sources={s['id']:s for s in collection['sources']}
    parts_by_artifact = {}
    for unit in collection['units'].values():
        if unit['source_id'] not in sources or unit['artifact_id'] not in collection['artifacts']:
            raise ValueError('Unit references an absent source or artifact')
        artifact=collection['artifacts'][unit['artifact_id']]
        locator=unit['source_locator']
        if artifact['source_id']!=unit['source_id'] or artifact['path']!=locator['artifact_path']:
            raise ValueError('Unit source locator does not match retained artifact')
        if artifact['text'] is None:
            raise ValueError('Undecodable artifacts cannot produce valid units')
        if unit['source_url'] != sources[unit['source_id']].get('url'):
            raise ValueError('Unit URL does not match its source')
        aid = unit['artifact_id']
        if aid not in parts_by_artifact:
            if 'original_base64' in artifact:
                try:
                    raw = base64.b64decode(artifact['original_base64'], validate=True)
                except (ValueError, TypeError, binascii.Error) as exc:
                    raise ValueError('Invalid retained original bytes') from exc
                decoded, _ = decode_artifact(raw, artifact.get('metadata', {}))
                if decoded is None or decoded != artifact['text']:
                    raise ValueError('Artifact text differs from its retained original bytes')
            try:
                parts, _ = parse_artifact(artifact, sources[unit['source_id']])
            except (ValueError, SyntaxError, TypeError, KeyError, RecursionError, LxmlError) as exc:
                raise ValueError('Cannot validate a unit against an unparseable artifact') from exc
            expected = {}
            for part in parts:
                source_locator = dict(artifact_path=artifact['path'], **part['locator'])
                key = fingerprint([source_locator, part['kind'], part['rule']])
                expected[key] = (part, source_locator)
            parts_by_artifact[aid] = expected
        key = fingerprint([locator, unit['kind'], unit['extraction_rule']])
        match = parts_by_artifact[aid].get(key)
        if match is None:
            raise ValueError('Unit locator, kind or rule does not identify a source part')
        part, source_locator = match
        if locator != source_locator or unit['text'] != part['text']:
            raise ValueError('Unit text differs from the source part at its locator')
        if fingerprint(unit.get('data')) != fingerprint(part['data']):
            raise ValueError('Unit format data differs from its source part')
        observed, _ = part_entities(part, sources[unit['source_id']], source_locator, artifact['path'])
        if sorted(map(fingerprint, unit['entities'])) != sorted(map(fingerprint, observed)):
            raise ValueError('Entity observations or coordinates do not match their source rules')
    return True
