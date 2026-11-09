#!/usr/bin/env python3
"""Replace the template placeholders after you create your own repository.

Usage:
    python3 scripts/init.py --owner YOUR_GITHUB_USER_OR_ORG --repo REPO_NAME \
        --name "Your Name or Org" --contact security@example.com [--year 2026] [--dry-run]

Replaces: OWNER/REPO, @OWNER, <YOUR NAME OR ORG>, SECURITY_CONTACT.
Run it once, review `git diff`, then commit.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "dist", "__pycache__"}
SKIP_FILES = {"init.py", "validate.py"}  # these legitimately contain the placeholder strings
TEXT_SUFFIXES = {".md", ".yml", ".yaml", ".toml", ".txt", ".mdc", ".sh", ".py", ".cff", ""}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--owner", required=True, help="GitHub user or organisation that will own the repository")
    ap.add_argument("--repo", required=True, help="repository name")
    ap.add_argument("--name", required=True, help="name for the LICENSE copyright line")
    ap.add_argument("--contact", required=True, help="security contact (email or URL)")
    ap.add_argument("--year", default="2026", help="copyright year (default 2026)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", a.owner):
        sys.exit("--owner must be a valid GitHub user/org name")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", a.repo):
        sys.exit("--repo must be a valid GitHub repository name")
    if not a.name.strip() or not a.contact.strip():
        sys.exit("--name and --contact must not be empty")

    replacements = [
        ("OWNER/REPO", f"{a.owner}/{a.repo}"),
        ("@OWNER", f"@{a.owner}"),
        ("<YOUR NAME OR ORG>", a.name.strip()),
        ("SECURITY_CONTACT", a.contact.strip()),
        ("Copyright (c) 2026", f"Copyright (c) {a.year}"),
    ]
    changed = 0
    for f in sorted(ROOT.rglob("*")):
        if not f.is_file() or (set(f.relative_to(ROOT).parts) & SKIP_DIRS) or f.name in SKIP_FILES:
            continue
        if f.suffix not in TEXT_SUFFIXES and f.name not in {"LICENSE", "CODEOWNERS", "VERSION"}:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text
        for old, rep in replacements:
            new = new.replace(old, rep)
        if new != text:
            changed += 1
            print(("would update " if a.dry_run else "updated      ") + str(f.relative_to(ROOT)))
            if not a.dry_run:
                f.write_text(new, encoding="utf-8")
    print(f"\n{changed} file(s) {'would change' if a.dry_run else 'changed'}. Next: git diff, then commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
