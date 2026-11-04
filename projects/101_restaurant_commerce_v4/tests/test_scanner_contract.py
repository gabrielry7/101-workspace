"""Coverage checks must reject malformed imports and proof-free success."""

import importlib.util
import json
from pathlib import Path

path = Path(__file__).parents[1] / "adversarial/scanner_contract.py"
spec = importlib.util.spec_from_file_location("scanner_contract", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_nested_body_refs_are_resolved_and_real_identifiers_preserved():
    schema = {
        "components": {
            "schemas": {
                "Copy": {
                    "type": "object",
                    "required": ["body"],
                    "properties": {"body": {"type": "string"}},
                }
            }
        },
        "paths": {
            "/campaigns/{campaign_id}": {
                "put": {
                    "parameters": [
                        {"name": "campaign_id", "in": "path", "schema": {"type": "string"}}
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["content"],
                                    "properties": {
                                        "content": {"$ref": "#/components/schemas/Copy"}
                                    },
                                }
                            }
                        }
                    },
                }
            }
        },
    }
    before = json.dumps(schema, sort_keys=True)
    fixture = {
        "PUT /campaigns/{campaign_id}": {
            "ids": {"campaign_id": "actual-row"},
            "body": {"content": {"body": 'Nested "quote" / unicode café'}},
        }
    }
    selected, coverage = module.prepared_spec(schema, fixture, {})
    operation = selected["paths"]["/campaigns/{campaign_id}"]["put"]
    assert operation["parameters"][0]["schema"]["default"] == "actual-row"
    content = operation["requestBody"]["content"]["application/json"]
    assert "$ref" not in json.dumps(content)
    assert (
        json.loads(json.dumps(content["example"]))
        == fixture["PUT /campaigns/{campaign_id}"]["body"]
    )
    assert coverage[0]["unbound_ids"] == [] and coverage[0]["business_fixture"]
    assert json.dumps(schema, sort_keys=True) == before


def test_unbound_ids_are_explicit_not_empty_or_claimed_as_covered():
    selected, coverage = module.prepared_spec(
        {
            "paths": {
                "/{id}": {
                    "get": {
                        "parameters": [{"name": "id", "in": "path", "schema": {"type": "string"}}]
                    }
                }
            }
        },
        {},
        {},
    )
    assert coverage[0]["unbound_ids"] == ["id"]
    assert not coverage[0]["business_fixture"]
    assert selected["paths"]["/{id}"]["get"]["parameters"][0]["example"]
