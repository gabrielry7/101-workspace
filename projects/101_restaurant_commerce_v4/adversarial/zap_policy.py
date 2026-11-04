"""Risk-mapped loopback HTTP policy; unknown installed rules require review."""

BASE = {
    "6": "Path inputs/static assets: directory traversal",
    "7": "Path inputs: file inclusion; no external callback collector enabled",
    "40009": "Rendered content: server-side includes",
    "40012": "Reflected customer/staff content",
    "40014": "Stored campaign/reward content and downstream rendering",
    "40016": "Stored-XSS payload priming dependency",
    "40017": "Stored-XSS retrieval dependency",
    "40018": "SQL parameters across customer/staff routes",
    "40022": "Actual PostgreSQL engine timing injection",
    "90019": "Python code injection through user fields",
    "90020": "Command injection through user fields",
    "90035": "HTML preview template injection",
    "40003": "Header/CRLF injection",
    "40008": "Parameter types and exceptional server behavior",
    "40034": "Accidental environment-file publication",
    "10058": "Method confusion; zero messages need manual JSON method tests",
}
ADDED = {
    "0": "Accidental static directory listings",
    "40035": "Hidden backup/configuration/source files beyond .env",
    "10104": "User-agent-dependent routing or authorization behavior",
}
EXCLUDED = {
    **dict.fromkeys(
        ["10045", "10048", "20017", "20018", "40028", "40029", "40032", "40042", "40045", "40048"],
        "No Java/PHP/ASP/CGI/React server; review if deployment changes",
    ),
    **dict.fromkeys(
        ["40019", "40020", "40021", "40024", "40027"],
        "Different SQL engine; this qualification uses PostgreSQL",
    ),
    **dict.fromkeys(
        ["20019", "40043", "90023", "90034"],
        "External callback/redirect/metadata traffic excluded; egress qualification required",
    ),
    **dict.fromkeys(
        ["20015", "10106", "10047"],
        "TLS edge is absent in loopback HTTP staging; intended ingress remains unqualified",
    ),
    "40026": "DOM scan not configured; Chromium sink regressions are separate evidence",
    "90021": "No XPath consumer in this application contract",
    "90024": "No client-supplied encrypted block oracle; opaque sessions tested separately",
    "90036": "Blind template timing deferred; direct template rule enabled, bounded scan budget",
    "90037": "Blind command timing deferred; direct command rule enabled, bounded scan budget",
    "30001": "Native buffer-overflow fuzzing deferred; Python HTTP/domain boundary prioritized",
    "30002": "Native format-string exploitation deferred; Python HTTP/domain boundary prioritized",
    "40044": "No XML contract; resource exhaustion tested separately",
    "90017": "No XSLT request consumer",
    "50000": "No custom ZAP scripts installed; application-specific checks run in live HTTP suite",
    "90026": "No SOAP actions in actual OpenAPI",
    "90029": "No SOAP XML request contract",
}


def policy(inventory, expanded=False):
    selected = {**BASE, **(ADDED if expanded else {})}
    known = set(BASE) | set(ADDED) | set(EXCLUDED)
    available = {str(row["id"]) for row in inventory}
    unknown = available - known
    missing = set(selected) - available
    if unknown or missing:
        raise ValueError(
            f"ZAP policy needs review: unknown={sorted(unknown)}, missing={sorted(missing)}"
        )
    rows = []
    for row in inventory:
        rid = str(row["id"])
        if rid in selected and row.get("allDependenciesAvailable") == "false":
            raise ValueError("ZAP selected rule has unavailable dependencies: " + rid)
        rows.append(
            {
                "id": rid,
                "name": row["name"],
                "enabled": rid in selected,
                "reason": selected.get(rid)
                or EXCLUDED.get(rid)
                or "Expanded S03 rule, not selected in legacy S01 profile",
                "native_quality": row.get("quality"),
                "new_in_s03": rid in ADDED,
            }
        )
    return {
        "version": "s03-v1",
        "strength": "LOW",
        "rules": rows,
        "selected": list(selected),
        "added": list(ADDED) if expanded else [],
    }


def execution_coverage(progress, selection):
    def plugins(value):
        if isinstance(value, dict):
            if "Plugin" in value:
                yield value["Plugin"]
            for child in value.values():
                yield from plugins(child)
        elif isinstance(value, list):
            for child in value:
                yield from plugins(child)

    observed = {str(p[1]): p for p in plugins(progress) if len(p) >= 6}
    rows = []
    for rid in selection:
        p = observed.get(rid)
        count = int(p[5]) if p else 0
        rows.append(
            {
                "id": rid,
                "native": p,
                "requests": count,
                "execution": "COMPLETE" if p and p[3] == "Complete" and count else "NOT RUN",
            }
        )
    return rows
