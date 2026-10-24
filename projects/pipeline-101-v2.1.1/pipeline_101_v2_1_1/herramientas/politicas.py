#!/usr/bin/env python3
"""Políticas de referencia del paquete documental; no autorizan producción."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

VERSION = '2.1.1'
CONTEXTS = ('prepublication', 'postdeployment', 'evaluation')
GATE_IDS = tuple([f'G{i:02d}' for i in range(4)] + ['G04a', 'G04b'] + [f'G{i:02d}' for i in range(5, 17)])
CAPABILITIES = frozenset(('public_info', 'menu_html', 'whatsapp_contact', 'whatsapp_request',
                         'reservation_request', 'reservation_confirmed', 'online_payment',
                         'delivery_dispatch', 'customer_accounts', 'loyalty'))
FEATURES = frozenset(('multi_location', 'shared_tenant_surfaces', 'durable_notifications',
                     'visual_search', 'evaluation_program'))


def load(path: Path) -> Any:
    """Rechaza claves JSON duplicadas y valores no finitos."""
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f'Clave JSON duplicada: {key}')
            result[key] = value
        return result

    def invalid_constant(value: str) -> None:
        raise ValueError(f'Número JSON no finito: {value}')

    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=invalid_constant)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def profile_errors(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if profile.get('schema_version') != VERSION or profile.get('kind') != 'applicability_profile':
        errors.append('Tipo o versión de perfil no admitidos')
    features = profile.get('features', {})
    if set(features) != FEATURES or any(type(v) is not bool for v in features.values()):
        errors.append('Las condiciones del perfil deben ser completas y booleanas; desconocido no es falso')
    caps = profile.get('enabled_capabilities', [])
    if len(caps) != len(set(caps)) or not set(caps).issubset(CAPABILITIES):
        errors.append('Capacidades desconocidas o repetidas')
    enabled = set(caps)
    dependencies = {'whatsapp_request': {'menu_html', 'whatsapp_contact'},
                    'online_payment': {'menu_html'}}
    if any(cap in enabled and not deps.issubset(enabled) for cap, deps in dependencies.items()):
        errors.append('Dependencias de capacidad incompletas')
    if profile.get('mode') not in ('prospect_private', 'authorized_live'):
        errors.append('Modalidad desconocida')
    if profile.get('mode') == 'prospect_private' and enabled & {
            'whatsapp_request', 'reservation_request', 'reservation_confirmed',
            'online_payment', 'delivery_dispatch', 'customer_accounts', 'loyalty'}:
        errors.append('Un prototipo privado no activa operaciones reales')
    contexts = profile.get('contexts', [])
    if not contexts or len(contexts) != len(set(contexts)) or not set(contexts).issubset(CONTEXTS):
        errors.append('Contextos ausentes, repetidos o desconocidos')
    if 'evaluation' in contexts and features.get('evaluation_program') is not True:
        errors.append('Contexto de evaluación sin programa de evaluación')
    if profile.get('design_level') not in ('N0', 'N1', 'N2', 'N3'):
        errors.append('Nivel de diseño desconocido')
    if profile.get('design_level') == 'N0' and features.get('visual_search') is True:
        errors.append('N0 no incluye búsqueda visual automática')
    return errors


def selection(test: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Deriva selección CONDICIONAL. No emite NOT_APPLICABLE ni PASS reales."""
    errors = profile_errors(profile)
    if errors:
        raise ValueError('; '.join(errors))
    applicability = test['applicability']
    required_caps = applicability['requires_all_capabilities']
    required_features = applicability['requires_all_features']
    if not set(required_caps).issubset(CAPABILITIES):
        raise ValueError('La prueba contiene una capacidad desconocida')
    if not set(required_features).issubset(FEATURES):
        raise ValueError('La prueba contiene una condición desconocida')
    contexts_by_gate = test['gate_contexts']
    if set(contexts_by_gate) != set(test['gate_ids']):
        raise ValueError('Contextos de prueba no coinciden con sus compuertas')
    for gate_id, contexts in contexts_by_gate.items():
        if gate_id not in GATE_IDS or not contexts or not set(contexts).issubset(CONTEXTS):
            raise ValueError('Compuerta/contexto desconocido o sin contexto')
    reasons = [f'capacidad deshabilitada: {c}' for c in required_caps
               if c not in profile['enabled_capabilities']]
    reasons += [f'condición ausente: {f}' for f in required_features
                if not profile['features'][f]]
    declared_contexts = set(profile['contexts'])
    active = {g: [c for c in cs if c in declared_contexts]
              for g, cs in contexts_by_gate.items()}
    active = {g: cs for g, cs in active.items() if cs}
    if not active:
        reasons.append('contexto fuera del perfil: ' + ', '.join(sorted({
            c for cs in contexts_by_gate.values() for c in cs})))
    in_scope = not reasons
    return {
        'test_id': test['test_id'],
        'selection': 'IN_SCOPE' if in_scope else 'OUT_OF_SCOPE',
        'reason': '; '.join(reasons) if reasons else 'Capacidades, condiciones y contexto cubiertos por el perfil propuesto.',
        'contexts_by_gate': active if in_scope else {},
        'execution_status': test['execution_status'],
    }


