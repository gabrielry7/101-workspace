"""Run every Social gate in bounded processes, retaining one combined JUnit report.

Long-lived PIL/SQL/browser fixture state exceeded this machine's memory limit in
one full pytest process. These batches change process lifetime, not selection.
"""

import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
BATCHES = (
    (
        "static-review-results",
        ("social_production", "social_design", "social_reviews", "social_results"),
    ),
    ("research-advisory", ("social_research", "social_auto_review", "social_research_browser")),
    ("media-jobs", ("social_video", "social_jobs")),
    (
        "context-connections",
        (
            "social_proposals",
            "social_context",
            "social_onboarding",
            "social_creative",
            "social_uploads",
            "social_workspace",
            "instagram_connections",
        ),
    ),
    ("workspace-browser", ("social_workspace_browser",)),
    ("video-browser", ("social_video_browser",)),
)


def main(args):
    forwarded = []
    destination = None
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in {"--junitxml", "--junit-xml"}:
            i += 1
            destination = Path(args[i])
        elif arg.startswith(("--junitxml=", "--junit-xml=")):
            destination = Path(arg.split("=", 1)[1])
        else:
            forwarded.append(arg)
        i += 1
    combined = ET.Element("testsuites")
    result = 0
    with tempfile.TemporaryDirectory(prefix="101-social-release-") as td:
        for name, modules in BATCHES:
            print("Social release: " + name, flush=True)
            report = Path(td) / (name + ".xml")
            files = [str(PROJECT / "tests" / ("test_" + m + ".py")) for m in modules]
            run = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    *files,
                    "--override-ini",
                    "addopts=",
                    "-q",
                    *forwarded,
                    "--junitxml=" + str(report),
                ],
                cwd=PROJECT,
            )
            if report.exists():
                combined.extend(ET.parse(report).getroot())
            else:
                suite = ET.SubElement(combined, "testsuite", name=name, tests="0", errors="1")
                case = ET.SubElement(suite, "testcase", name="batch_did_not_finish")
                ET.SubElement(case, "error").text = "No JUnit report; process exit: " + str(
                    run.returncode
                )
            if destination:
                destination.parent.mkdir(parents=True, exist_ok=True)
                ET.ElementTree(combined).write(destination, encoding="utf-8", xml_declaration=True)
            if run.returncode:
                result = 1
                if "-x" in forwarded or "--exitfirst" in forwarded:
                    break
    return result


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
