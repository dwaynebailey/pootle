#!/usr/bin/env python3
"""Phase 0, stream F: dependency vulnerability baseline.

Queries the OSV.dev API directly for each pinned package, rather than
going through pip-audit/npm audit's normal resolution path - both tried
to actually build/install the (ancient, Python-2-only) packages to get
their metadata first, which fails on current tooling for the same class
of reason the rest of Phase 0 has been running into (e.g. django-allauth's
setup.py imports a `setuptools.convert_path` that current setuptools
removed). OSV's API just needs a name + version, which we already have
pinned in requirements/base.lock.txt, so it sidesteps the problem
entirely rather than needing another archive-mirror-style workaround.

Usage:
    python3 tools/security-audit.py                 # both ecosystems
    python3 tools/security-audit.py --pypi-only
    python3 tools/security-audit.py --npm-only
    python3 tools/security-audit.py --json out.json  # also write raw results
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OSV_QUERY_URL = "https://api.osv.dev/v1/query"


def parse_requirements(path: Path) -> list[tuple[str, str]]:
    packages = []
    for line in path.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*==\s*([A-Za-z0-9_.\-]+)$", line)
        if m:
            packages.append((m.group(1), m.group(2)))
    return packages


def parse_package_json(path: Path) -> list[tuple[str, str, bool]]:
    """Returns (name, version, is_exact) - caret/tilde ranges are resolved
    to their minimum version (not exact - package.json has no committed
    lockfile), flagged via is_exact=False.
    """
    data = json.loads(path.read_text())
    packages = []
    for section in ("dependencies", "devDependencies"):
        for name, spec in data.get(section, {}).items():
            m = re.match(r"^[~^]?(\d[\w.\-]*)", spec)
            if m:
                packages.append((name, m.group(1), not re.match(r"^[~^]", spec)))
    return packages


def query_osv(ecosystem: str, name: str, version: str) -> list[dict]:
    payload = json.dumps(
        {"version": version, "package": {"name": name, "ecosystem": ecosystem}}
    ).encode()
    req = urllib.request.Request(
        OSV_QUERY_URL, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()).get("vulns", [])
    except urllib.error.URLError as e:
        print(f"  ! query failed for {name}=={version}: {e}", file=sys.stderr)
        return []


def audit(ecosystem: str, packages: list[tuple], label: str) -> dict:
    print(f"\n=== {label} ({len(packages)} packages) ===")
    results = {}
    for pkg in packages:
        name, version = pkg[0], pkg[1]
        exact_note = "" if len(pkg) < 3 or pkg[2] else "  (range, not exact pin)"
        vulns = query_osv(ecosystem, name, version)
        if vulns:
            ids = ", ".join(v["id"] for v in vulns)
            print(f"  {name}=={version}: {len(vulns)} advisory(ies) - {ids}{exact_note}")
            results[f"{name}=={version}"] = vulns
    if not results:
        print("  no known advisories for any pinned version")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pypi-only", action="store_true")
    parser.add_argument("--npm-only", action="store_true")
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    all_results = {}

    if not args.npm_only:
        pypi_packages = parse_requirements(REPO_ROOT / "requirements" / "base.lock.txt")
        all_results["pypi"] = audit("PyPI", pypi_packages, "requirements/base.lock.txt")

    if not args.pypi_only:
        npm_packages = parse_package_json(REPO_ROOT / "pootle" / "static" / "js" / "package.json")
        all_results["npm"] = audit(
            "npm", npm_packages, "pootle/static/js/package.json (no committed lockfile - ranges resolved to their minimum version)"
        )

    if args.json:
        args.json.write_text(json.dumps(all_results, indent=2))
        print(f"\nWrote raw results to {args.json}")


if __name__ == "__main__":
    main()
