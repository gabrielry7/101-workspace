"""Regresiones DOCUMENTALES. No son las pruebas T01–T84 del producto."""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'herramientas'))
from generar_indices import expected_outputs
from politicas import load
from validar_especificacion import run


class PackageRegressions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='pipeline-211-regression-')
        self.root = Path(self.temp.name) / 'package with spaces'
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns('__pycache__', '.venv', '*.pyc'))

    def tearDown(self) -> None:
        self.temp.cleanup()

    def edit(self, rel: str, transform: Callable[[dict[str, Any]], None]) -> None:
        value = load(self.root / rel)
        transform(value)
        (self.root / rel).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def regenerate(self) -> None:
        for rel, text in expected_outputs(self.root).items():
            (self.root / rel).write_text(text, encoding='utf-8')

    def assert_rejected(self, expected_check: str) -> None:
        result = run(self.root)
        self.assertEqual(result['status'], 'FAIL')
        failed = [x['check'] for x in result['checks'] if x['status'] == 'FAIL']
        self.assertTrue(any(expected_check in name for name in failed), failed)
        self.assertEqual(result['product_tests_executed'], 0)
        self.assertFalse(result['publication_authorized'])

    def edit_test(self, tid: str, change: Callable[[dict[str, Any]], None]) -> None:
        def update(catalog: dict[str, Any]) -> None:
            change(next(t for t in catalog['tests'] if t['test_id'] == tid))
        self.edit('especificacion/pruebas_aceptacion.json', update)

    def test_00_intact_package_is_valid(self) -> None:
        result = run(self.root)
        self.assertEqual(result['status'], 'PASS')
        self.assertFalse(result['publication_authorized'])
        self.assertEqual(result['product_tests_executed'], 0)

    def test_01_legacy_G04_cannot_return_to_active_schema(self) -> None:
        self.edit('especificacion/contratos.schema.json',
                  lambda s: s['$defs']['GateResult']['properties']['gate_id']['enum'].append('G04'))
        self.assert_rejected('Enum del contrato')

    def test_02_T66_cannot_be_excluded_as_evaluation(self) -> None:
        self.edit_test('T66', lambda t: t['applicability'].update(requires_all_features=['evaluation_program']))
        self.regenerate()  # No depender solo de detectar índices viejos.
        self.assert_rejected('T66 sigue en G15')

    def test_03_T22_cannot_become_whatsapp_inventory(self) -> None:
        self.edit_test('T22', lambda t: t['applicability'].update(requires_all_capabilities=['whatsapp_request']))
        self.regenerate()
        self.assert_rejected('T22 conserva dependencia')

    def test_04_T26_cannot_become_whatsapp_quote(self) -> None:
        self.edit_test('T26', lambda t: t['applicability'].update(requires_all_capabilities=['whatsapp_request']))
        self.regenerate()
        self.assert_rejected('T26 conserva dependencia')

    def test_05_T52_is_not_a_payment_test(self) -> None:
        self.edit_test('T52', lambda t: t['applicability'].update(
            requires_all_capabilities=['online_payment'], requires_all_features=[]))
        self.regenerate()
        self.assert_rejected('T52 depende de cola')

    def test_06_production_receipt_cannot_be_required_before_deploy(self) -> None:
        self.edit_test('T59', lambda t: t['gate_contexts'].update(G15=['prepublication', 'postdeployment']))
        self.regenerate()
        self.assert_rejected('T59 es posterior')

    def test_07_static_site_cannot_skip_content_injection(self) -> None:
        self.edit_test('T40', lambda t: (t['gate_ids'].remove('G10'), t['gate_contexts'].pop('G10')))
        self.edit('especificacion/compuertas.json',
                  lambda c: next(g for g in c['gates'] if g['gate_id'] == 'G10')['test_ids'].remove('T40'))
        self.regenerate()  # Ambas referencias son consistentes; aun así falta una garantía.
        self.assert_rejected('G10 conserva inyección')

    def test_08_typography_change_must_invalidate_typography_review(self) -> None:
        self.edit('especificacion/politica_diseno.json', lambda p: p['criterion_dependencies']['typography'].remove('R5'))
        self.regenerate()
        self.assert_rejected('Cambio typography invalida R5')

    def test_09_two_rows_do_not_make_two_reviewers(self) -> None:
        self.edit('ejemplos/design_review.json',
                  lambda r: r['reviewers'][1].update(actor_id=r['reviewers'][0]['actor_id']))
        self.assert_rejected('Consistencia local de design_review.json')

    def test_10_unexecuted_review_cannot_become_PASS(self) -> None:
        self.edit('ejemplos/design_review.json', lambda r: r.update(status='PASS'))
        self.assert_rejected('Esquema de design_review.json')

    def test_11_unknown_surface_cannot_be_treated_as_absent(self) -> None:
        self.edit('especificacion/perfil_piloto.json', lambda p: p['features'].pop('shared_tenant_surfaces'))
        self.assert_rejected('Estructura estricta de perfil')

    def test_12_manual_table_changes_are_detected(self) -> None:
        target = self.root / 'PRUEBAS_DE_ACEPTACION.md'
        target.write_text(target.read_text(encoding='utf-8') + '\nClasificación manual no derivada.\n', encoding='utf-8')
        self.assert_rejected('Derivación sincronizada: PRUEBAS_DE_ACEPTACION.md')

    def test_13_modified_source_is_detected(self) -> None:
        target = self.root / 'referencia/Pipeline_101_restaurantes_v2.1.md'
        target.write_text(target.read_text(encoding='utf-8') + '\nAlteración controlada.\n', encoding='utf-8')
        self.assert_rejected('Fuente intacta: referencia/Pipeline_101_restaurantes_v2.1.md')

    def test_14_product_status_cannot_be_fabricated(self) -> None:
        self.edit_test('T01', lambda t: t.update(execution_status='PASS'))
        self.assert_rejected('Estructura estricta de pruebas')

    def test_15_unknown_context_is_rejected(self) -> None:
        self.edit_test('T59', lambda t: t['gate_contexts'].update(G15=['sometime']))
        self.assert_rejected('Estructura estricta de pruebas')

    def test_16_review_inputs_cannot_change_under_old_fingerprint(self) -> None:
        self.edit('ejemplos/design_review.json', lambda r: r['fingerprints'].update(typography='0' * 64))
        self.assert_rejected('Consistencia local de design_review.json')


if __name__ == '__main__':
    unittest.main(verbosity=2)
