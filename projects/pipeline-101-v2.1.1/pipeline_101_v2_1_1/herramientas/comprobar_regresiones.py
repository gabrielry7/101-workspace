#!/usr/bin/env python3
"""Ejecuta regresiones del paquete documental, no pruebas del producto."""
from __future__ import annotations
import argparse
import json
import sys
import unittest
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    suite = unittest.defaultTestLoader.discover(str(root / 'pruebas_documentales'), pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        'scope': 'DOCUMENTARY_REGRESSION_TESTS_ONLY',
        'status': 'PASS' if result.wasSuccessful() else 'FAIL',
        'checks_run': result.testsRun,
        'checks_failed': len(result.failures), 'checks_errored': len(result.errors),
        'checks_skipped': len(result.skipped),
        'product_tests_executed': 0, 'publication_authorized': False,
        'failures': [{'test': str(case), 'traceback': text} for case, text in result.failures],
        'errors': [{'test': str(case), 'traceback': text} for case, text in result.errors],
        'method': 'Una copia intacta y dieciséis mutaciones aisladas del paquete; los índices se regeneran cuando corresponde para no detectar solo archivos viejos.',
    }
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
