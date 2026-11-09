#!/usr/bin/env python3
"""Refresh data/owasp-cheatsheets.txt from the live OWASP Cheat Sheet Series index.

Usage:
    python3 scripts/refresh_cheatsheet_index.py            # download, show diff, write file
    python3 scripts/refresh_cheatsheet_index.py --dry-run  # download and show diff only
    python3 scripts/refresh_cheatsheet_index.py --from-file index.html   # parse a saved copy

Needs network access to cheatsheetseries.owasp.org (unless --from-file). After a refresh, run
scripts/validate.py: any cheat sheet URL in the documents that no longer exists is reported.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "owasp-cheatsheets.txt"
URL = "https://cheatsheetseries.owasp.org/Glossary.html"
SLUG = re.compile(r"cheatsheets/([A-Za-z0-9_\-]+)_Cheat_Sheet\.html")


def parse(html: str) -> list[str]:
    return sorted(set(SLUG.findall(html)))


def current() -> set[str]:
    if not DATA.exists():
        return set()
    return {ln.strip() for ln in DATA.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-file", help="parse a saved copy of the index page instead of downloading")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.from_file:
        html = Path(a.from_file).read_text(encoding="utf-8")
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "website-security-skill-maintenance"})
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (fixed https URL)
            html = r.read().decode("utf-8", "replace")
    slugs = parse(html)
    if len(slugs) < 50:
        sys.exit(f"parsed only {len(slugs)} cheat sheets: the page format may have changed; not writing")
    old = current()
    new = set(slugs)
    print(f"index entries: {len(new)} (previously {len(old)})")
    for s in sorted(new - old):
        print(f"  + {s}")
    for s in sorted(old - new):
        print(f"  - {s}   <- removed or renamed upstream: check documents that link to it")
    if a.dry_run:
        return 0
    header = [
        "# OWASP Cheat Sheet Series: slug index used by scripts/validate.py",
        f"# Source: {URL} (alphabetical index)",
        f"# Retrieved: {dt.date.today().isoformat()} ({len(new)} entries). Refresh with: python3 scripts/refresh_cheatsheet_index.py",
        "# URL pattern: https://cheatsheetseries.owasp.org/cheatsheets/<slug>_Cheat_Sheet.html",
    ]
    DATA.write_text("\n".join(header + slugs) + "\n", encoding="utf-8")
    print(f"wrote {DATA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
