"""Record real PostgreSQL fixture use and installed-module identity for the gate."""

import importlib.metadata
import json
import os
import sys
from pathlib import Path

import pytest

postgres_ids = []
installed = False


def pytest_sessionstart(session):
    global installed
    import world_model.restaurant_commerce.api as api

    installed = Path(api.__file__).is_relative_to(Path(os.environ["COMMERCE_EXPECTED_SITE"]))
    if not installed:
        raise pytest.UsageError("Tests must import the installed deployment artifact")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    yield
    factory = item.funcargs.get("factory")
    if factory is not None and hasattr(factory, "kw"):
        engine = factory.kw.get("bind")
        if engine is not None and engine.dialect.name == "postgresql":
            postgres_ids.append(item.nodeid)


def pytest_sessionfinish(session, exitstatus):
    Path(os.environ["COMMERCE_QUALIFICATION_PROOF"]).write_text(
        json.dumps(
            {
                "installed_artifact": installed,
                "python_version": sys.version,
                "tool_versions": {
                    name: importlib.metadata.version(name)
                    for name in ["pytest", "playwright", "hypothesis", "defusedxml"]
                },
                "postgres_test_ids": postgres_ids,
                "exit_status": int(exitstatus),
            },
            indent=2,
        )
        + "\n"
    )
