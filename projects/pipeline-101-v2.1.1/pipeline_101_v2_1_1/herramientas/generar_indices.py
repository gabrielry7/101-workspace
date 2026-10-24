#!/usr/bin/env python3
"""Genera índices documentales desde catálogos; no ejecuta pruebas del producto."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from politicas import applicability_document, load

DOC = 'Pipeline_101_restaurantes_v2.1.1.md'
CONTEXT_NAMES = {'prepublication': 'Antes', 'postdeployment': 'Después', 'evaluation': 'Evaluación'}


def cell(value: Any) -> str:
    return str(value).replace('|', '\\|').replace('\n', ' ')


def replace_block(document: str, name: str, content: str) -> str:
    start = f'<!-- BEGIN GENERATED:{name} -->'
    end = f'<!-- END GENERATED:{name} -->'
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError(f'Bloque generado inexistente o repetido: {name}')
    left, rest = document.split(start, 1)
    _, right = rest.split(end, 1)
    return left + start + '\n' + content.strip() + '\n' + end + right


def expected_outputs(root: Path) -> dict[str, str]:
    gates = load(root / 'especificacion/compuertas.json')['gates']
    tests = load(root / 'especificacion/pruebas_aceptacion.json')['tests']
    profile = load(root / 'especificacion/perfil_piloto.json')
    policy = load(root / 'especificacion/politica_diseno.json')
    app = applicability_document(gates, tests, profile)
    summary = (
        f"**{len(gates)} compuertas y {len(tests)} casos definidos.** Bajo el perfil propuesto: "
        f"**{app['in_scope']} casos dentro del alcance y {app['out_of_scope']} fuera**. "
        f"Hay {app['prepublication_unique']} casos con obligaciones previas y "
        f"{app['postdeployment_unique']} con obligaciones posteriores; estos conjuntos se solapan "
        "y no se suman. Todos los casos del producto siguen `NOT_RUN`.\n\n"
        "La clasificación es condicional: los supuestos del perfil están `NOT_RUN`, no verificados. "
        "Este índice no emite `PASS`, `NOT_APPLICABLE` real ni autorización para publicar.\n\n"
        "| Selección por contexto | Casos |\n| --- | --- |\n"
    )
    for context in ('prepublication', 'postdeployment'):
        ids = [c['test_id'] for c in app['cases'] if
               any(context in cs for cs in c['contexts_by_gate'].values())]
        summary += f"| {CONTEXT_NAMES[context]} | {', '.join(ids)} |\n"
    excluded = [c['test_id'] for c in app['cases'] if c['selection'] == 'OUT_OF_SCOPE']
    summary += f"| Fuera del perfil propuesto | {', '.join(excluded)} |\n"

    assertion_table = '| ID | Comprobación mecánica | Límite y tratamiento |\n| --- | --- | --- |\n'
    for assertion in policy['mechanical_assertions']:
        assertion_table += f"| {assertion['id']} | {cell(assertion['assertion'])} | {cell(assertion['limit'])} |\n"
    dependencies = '| Entrada que cambia | Criterios que deben reevaluarse |\n| --- | --- |\n'
    for dimension in policy['fingerprint_dimensions']:
        affected = policy['criterion_dependencies'][dimension]
        label = 'R1–R11 (todos)' if set(affected) == set(policy['criteria']) else ', '.join(affected)
        dependencies += f'| `{dimension}` | {label} |\n'

    document = (root / DOC).read_text(encoding='utf-8')
    for name, content in [('pilot', summary), ('mechanical', assertion_table), ('invalidation', dependencies)]:
        document = replace_block(document, name, content)

    index = '# Pruebas de aceptación — Pipeline 101 v2.1.1\n\n'
    index += '**Archivo generado.** No editar las tablas a mano. Regenerar con `python3 herramientas/generar_indices.py`.\n\n'
    index += summary + '\n## Casos y razones\n\n'
    index += 'Los detalles de preparación, acción, resultado esperado y evidencia están en `especificacion/pruebas_aceptacion.json`. «Antes» y «Después» son obligaciones distintas aun cuando reutilicen el identificador de caso.\n\n'
    index += '| Caso | Qué prueba | Compuertas | Contexto en este perfil | Razón de selección/exclusión | Ejecución |\n| --- | --- | --- | --- | --- | --- |\n'
    by_id = {t['test_id']: t for t in tests}
    for result in app['cases']:
        test = by_id[result['test_id']]
        contexts = '; '.join(g + ': ' + '/'.join(CONTEXT_NAMES[c] for c in cs)
                             for g, cs in result['contexts_by_gate'].items()) or 'Fuera de alcance'
        index += '| ' + ' | '.join(cell(v) for v in [test['test_id'], test['title'], ', '.join(test['gate_ids']),
                                                     contexts, result['reason'], test['execution_status']]) + ' |\n'
    index += '\n## Obligaciones por compuerta\n\n'
    index += '| Compuerta | Antes de publicar | Después de desplegar | Evaluación |\n| --- | --- | --- | --- |\n'
    for gate in app['gates']:
        index += '| ' + gate['gate_id'] + ' | ' + ' | '.join(
            ', '.join(gate['contexts'][c]) or 'No exigida en este contexto/perfil'
            for c in ('prepublication', 'postdeployment', 'evaluation')) + ' |\n'
    index += '\n## Límites\n\nNo hay casos del producto ejecutados en esta entrega. La correspondencia entre archivos no verifica permisos, operación, navegadores, derechos ni la existencia de personas revisoras. La integración debe verificar el perfil y la procedencia de evidencias antes de usar estos resultados como selección operativa. Una omisión de detector o una obligación no ejecutada bloquea la compuerta correspondiente.\n'
    return {
        DOC: document,
        'PRUEBAS_DE_ACEPTACION.md': index,
        'APLICABILIDAD_PILOTO.json': json.dumps(app, ensure_ascii=False, indent=2) + '\n',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true', help='Solo comprobar sincronización; no escribir.')
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        outputs = expected_outputs(root)
        differences = []
        for rel, content in outputs.items():
            path = root / rel
            if args.check:
                if not path.exists() or path.read_text(encoding='utf-8') != content:
                    differences.append(rel)
            else:
                path.write_text(content, encoding='utf-8')
        if differences:
            print('Archivos desactualizados: ' + ', '.join(differences), file=sys.stderr)
            return 1
        print('Índices sincronizados.' if args.check else 'Índices regenerados; pruebas del producto: sin ejecutar.')
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'No se pudieron generar/verificar índices: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
