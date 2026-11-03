"""Runner regressions: never kill an earlier run or manufacture a pass from stale evidence."""

import json
import os
import sys
import time
from pathlib import Path

import pytest
import run
from summarize import summarize


def test_existing_directory_does_not_cleanup(tmp_path, monkeypatch):
    touched = []
    monkeypatch.setattr(run, "cleanup", lambda c: touched.append(c))
    (tmp_path / "config.json").write_text("{}")
    with pytest.raises(FileExistsError):
        run.setup(tmp_path)
    assert touched == []


@pytest.mark.parametrize("value", ["", "typo", "baseline,"])
def test_unknown_or_empty_layer_cannot_false_pass(value):
    with pytest.raises(ValueError):
        run.validate_layers(value)


def test_timeout_receipt_cannot_reuse_green_xml(tmp_path):
    c = {
        "run_dir": str(tmp_path),
        "revision": "test",
        "wheel_sha256": "test",
        "base_url": "http://127.0.0.1:1",
    }
    (tmp_path / "existing-tests.xml").write_text(
        '<testsuites><testsuite tests="2" failures="0" errors="0" skipped="0"/></testsuites>'
    )
    (tmp_path / "existing-tests.receipt.json").write_text(
        json.dumps(
            {
                "start": "2000-01-01T00:00:00+00:00",
                "exit_code": 124,
                "wheel_sha256": "test",
            }
        )
    )
    assert summarize(c)["layers"]["baseline"]["outcome"] != "PASS"
    (tmp_path / "browser").mkdir()
    (tmp_path / "browser/summary.json").write_text("{")
    assert summarize(c)["layers"]["browser"]["execution"] == "PARTIAL"


def test_command_refuses_to_overwrite_evidence(tmp_path):
    (tmp_path / "old.log").write_text("prior result")
    with pytest.raises(RuntimeError):
        run.command({"run_dir": str(tmp_path)}, "old", [sys.executable, "-c", "pass"])
    assert (tmp_path / "old.log").read_text() == "prior result"


def test_timeout_kills_term_resistant_descendant(tmp_path):
    marker = tmp_path / "pid"
    descendant = (
        "import os,signal,time;from pathlib import Path;signal.signal(signal.SIGTERM,signal.SIG_IGN);Path("
        + repr(str(marker))
        + ").write_text(str(os.getpid()));time.sleep(30)"
    )
    parent = (
        "import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',"
        + repr(descendant)
        + "]);time.sleep(30)"
    )
    assert (
        run.command(
            {"run_dir": str(tmp_path)},
            "timeout",
            [sys.executable, "-c", parent],
            timeout=1,
        )
        == 124
    )
    pid = int(marker.read_text())
    for _ in range(50):
        status = Path(f"/proc/{pid}/stat")
        if not status.exists() or status.read_text().split()[2] == "Z":
            break
        time.sleep(0.02)
    else:
        os.kill(pid, 9)
        pytest.fail("Owned descendant survived command timeout")


def test_cleanup_uses_restarted_owned_process_records(tmp_path, monkeypatch):
    (tmp_path / ".commerce-test-run").touch()
    stale = {"run_dir": str(tmp_path), "processes": {"application": {"pid": 10}}}
    current = {
        "run_dir": str(tmp_path),
        "processes": {"application": {"pid": 20}, "recovery": {"pid": 21}},
    }
    (tmp_path / "config.json").write_text(json.dumps(current))
    stopped = []
    monkeypatch.setattr(run, "stop", lambda c, name: stopped.append(c["processes"][name]["pid"]))
    run.cleanup(stale)
    assert stopped == [20, 21]