def expected_test_ids(tests: list[dict[str, Any]], profile: dict[str, Any],
                      gate_id: str, context: str) -> list[str]:
    if gate_id not in GATE_IDS or context not in CONTEXTS:
        raise ValueError('Compuerta o contexto desconocido')
    selected: list[str] = []
    for test in tests:
        result = selection(test, profile)
        if context in result['contexts_by_gate'].get(gate_id, []):
            selected.append(test['test_id'])
    return selected


def report_obligation_errors(report: dict[str, Any], tests: list[dict[str, Any]],
                             profile: dict[str, Any]) -> list[str]:
    """Contrasta un PASS estructural con obligaciones derivadas, no autenticidad."""
    errors = profile_errors(profile)
    if errors:
        return errors
    if report.get('applicability_profile_hash') != fingerprint(profile):
        errors.append('El reporte no corresponde al perfil de aplicabilidad')
    try:
        expected = expected_test_ids(tests, profile, report['gate_id'], report['evaluation_context'])
    except (KeyError, ValueError) as exc:
        return errors + [str(exc)]
    if report.get('status') == 'PASS':
        declared = report.get('applicable_test_ids', [])
        if not expected:
            errors.append('No se permite PASS de una compuerta sin obligaciones en este contexto')
        if len(declared) != len(set(declared)) or set(declared) != set(expected):
            errors.append('PASS no cubre los casos derivados del catálogo y perfil')
    return errors


def affected_criteria(policy: dict[str, Any], before: dict[str, Any],
                      after: dict[str, Any], scope_changed: bool = False) -> list[str]:
    """Devuelve invalidación conservadora; desconocido/ausente invalida todo."""
    dimensions = set(policy['fingerprint_dimensions'])
    criteria = policy['criteria']
    if scope_changed or set(before) != dimensions or set(after) != dimensions:
        return list(criteria)
    if any(not isinstance(v, str) or re.fullmatch(r'[0-9a-f]{64}', v) is None for v in [*before.values(), *after.values()]):
        return list(criteria)
    changed = {key for key in dimensions if before[key] != after[key]}
    affected: set[str] = set()
    for key in changed:
        affected.update(policy['criterion_dependencies'].get(key, criteria))
    return [c for c in criteria if c in affected]


def review_errors(value: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    """Consistencia de una revisión; las personas/evidencias requieren verificación externa."""
    errors: list[str] = []
    if fingerprint(value['fingerprints']) != value['inputs_hash']:
        errors.append('Huella de entradas de diseño incorrecta')
    people = value['reviewers']
    actors = [person['actor_id'] for person in people]
    if len(actors) != policy['required_reviewers'] or len(set(actors)) != len(actors):
        errors.append('Se requieren dos personas distintas')
    for person in people:
        ids = [item['criterion_id'] for item in person['criteria']]
        if len(ids) != len(set(ids)) or set(ids) != set(policy['criteria']):
            errors.append('Cada persona debe evaluar exactamente los once criterios')
        if value['status'] == 'PASS' and any(item['level'] not in ('aceptable', 'destacado')
                                           for item in person['criteria']):
            errors.append('PASS con criterio fallido o no evaluado')
        for item in person['criteria']:
            if item.get('reused_from_review_id') == value['review_id']:
                errors.append('Una revisión no puede reutilizarse a sí misma')
    return errors


def design_gate_binding_errors(report: dict[str, Any], review: dict[str, Any]) -> list[str]:
    """Une G04b al candidato y archivo de revisión concretos, sin verificar autoridad."""
    errors: list[str] = []
    if report.get('gate_id') != 'G04b' or report.get('status') != 'PASS':
        return errors
    if review.get('status') != 'PASS':
        errors.append('G04b PASS exige revisión PASS')
    if report.get('subject_type') != 'release_candidate' or report.get('subject_hash') != review.get('candidate_hash'):
        errors.append('Revisión y G04b no corresponden al mismo candidato')
    if report.get('design_review_hash') != fingerprint(review):
        errors.append('La huella de la revisión no corresponde al archivo referenciado')
    return errors


def applicability_document(gates: list[dict[str, Any]], tests: list[dict[str, Any]],
                           profile: dict[str, Any]) -> dict[str, Any]:
    cases = [selection(t, profile) for t in tests]
    selected = [c for c in cases if c['selection'] == 'IN_SCOPE']
    return {
        'schema_version': VERSION,
        'scope': 'CONDITIONAL_SPECIFICATION_SELECTION_NOT_PRODUCT_EXECUTION',
        'profile_id': profile['profile_id'],
        'profile_hash': fingerprint(profile),
        'catalog_hash': fingerprint({'gates': gates, 'tests': tests}),
        'profile_verification': profile['status'],
        'publication_authorized': False,
        'tests_total': len(tests), 'in_scope': len(selected),
        'out_of_scope': len(cases) - len(selected),
        'prepublication_unique': len({c['test_id'] for c in selected
                                     if any('prepublication' in cs for cs in c['contexts_by_gate'].values())}),
        'postdeployment_unique': len({c['test_id'] for c in selected
                                     if any('postdeployment' in cs for cs in c['contexts_by_gate'].values())}),
        'gates': [{
            'gate_id': g['gate_id'],
            'contexts': {context: expected_test_ids(tests, profile, g['gate_id'], context)
                         for context in CONTEXTS},
        } for g in gates],
        'cases': cases,
    }
