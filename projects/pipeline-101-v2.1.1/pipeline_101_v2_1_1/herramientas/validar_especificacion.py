#!/usr/bin/env python3
"""Valida archivos y políticas de referencia de Pipeline 101 v2.1.1, NO el producto.

No inspecciona 101, no llama proveedores, no acredita identidades ni derechos,
no ejecuta los casos del producto y no autoriza despliegues.
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
    print('Falta jsonschema: python3 -m pip install -r requirements.txt', file=sys.stderr)
    raise SystemExit(2)

from generar_indices import DOC, expected_outputs
from politicas import (VERSION, GATE_IDS, FEATURES, affected_criteria, applicability_document,
                       canonical_bytes, design_gate_binding_errors, expected_test_ids,
                       fingerprint, load, profile_errors, report_obligation_errors,
                       review_errors, selection)

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
    results: list[dict[str, Any]] = []
    gates: list[dict[str, Any]] = []
    tests: list[dict[str, Any]] = []
    application: dict[str, Any] = {}

    def record(name: str, condition: bool, detail: Any = None) -> None:
        entry = {'check': name, 'status': 'PASS' if condition else 'FAIL'}
        if detail and not condition:
            entry['detail'] = detail
        results.append(entry)

    def finish() -> dict[str, Any]:
        passed = sum(x['status'] == 'PASS' for x in results)
        return {
            'schema_version': VERSION,
            'scope': 'DOCUMENT_PACKAGE_AND_REFERENCE_POLICIES_ONLY',
            'status': 'PASS' if passed == len(results) and results else 'FAIL',
            'spec_checks_total': len(results), 'spec_checks_passed': passed,
            'gates_defined': len(gates), 'acceptance_cases_defined': len(tests),
            'pilot_selection_conditional': {k: application.get(k) for k in (
                'in_scope', 'out_of_scope', 'prepublication_unique', 'postdeployment_unique')},
            'product_tests_executed': 0, 'production_sites_tested': 0,
            'repository_audited': False, 'publication_authorized': False,
            'limitations': [
                'No se verificaron código, detectores, navegadores ni integraciones del producto.',
                'El perfil del piloto es propuesto: sus supuestos no están verificados.',
                'Los ejemplos y PASS efímeros de controles de forma son sintéticos, no revisiones ni resultados reales.',
                'Las huellas vinculan archivos; no prueban verdad, derechos, autoridad, procedencia confiable ni existencia de una sesión humana.',
                'No hay certificación legal, de seguridad, accesibilidad o rendimiento; no se volvieron a consultar fuentes externas.',
            ],
            'checks': results,
        }

    schema = load(root / 'especificacion/contratos.schema.json')
    catalogs_schema = load(root / 'especificacion/catalogos.schema.json')
    for label, value in [('contratos', schema), ('catálogos', catalogs_schema)]:
        Draft202012Validator.check_schema(value)
        record(f'JSON Schema 2020-12 bien formado: {label}', True)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    catalog_validator = Draft202012Validator(catalogs_schema, format_checker=FormatChecker())
    gate_catalog = load(root / 'especificacion/compuertas.json')
    test_catalog = load(root / 'especificacion/pruebas_aceptacion.json')
    profile = load(root / 'especificacion/perfil_piloto.json')
    policy = load(root / 'especificacion/politica_diseno.json')
    valid_catalogs = True
    for name, data in [('compuertas', gate_catalog), ('pruebas', test_catalog), ('perfil', profile), ('diseño', policy)]:
        errors = list(catalog_validator.iter_errors(data))
        record(f'Estructura estricta de {name}', not errors, [e.message for e in errors[:3]])
        valid_catalogs = valid_catalogs and not errors
    if not valid_catalogs:
        return finish()
    gates, tests = gate_catalog['gates'], test_catalog['tests']
    gate_by_id = {g['gate_id']: g for g in gates}
    test_by_id = {t['test_id']: t for t in tests}
    record('18 compuertas activas, sin G04 legado', tuple(g['gate_id'] for g in gates) == GATE_IDS)
    record('IDs de compuerta únicos', len(gate_by_id) == len(gates))
    record('IDs T01–T84 presentes exactamente una vez', len(test_by_id) == len(tests) == 84
           and set(test_by_id) == {f'T{i:02d}' for i in range(1, 85)})
    record('Enum del contrato coincide exactamente con catálogo',
           schema['$defs']['GateResult']['properties']['gate_id'].get('enum') == list(GATE_IDS))
    record('Versión de contrato activa', schema['$id'].endswith(':' + VERSION))
    record('Referencias compuerta/caso bidireccionales',
           all(set(g['test_ids']) == {t['test_id'] for t in tests if g['gate_id'] in t['gate_ids']} for g in gates))
    record('Cada caso declara contexto exactamente para sus compuertas',
           all(set(t['gate_contexts']) == set(t['gate_ids']) for t in tests))
    record('Contextos de caso admitidos por la compuerta',
           all(set(cs).issubset(gate_by_id[g]['applicability']['contexts'])
               for t in tests for g, cs in t['gate_contexts'].items()))
    record('Cada caso mantiene preparación, acción y evidencia exigida',
           all(all(t.get(k) for k in ('given', 'when', 'expected', 'evidence_required')) for t in tests))
    record('Ningún resultado de producto inventado', all(t['execution_status'] == 'NOT_RUN'
           and t['implementation_ref'] is None and t['actual_result'] is None and not t['evidence_refs'] for t in tests))
    record('Ningún detector integrado declarado sin integración',
           all(g['checker_status'] == 'TO_INTEGRATE' and g['checker_ref'] is None for g in gates))
    record('Perfil completo, sin condiciones desconocidas', not profile_errors(profile), profile_errors(profile))
    if profile_errors(profile):
        return finish()
    record('Seis supuestos distintos y aún no verificados',
           {s['id'] for s in profile['assumptions']} == {f'S{i}' for i in range(1, 7)}
           and all(s['verification_status'] == 'NOT_RUN' and not s['evidence_refs'] for s in profile['assumptions']))
    record('Perfil conserva N0 y las cuatro capacidades del piloto',
           profile['design_level'] == 'N0' and set(profile['enabled_capabilities']) == {
               'public_info', 'menu_html', 'whatsapp_contact', 'whatsapp_request'})
    record('Reglas de G14/G16 conservan el momento correcto',
           not gate_by_id['G14']['applicability']['required_for_prepublication']
           and not gate_by_id['G16']['applicability']['pilot_required'])
    application = applicability_document(gates, tests, profile)
    record('Selección cubre cada caso exactamente una vez', len(application['cases']) == len(tests)
           and application['in_scope'] + application['out_of_scope'] == len(tests))
    pre = {g: expected_test_ids(tests, profile, g, 'prepublication') for g in GATE_IDS}
    post = {g: expected_test_ids(tests, profile, g, 'postdeployment') for g in GATE_IDS}
    record('Todas las compuertas previas obligatorias tienen obligaciones',
           all(pre[g['gate_id']] for g in gates if g['applicability']['required_for_prepublication']))
    record('G14 no se exige antes ni G16 dentro de este perfil', not pre['G14']
           and not pre['G16'] and not post['G16'])
    record('T59 es posterior en G14 y G15, nunca previo',
           test_by_id['T59']['gate_contexts'] == {'G14': ['postdeployment'], 'G15': ['postdeployment']}
           and 'T59' in post['G14'] and 'T59' in post['G15'] and 'T59' not in pre['G15'])
    record('T27 separa comprobación previa y producción',
           'T27' in pre['G05'] and 'T27' in post['G14'] and 'T27' not in pre['G14'])
    record('T66 sigue en G15 y aplica antes y después',
           test_by_id['T66']['gate_ids'] == ['G15'] and 'T66' in pre['G15'] and 'T66' in post['G15'])
    for tid in ('T22', 'T26'):
        record(tid + ' conserva dependencia de pago y queda fuera del piloto',
               test_by_id[tid]['applicability']['requires_all_capabilities'] == ['online_payment']
               and selection(test_by_id[tid], profile)['selection'] == 'OUT_OF_SCOPE')
    record('T52 depende de cola duradera, no pago',
           test_by_id['T52']['applicability']['requires_all_capabilities'] == ['whatsapp_request']
           and test_by_id['T52']['applicability']['requires_all_features'] == ['durable_notifications']
           and selection(test_by_id['T52'], profile)['selection'] == 'OUT_OF_SCOPE')
    queued = changed(profile, (['features', 'durable_notifications'], True))
    record('Activar notificaciones activa T52 sin habilitar pago',
           selection(test_by_id['T52'], queued)['selection'] == 'IN_SCOPE'
           and 'online_payment' not in queued['enabled_capabilities'])
    record('T71 se excluye por no haber búsqueda visual',
           test_by_id['T71']['applicability']['requires_all_features'] == ['visual_search']
           and selection(test_by_id['T71'], profile)['selection'] == 'OUT_OF_SCOPE')
    shared = changed(profile, (['features', 'shared_tenant_surfaces'], True))
    record('Superficie compartida activa T42 sin exigir segundo sitio publicado',
           selection(test_by_id['T42'], shared)['selection'] == 'IN_SCOPE')
    for tid in ('T25', 'T40', 'T41', 'T44', 'T63', 'T66', 'T70', 'T80', 'T81', 'T83'):
        record(f'{tid} no se elimina por simplificar el piloto', selection(test_by_id[tid], profile)['selection'] == 'IN_SCOPE')
    record('G10 conserva inyección, agente, secretos, dependencias y permisos',
           {'T40', 'T41', 'T44', 'T80', 'T81', 'T83'}.issubset(pre['G10']))
    record('G13 conserva revocación y recuperación con datos actuales',
           {'T12', 'T48', 'T49', 'T50', 'T51', 'T63', 'T70'}.issubset(pre['G13']))
    unknown = copy.deepcopy(profile); del unknown['features']['shared_tenant_surfaces']
    record('Condición ausente no equivale a falsa', bool(profile_errors(unknown)))
    unknown = changed(profile, (['features', 'shared_tenant_surfaces'], None))
    record('Condición desconocida no produce exclusión silenciosa', bool(profile_errors(unknown)))
    record('N0 no permite activar búsqueda sin revisar el perfil',
           bool(profile_errors(changed(profile, (['features', 'visual_search'], True)))))

    record('Once criterios de revisión sin duplicados', policy['criteria'] == [f'R{i}' for i in range(1, 12)])
    record('Aserciones D01–D06 completas', [a['id'] for a in policy['mechanical_assertions']]
           == [f'D{i:02d}' for i in range(1, 7)])
    record('Todas las dimensiones tienen dependencias de criterios',
           set(policy['fingerprint_dimensions']) == set(policy['criterion_dependencies'])
           and all(set(cs).issubset(policy['criteria']) for cs in policy['criterion_dependencies'].values()))
    record('Variación entre secciones y dos líneas no son compuertas duras',
           {'varied_adjacent_sections', 'description_two_lines'}.issubset(
               {d['rule_id'] for d in policy['aesthetic_defaults'] if not d['hard_gate']}))
    record('Excepciones estéticas no desactivan garantías duras',
           {'truth', 'rights', 'accessibility', 'security', 'money', 'operational_confirmation'}
           .issubset(policy['never_waivable']))

    examples: dict[str, dict[str, Any]] = {}
    example_paths = sorted((root / 'ejemplos').glob('*.json'))
    for path in example_paths:
        value = load(path)
        errors = list(validator.iter_errors(value))
        record(f'Esquema de {path.name}', not errors, [e.message for e in errors[:2]])
        if errors:
            continue
        local_errors = review_errors(value, policy) if value['kind'] == 'design_review' else semantic_errors(value)
        record(f'Consistencia local de {path.name}', not local_errors, local_errors)
        if value['kind'] == 'gate_result':
            record(f'Perfil y estado NOT_RUN de {path.name}', value['status'] == 'NOT_RUN'
                   and not report_obligation_errors(value, tests, profile))
        if value['kind'] not in examples or path.name == 'gate_result.json':
            examples[value['kind']] = value
    record('Siete contratos representados en ejemplos', set(examples) == {
        'fact', 'asset_rights', 'capability_plan', 'release_manifest', 'approval', 'gate_result', 'design_review'})
    if len(examples) != 7:
        return finish()
    manifest = examples['release_manifest']
    for art in manifest['candidate_inputs']['artifacts']:
        path = (root / art['path']).resolve()
        inside = path.is_relative_to(root.resolve())
        record('Artefacto sintético dentro de carpeta', inside)
        if inside:
            data = path.read_bytes()
            record('Huella/tamaño de artefacto sintético', hashlib.sha256(data).hexdigest() == art['sha256']
                   and len(data) == art['size_bytes'])
    record('Candidato sintético vincula perfil y modo compatibles',
           manifest['candidate_inputs']['applicability_profile_hash'] == fingerprint(profile)
           and manifest['candidate_inputs']['mode'] == profile['mode'])
    record('Aprobación de ejemplo sigue rechazada y vinculada', examples['approval']['decision'] == 'rejected'
           and examples['approval']['subject_hash'] == manifest['candidate_hash'])
    record('Revisión de diseño de ejemplo no inventa personas ni evaluación',
           examples['design_review']['status'] == 'NOT_RUN'
           and all(c['level'] == 'NOT_RUN' for r in examples['design_review']['reviewers'] for c in r['criteria']))

    fact, rights, plan, gate, approval = (examples[k] for k in (
        'fact', 'asset_rights', 'capability_plan', 'gate_result', 'approval'))
    invalid_shapes = [
        ('hecho verificado sin verificación', changed(fact, (['verification_status'], 'verified'))),
        ('clase de publicación desconocida', changed(fact, (['publication_class'], 'approved_publish_everything'))),
        ('importe negativo', changed(fact, (['value', 'amount_minor'], -1))),
        ('importe no entero', changed(fact, (['value', 'amount_minor'], 12.5))),
        ('escala COP incorrecta', changed(fact, (['value', 'minor_unit_exponent'], 0))),
        ('fecha inválida', changed(fact, (['observed_at'], 'not-a-date'))),
        ('derechos habilitados sin evidencia', changed(rights, (['status'], 'cleared'))),
        ('atribución exigida pero ausente', changed(rights, (['attribution_required'], True))),
        ('capacidad sin responsable/política', changed(plan, (['capabilities', 0, 'enabled'], True))),
        ('hash de formato inválido', changed(manifest, (['candidate_hash'], 'not-a-hash'))),
        ('agente suplantando aprobador', changed(approval, (['actor_role'], 'generator_agent'))),
        ('PASS sin ejecución ni evidencia', changed(gate, (['status'], 'PASS'))),
        ('N/A sin motivo ni evidencia', changed(gate, (['status'], 'NOT_APPLICABLE'))),
        ('G04 legado en reporte nuevo', changed(gate, (['gate_id'], 'G04'))),
        ('versión de política anterior', changed(gate, (['gate_policy_version'], '2.0'))),
    ]
    missing_id = copy.deepcopy(fact); del missing_id['fact_id']
    invalid_shapes.append(('identificador requerido ausente', missing_id))
    for label, value in invalid_shapes:
        record('Rechazo estructural esperado: ' + label, bool(list(validator.iter_errors(value))))
    for gid in ('G04a', 'G04b'):
        record(gid + ' admitida como identificador activo',
               not list(validator.iter_errors(changed(gate, (['gate_id'], gid)))))

    positive = changed(gate, (['started_at'], '2026-10-03T00:00:00Z'),
        (['finished_at'], '2026-10-03T00:00:01Z'), (['status'], 'PASS'),
        (['applicable_test_ids'], pre['G01']),
        (['case_results'], [{'test_id': tid, 'status': 'PASS', 'evidence_refs': ['synthetic-only'],
                            'not_applicable_reason': None} for tid in pre['G01']]),
        (['evidence_refs'], ['synthetic-only']))
    record('PASS sintético completo acepta solo forma y obligaciones declaradas',
           not list(validator.iter_errors(positive)) and not semantic_errors(positive)
           and not report_obligation_errors(positive, tests, profile))
    record('PASS con caso NOT_RUN se rechaza', bool(list(validator.iter_errors(
        changed(positive, (['case_results', 0, 'status'], 'NOT_RUN'))))))
    blocker = {'code': 'synthetic', 'severity': 'BLOCKER', 'message': 'synthetic',
               'owner_role': 'synthetic', 'evidence_refs': []}
    record('PASS con hallazgo bloqueante se rechaza', bool(list(validator.iter_errors(
        changed(positive, (['findings'], [blocker]))))))
    record('Cambio de contenido invalida hash de candidato', bool(semantic_errors(
        changed(manifest, (['candidate_inputs', 'content_version'], 'changed')))))
    record('Control detecta resultado de caso duplicado', bool(semantic_errors(
        changed(positive, (['case_results'], positive['case_results'] * 2)))))
    record('Control detecta falta de caso aunque el reporte se declare completo', bool(report_obligation_errors(
        changed(positive, (['applicable_test_ids'], ['T01']), (['case_results'], positive['case_results'][:1])), tests, profile)))
    record('Control detecta perfil de otro hash', bool(report_obligation_errors(
        changed(positive, (['applicability_profile_hash'], '0' * 64)), tests, profile)))
    record('Control detecta PASS sin obligaciones en momento equivocado', bool(report_obligation_errors(
        changed(positive, (['gate_id'], 'G14')), tests, profile)))
    record('Control local detecta ruta ascendente', bool(semantic_errors(
        changed(manifest, (['candidate_inputs', 'artifacts', 0, 'path'], '../private.txt')))))
    bad_plan = changed(plan, (['capabilities', 3, 'enabled'], True), (['capabilities', 3, 'mode'], 'manual'),
        (['capabilities', 3, 'owner_role'], 'synthetic'), (['capabilities', 3, 'operations_policy_ref'], 'synthetic'),
        (['capabilities', 3, 'required_test_ids'], ['T17']), (['capabilities', 3, 'dependencies'], ['menu_html']))
    record('Dependencia faltante y operación en prototipo privado se detectan', len(semantic_errors(bad_plan)) >= 2)

    review = examples['design_review']
    fingerprints = review['fingerprints']
    for dim, criterion in [('typography', 'R5'), ('color', 'R6'), ('imagery', 'R2'), ('spacing', 'R7'),
                            ('motion', 'R10'), ('visible_content', 'R3'), ('components', 'R8')]:
        new = dict(fingerprints); new[dim] = '0' * 64
        record(f'Cambio {dim} invalida {criterion} sin cambiar composición',
               criterion in affected_criteria(policy, fingerprints, new))
    record('Entradas visuales iguales no exigen nuevo juicio por sí solas',
           not affected_criteria(policy, fingerprints, fingerprints))
    record('Cambio de ámbito invalida todos los criterios',
           affected_criteria(policy, fingerprints, fingerprints, True) == policy['criteria'])
    partial = dict(fingerprints); partial.pop('typography')
    record('Dimensión faltante invalida todos los criterios',
           affected_criteria(policy, fingerprints, partial) == policy['criteria'])
    unknown_inputs = dict(fingerprints); unknown_inputs['unknown'] = '0' * 64
    record('Dimensión desconocida invalida todos los criterios',
           affected_criteria(policy, fingerprints, unknown_inputs) == policy['criteria'])
    for dim in ('design_policy', 'rubric_policy', 'routes_states', 'render_environment'):
        new = dict(fingerprints); new[dim] = '0' * 64
        record(f'Cambio {dim} invalida revisión completa',
               affected_criteria(policy, fingerprints, new) == policy['criteria'])

    complete_review = copy.deepcopy(review)
    complete_review.update(status='PASS', task_evidence_refs=['synthetic-only'],
                           device_evidence_refs=['synthetic-only'], evidence_refs=['synthetic-only'])
    for person in complete_review['reviewers']:
        person.update(authority_ref='synthetic-no-real-authority', recorded_independently=True,
                      reviewed_at='2026-10-03T00:00:00Z')
        for criterion in person['criteria']:
            criterion.update(level='aceptable', evidence_refs=['synthetic-only'])
    record('Revisión sintética completa tiene forma válida, no acredita ejecución',
           not list(validator.iter_errors(complete_review)) and not review_errors(complete_review, policy))
    for label, bad in [
        ('criterio sin evaluar', changed(complete_review, (['reviewers', 0, 'criteria', 0, 'level'], 'NOT_RUN'))),
        ('criterio fallido', changed(complete_review, (['reviewers', 0, 'criteria', 0, 'level'], 'falla'))),
        ('sin tareas observadas', changed(complete_review, (['task_evidence_refs'], []))),
        ('agente como revisor', changed(complete_review, (['reviewers', 0, 'actor_role'], 'generator_agent'))),
        ('sin revisión separada', changed(complete_review, (['reviewers', 0, 'recorded_independently'], False))),
        ('reutilización sin evidencia', changed(complete_review, (['reviewers', 0, 'criteria', 0, 'reused_from_review_id'], 'old'))),
    ]:
        record('Rechazo de revisión: ' + label, bool(list(validator.iter_errors(bad))))
    record('Revisores duplicados no cuentan como dos personas', bool(review_errors(
        changed(complete_review, (['reviewers', 1, 'actor_id'], complete_review['reviewers'][0]['actor_id'])), policy)))
    record('Once filas con criterio repetido no completan la rúbrica', bool(review_errors(
        changed(complete_review, (['reviewers', 0, 'criteria', 0, 'criterion_id'], 'R2')), policy)))
    record('Huella incorrecta de entradas de revisión se detecta', bool(review_errors(
        changed(complete_review, (['inputs_hash'], '0' * 64)), policy)))
    design_gate = changed(positive, (['gate_id'], 'G04b'), (['subject_type'], 'release_candidate'),
        (['subject_hash'], complete_review['candidate_hash']),
        (['applicable_test_ids'], pre['G04b']),
        (['case_results'], [{'test_id': tid, 'status': 'PASS', 'evidence_refs': ['synthetic-only'],
                           'not_applicable_reason': None} for tid in pre['G04b']]),
        (['design_review_ref'], 'synthetic-only'), (['design_review_hash'], fingerprint(complete_review)))
    record('G04b estructural vincula revisión completa y candidato', not list(validator.iter_errors(design_gate))
           and not design_gate_binding_errors(design_gate, complete_review)
           and not report_obligation_errors(design_gate, tests, profile))
    record('G04b PASS sin referencia humana se rechaza', bool(list(validator.iter_errors(
        changed(design_gate, (['design_review_ref'], None))))))
    record('G04b con revisión de otro candidato se rechaza', bool(design_gate_binding_errors(
        design_gate, changed(complete_review, (['candidate_hash'], '0' * 64)))))
    record('G04b con revisión no ejecutada se rechaza', bool(design_gate_binding_errors(design_gate, review)))
    record('G04b con huella de revisión errónea se rechaza', bool(design_gate_binding_errors(
        changed(design_gate, (['design_review_hash'], '0' * 64)), complete_review)))

    # Archivos derivados: cambiar el catálogo sin regenerar la tabla hace fallar la entrega.
    for rel, content in expected_outputs(root).items():
        path = root / rel
        record('Derivación sincronizada: ' + rel, path.exists() and path.read_text(encoding='utf-8') == content)
    provenance = load(root / 'especificacion/procedencia.json')
    for source in provenance['sources']:
        path = (root / source['path']).resolve()
        inside = path.is_relative_to((root / 'referencia').resolve())
        data = path.read_bytes() if inside and path.is_file() else b''
        record('Fuente intacta: ' + source['path'], inside and len(data) == source['size_bytes']
               and hashlib.sha256(data).hexdigest() == source['sha256'])
    record('Huella conocida del original preservada', hashlib.sha256(
        (root / 'referencia/Pipeline_101_original.md').read_bytes()).hexdigest()
        == '0019fe79ce07f24d05620bae7843ffd2cbd8cca0e05b984c61dbf072c1005837')
    document = (root / DOC).read_text(encoding='utf-8')
    record('Siete fases conservadas', all(f'## Fase {i} ' in document for i in range(1, 8)))
    record('Cuatro capas conservadas', all(f'## Capa transversal {c} ' in document for c in 'ABCD'))
    record('Catálogo visible sin compuerta G04 activa', '| G04 |' not in document
           and all(f'| {g} |' in document for g in GATE_IDS))
    record('Advertencia de clasificación tentativa anterior retirada',
           'Esta revisión no tuvo acceso a `especificacion/pruebas_aceptacion.json`' not in document
           and 'Unos 17 de los 74 casos' not in document)
    return finish()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--report', type=Path, help='Guardar reporte documental, sin alterar casos del producto.')
    args = parser.parse_args()
    try:
        report = run(args.root.resolve())
        if args.report:
            args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f"Especificación: {report['status']} — {report['spec_checks_passed']}/{report['spec_checks_total']} comprobaciones.")
        print(f"Definidas: {report['gates_defined']} compuertas y {report['acceptance_cases_defined']} casos.")
        print('Pruebas del producto ejecutadas: 0. Perfil no verificado. Publicación autorizada: no.')
        for item in report['checks']:
            if item['status'] != 'PASS':
                print('FAIL:', item['check'], item.get('detail', ''))
        return 0 if report['status'] == 'PASS' else 1
    except (OSError, ValueError, KeyError, TypeError, SchemaError) as exc:
        print(f'No se pudo validar la entrega: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
