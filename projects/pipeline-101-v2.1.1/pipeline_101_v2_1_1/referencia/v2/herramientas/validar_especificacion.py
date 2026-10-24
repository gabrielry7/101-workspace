#!/usr/bin/env python3
"""Valida la entrega documental de Pipeline 101 v2, NO el producto.

No inspecciona un repositorio externo, no verifica permisos reales, no llama a
proveedores, no modifica el estado de pruebas y no autoriza despliegues.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import SchemaError
except ImportError:
    print("Falta jsonschema. Ejecuta: python3 -m pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(2)


def load(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def semantic_errors(value: dict[str, Any]) -> list[str]:
    """Controles referenciales locales; nunca pruebas de verdad o autoridad."""
    errors: list[str] = []
    kind = value.get("kind")
    if kind == "release_manifest":
        calculated = hashlib.sha256(canonical_bytes(value["candidate_inputs"])).hexdigest()
        if calculated != value["candidate_hash"]:
            errors.append("candidate_hash no corresponde a candidate_inputs")
        refs = value["candidate_inputs"]["artifacts"]
        paths = [entry["path"] for entry in refs]
        if len(paths) != len(set(paths)):
            errors.append("Rutas de artefactos duplicadas")
        for raw in paths:
            p = Path(raw)
            if p.is_absolute() or ".." in p.parts or "\\" in raw:
                errors.append("Ruta de artefacto no relativa/segura")
    elif kind == "capability_plan":
        caps = value["capabilities"]
        ids = [item["capability_id"] for item in caps]
        enabled = {item["capability_id"] for item in caps if item["enabled"]}
        if len(ids) != len(set(ids)):
            errors.append("Capacidad repetida")
        for item in caps:
            if item["enabled"] and not set(item["dependencies"]).issubset(enabled):
                errors.append("Dependencia declarada no habilitada")
        if value["mode"] == "prospect_private" and enabled.intersection({
            "whatsapp_request", "reservation_request", "reservation_confirmed",
            "online_payment", "delivery_dispatch", "customer_accounts", "loyalty"
        }):
            errors.append("Prototipo privado no habilita operaciones reales")
    elif kind == "gate_result":
        ids = [item["test_id"] for item in value["case_results"]]
        if len(ids) != len(set(ids)):
            errors.append("Resultado de caso duplicado")
        if value["status"] == "PASS":
            if set(ids) != set(value["applicable_test_ids"]):
                errors.append("PASS no cubre exactamente sus casos aplicables declarados")
            if any(item["status"] != "PASS" for item in value["case_results"]):
                errors.append("PASS contiene un caso no aprobado")
    return errors


def changed(original: dict[str, Any], *changes: tuple[list[str | int], Any]) -> dict[str, Any]:
    result = copy.deepcopy(original)
    for path, replacement in changes:
        target: Any = result
        for part in path[:-1]:
            target = target[part]
        target[path[-1]] = replacement
    return result


def run(root: Path) -> dict[str, Any]:
    schema = load(root / "especificacion/contratos.schema.json")
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    gates = load(root / "especificacion/compuertas.json")["gates"]
    tests = load(root / "especificacion/pruebas_aceptacion.json")["tests"]
    results: list[dict[str, str]] = []

    def record(name: str, condition: bool) -> None:
        results.append({"check": name, "status": "PASS" if condition else "FAIL"})

    record("Esquema JSON Schema 2020-12 bien formado", True)
    gate_by_id = {g["gate_id"]: g for g in gates}
    test_by_id = {t["test_id"]: t for t in tests}
    record("IDs de compuerta únicos", len(gate_by_id) == len(gates))
    record("IDs de caso únicos", len(test_by_id) == len(tests))
    record("Cobertura G00–G16", set(gate_by_id) == {f"G{i:02d}" for i in range(17)})
    record("Cada caso tiene preparación, acción, expectativa y evidencia requerida",
           all(all(t.get(k) for k in ("given", "when", "expected", "evidence_required")) for t in tests))
    record("Todos los casos referencian compuertas existentes",
           all(set(t["gate_ids"]).issubset(gate_by_id) for t in tests))
    record("Todas las compuertas tienen casos existentes",
           all(g["test_ids"] and set(g["test_ids"]).issubset(test_by_id) for g in gates))
    record("Referencias compuerta/caso bidireccionales",
           all(set(g["test_ids"]) == {t["test_id"] for t in tests if g["gate_id"] in t["gate_ids"]}
               for g in gates))
    record("No se inventaron ejecuciones de pruebas del producto",
           all(t["execution_status"] == "NOT_RUN" and t["actual_result"] is None
               and t["implementation_ref"] is None and not t["evidence_refs"] for t in tests))
    record("No se inventaron comprobadores integrados",
           all(g["checker_status"] == "TO_INTEGRATE" and g["checker_ref"] is None for g in gates))
    record("G14 no es prerrequisito circular de su propio despliegue",
           not gate_by_id["G14"]["applicability"]["required_for_prepublication"])
    record("G16 no bloquea el primer piloto con revisión humana",
           not gate_by_id["G16"]["applicability"]["pilot_required"])

    examples: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "ejemplos").glob("*.json")):
        value = load(path)
        examples[value["kind"]] = value
        record(f"Esquema del ejemplo {path.name}", not list(validator.iter_errors(value)))
        record(f"Consistencia local del ejemplo {path.name}", not semantic_errors(value))
    record("Seis tipos de ejemplos presentes", set(examples) == {
        "fact", "asset_rights", "capability_plan", "release_manifest", "approval", "gate_result"
    })
    manifest = examples["release_manifest"]
    for art in manifest["candidate_inputs"]["artifacts"]:
        candidate_path = (root / art["path"]).resolve()
        if not candidate_path.is_relative_to(root.resolve()):
            record("Artefacto de ejemplo dentro de la carpeta", False)
            continue
        data = candidate_path.read_bytes()
        record("Hash y tamaño del artefacto sintético",
               hashlib.sha256(data).hexdigest() == art["sha256"] and len(data) == art["size_bytes"])
    record("Rechazo sintético refiere el candidato sintético",
           examples["approval"]["subject_hash"] == manifest["candidate_hash"]
           and examples["approval"]["decision"] == "rejected")
    record("El ejemplo de compuerta permanece NOT_RUN",
           examples["gate_result"]["status"] == "NOT_RUN")

    # Rechazos esperados: prueban nuestros esquemas/controles de referencia,
    # no demuestran que esas defensas existan ya en 101.
    fact, rights, plan, gate, approval = (examples[k] for k in (
        "fact", "asset_rights", "capability_plan", "gate_result", "approval"))
    invalid_shapes = [
        ("hecho verificado sin verificación", changed(fact, (["verification_status"], "verified"))),
        ("clase de publicación desconocida", changed(fact, (["publication_class"], "approved_publish_everything"))),
        ("importe negativo", changed(fact, (["value", "amount_minor"], -1))),
        ("importe no entero", changed(fact, (["value", "amount_minor"], 12.5))),
        ("escala COP incorrecta", changed(fact, (["value", "minor_unit_exponent"], 0))),
        ("fecha inválida", changed(fact, (["observed_at"], "not-a-date"))),
        ("derechos habilitados sin evidencia", changed(rights, (["status"], "cleared"))),
        ("atribución exigida pero ausente", changed(rights, (["attribution_required"], True))),
        ("capacidad habilitada sin responsable/política", changed(plan, (["capabilities", 0, "enabled"], True))),
        ("hash de formato inválido", changed(manifest, (["candidate_hash"], "not-a-hash"))),
        ("agente suplantando aprobador", changed(approval, (["actor_role"], "generator_agent"))),
        ("PASS sin ejecución ni evidencia", changed(gate, (["status"], "PASS"))),
        ("N/A sin motivo ni evidencia", changed(gate, (["status"], "NOT_APPLICABLE"))),
    ]
    missing_id = copy.deepcopy(fact)
    del missing_id["fact_id"]
    invalid_shapes.append(("identificador requerido ausente", missing_id))
    for label, value in invalid_shapes:
        record(f"Rechazo estructural esperado: {label}", bool(list(validator.iter_errors(value))))

    positive_shape = changed(gate,
        (["started_at"], "2026-10-03T00:00:00Z"),
        (["finished_at"], "2026-10-03T00:00:01Z"),
        (["status"], "PASS"),
        (["applicable_test_ids"], ["T01"]),
        (["case_results"], [{"test_id": "T01", "status": "PASS", "evidence_refs": ["synthetic-only"], "not_applicable_reason": None}]),
        (["evidence_refs"], ["synthetic-only"]))
    record("Forma sintética PASS completa aceptada por esquema (no autorización real)",
           not list(validator.iter_errors(positive_shape)) and not semantic_errors(positive_shape))
    record("Rechazo de PASS con caso NOT_RUN", bool(list(validator.iter_errors(
        changed(positive_shape, (["case_results", 0, "status"], "NOT_RUN"))))))
    blocker = {"code": "synthetic", "severity": "BLOCKER", "message": "synthetic",
               "owner_role": "synthetic", "evidence_refs": []}
    record("Rechazo de PASS con hallazgo bloqueante", bool(list(validator.iter_errors(
        changed(positive_shape, (["findings"], [blocker]))))))
    record("Hash detecta modificación de contenido del candidato", bool(semantic_errors(
        changed(manifest, (["candidate_inputs", "content_version"], "changed-after-approval")))))
    record("Control local detecta caso aplicable faltante", bool(semantic_errors(
        changed(positive_shape, (["applicable_test_ids"], ["T01", "T02"])))))
    record("Control local detecta resultado duplicado", bool(semantic_errors(
        changed(positive_shape, (["case_results"], positive_shape["case_results"] * 2)))))
    record("Control local detecta rutas con ascenso", bool(semantic_errors(
        changed(manifest, (["candidate_inputs", "artifacts", 0, "path"], "../private.txt")))))
    bad_plan = changed(plan,
        (["capabilities", 3, "enabled"], True),
        (["capabilities", 3, "mode"], "manual"),
        (["capabilities", 3, "owner_role"], "synthetic"),
        (["capabilities", 3, "operations_policy_ref"], "synthetic"),
        (["capabilities", 3, "required_test_ids"], ["T17"]),
        (["capabilities", 3, "dependencies"], ["menu_html"]))
    record("Control local detecta dependencia faltante y operación en prototipo privado",
           len(semantic_errors(bad_plan)) >= 2)

    original = root / "referencia/Pipeline_101_original.md"
    record("Original conservado sin modificaciones",
           hashlib.sha256(original.read_bytes()).hexdigest()
           == "0019fe79ce07f24d05620bae7843ffd2cbd8cca0e05b984c61dbf072c1005837")
    document = (root / "Pipeline_101_restaurantes_v2.md").read_text(encoding="utf-8")
    record("Documento conserva las siete fases", all(f"## Fase {i} " in document for i in range(1, 8)))
    record("Documento conserva las cuatro capas transversales",
           all(f"## Capa transversal {c} " in document for c in "ABCD"))
    record("Documento referencia todas las compuertas", all(gid in document for gid in gate_by_id))

    passed = sum(item["status"] == "PASS" for item in results)
    return {
        "scope": "DOCUMENT_PACKAGE_AND_REFERENCE_CONTRACTS_ONLY",
        "status": "PASS" if passed == len(results) else "FAIL",
        "spec_checks_total": len(results),
        "spec_checks_passed": passed,
        "gates_defined": len(gates),
        "acceptance_cases_defined": len(tests),
        "product_tests_executed": 0,
        "production_sites_tested": 0,
        "repository_audited": False,
        "publication_authorized": False,
        "limitations": [
            "No se validaron código ni integraciones de 101.",
            "Los ejemplos son sintéticos; hashes de entradas auxiliares son ilustrativos.",
            "La forma de una aprobación o reporte no verifica autoridad o autenticidad.",
            "Las comprobaciones no constituyen certificación de seguridad, legalidad, accesibilidad ni rendimiento."
        ],
        "checks": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--report", type=Path, help="Guardar reporte JSON, sin alterar catálogos.")
    args = parser.parse_args()
    try:
        report = run(args.root.resolve())
        text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.report:
            args.report.write_text(text, encoding="utf-8")
        print(f"Especificación: {report['status']} — {report['spec_checks_passed']}/{report['spec_checks_total']} comprobaciones.")
        print(f"Definidas: {report['gates_defined']} compuertas y {report['acceptance_cases_defined']} pruebas de aceptación.")
        print("Pruebas del producto ejecutadas: 0. Publicación autorizada: no.")
        for check in report["checks"]:
            if check["status"] != "PASS":
                print("FAIL:", check["check"])
        return 0 if report["status"] == "PASS" else 1
    except (OSError, ValueError, KeyError, TypeError, SchemaError) as exc:
        print(f"No se pudo validar la entrega: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
