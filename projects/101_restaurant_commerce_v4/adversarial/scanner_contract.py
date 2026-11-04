"""Use the real OpenAPI contract with explicit, serializable disposable examples."""

from copy import deepcopy
from datetime import UTC, datetime


def inline_schema(node, root, seen=()):
    if isinstance(node, list):
        return [inline_schema(x, root, seen) for x in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node and node["$ref"].startswith("#/"):
        ref = node["$ref"]
        if ref in seen:
            raise ValueError("Recursive request schema needs an explicit fixture: " + ref)
        resolved = root
        for key in ref[2:].split("/"):
            resolved = resolved[key.replace("~1", "/").replace("~0", "~")]
        return inline_schema(
            {**resolved, **{k: v for k, v in node.items() if k != "$ref"}}, root, (*seen, ref)
        )
    return {k: inline_schema(v, root, seen) for k, v in node.items()}


def example(schema):
    if "example" in schema:
        return schema["example"]
    if "default" in schema and schema["default"] is not None:
        return schema["default"]
    if "enum" in schema:
        return schema["enum"][0]
    if "const" in schema:
        return schema["const"]
    for keyword in ["anyOf", "oneOf"]:
        if keyword in schema:
            return example(next(x for x in schema[keyword] if x.get("type") != "null"))
    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        return {
            k: example(v)
            for k, v in schema.get("properties", {}).items()
            if k in schema.get("required", [])
        }
    if kind == "array":
        return [example(schema["items"]) for _ in range(max(1, schema.get("minItems", 0)))]
    if kind in {"integer", "number"}:
        return max(schema.get("minimum", 0), schema.get("exclusiveMinimum", -1) + 1)
    if kind == "boolean":
        return False
    if schema.get("format") == "date-time":
        return datetime.now(UTC).isoformat()
    if schema.get("format") == "date":
        return datetime.now(UTC).date().isoformat()
    return "synthetic"[: schema.get("maxLength", 9)]


def prepared_spec(spec, fixtures, common_ids):
    selected = deepcopy(spec)
    coverage = []
    for path, item in selected["paths"].items():
        for method, operation in item.items():
            if method not in {"get", "post", "put", "patch", "delete", "head", "options"}:
                continue
            fixture = fixtures.get(method.upper() + " " + path, {})
            ids = {**common_ids, **fixture.get("ids", {})}
            unresolved = []
            for parameter in operation.get("parameters", []):
                if parameter["in"] == "path":
                    value = ids.get(parameter["name"], "synthetic-unbound-id")
                    if parameter["name"] not in ids:
                        unresolved.append(parameter["name"])
                    parameter["example"] = value
                    parameter.setdefault("schema", {}).update(default=value, example=value)
            content = operation.get("requestBody", {}).get("content", {}).get("application/json")
            if content is not None:
                content["schema"] = inline_schema(content["schema"], spec)
                value = fixture.get("body")
                if value is None:
                    value = example(content["schema"])
                content["example"] = value
                content["schema"]["example"] = value
                content["schema"]["default"] = value
            coverage.append(
                {
                    "operation": method.upper() + " " + path,
                    "unbound_ids": unresolved,
                    "business_fixture": bool(fixture),
                    "json_body": content is not None,
                }
            )
    return selected, coverage
