#!/usr/bin/env python3
"""Build the release artifacts into dist/.

Produces:
    dist/website-security-<version>.zip   ZIP with a top-level 'website-security/' folder (skill files,
                                          VERSION, LICENSE): upload it to claude.ai/Claude Desktop, or unzip
                                          into .claude/skills/ for Claude Code.
    dist/SHA256SUMS                       checksum of every artifact
    dist/RELEASE_NOTES.md                 the CHANGELOG section for this version

The ZIP is reproducible: entries are sorted and carry fixed timestamps and permissions, so the same
sources always give the same checksum.

Usage:
    python3 scripts/build_release.py [--skip-validate] [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "skill" / "website-security"
DIST = ROOT / "dist"
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


def version() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def changelog_section(ver: str) -> str:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    m = re.search(rf"^## \[{re.escape(ver)}\][^\n]*\n(.*?)(?=^## \[|\Z)", text, flags=re.S | re.M)
    if not m:
        raise SystemExit(f"CHANGELOG.md has no section for {ver}")
    body = re.sub(r"^\[[^\]]+\]:\s+https?://\S+\s*$", "", m.group(0), flags=re.M)
    return body.strip() + "\n"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def build(ver: str) -> Path:
    DIST.mkdir(exist_ok=True)
    out = DIST / f"website-security-{ver}.zip"
    entries = sorted(p for p in PAYLOAD.iterdir() if p.is_file())
    extra = [(ROOT / "VERSION", "VERSION"), (ROOT / "LICENSE", "LICENSE")]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        items = [(p, p.name) for p in entries] + extra
        for src, name in sorted(items, key=lambda t: t[1]):
            info = zipfile.ZipInfo(f"website-security/{name}", date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, src.read_bytes())
    return out


def check(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        bad = [n for n in names if not n.startswith("website-security/")]
        if bad:
            raise SystemExit(f"ZIP entries outside website-security/: {bad}")
        if "website-security/SKILL.md" not in names:
            raise SystemExit("ZIP is missing website-security/SKILL.md")
        if z.testzip() is not None:
            raise SystemExit("ZIP failed integrity test")
    print(f"ok: {zip_path.name} structure valid ({len(names)} files)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-validate", action="store_true", help="do not run scripts/validate.py --release first")
    ap.add_argument("--check", action="store_true", help="verify the built ZIP structure")
    args = ap.parse_args()

    if not args.skip_validate:
        rc = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate.py"), "--release"]).returncode
        if rc != 0:
            print("validation failed; refusing to build a release", file=sys.stderr)
            return rc
    ver = version()
    zip_path = build(ver)
    (DIST / "RELEASE_NOTES.md").write_text(changelog_section(ver), encoding="utf-8")
    (DIST / "SHA256SUMS").write_text(f"{sha256(zip_path)}  {zip_path.name}\n", encoding="utf-8")
    print(f"built {zip_path.relative_to(ROOT)}  sha256={sha256(zip_path)}")
    if args.check:
        check(zip_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
