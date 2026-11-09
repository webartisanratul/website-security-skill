#!/usr/bin/env python3
"""Validate repository consistency, internal links and content freshness.

Usage:
    python3 scripts/validate.py [--max-age-days N] [--strict] [--release]

Exit status is non-zero when an error is found. Warnings do not fail the run unless --strict.
--release additionally treats unreplaced placeholders (OWNER/REPO, <YOUR NAME OR ORG>) as errors.
Uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "skill" / "website-security"
PAYLOAD_FILES = [
    "SKILL.md",
    "AI_SECURITY_RULES.md",
    "WEBSITE_SECURITY_SKILL.md",
    "SECURITY_AUDIT_CHECKLIST.md",
    "SECURITY_IMPLEMENTATION_GUIDE.md",
]
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
SECRET_PATTERNS = {
    "AWS access key id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    "Stripe live key": re.compile(r"\bsk_live_[0-9A-Za-z]{20,}\b"),
}
PLACEHOLDERS = ["OWNER/REPO", "@OWNER", "<YOUR NAME OR ORG>", "SECURITY_CONTACT"]

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def md_files() -> list[Path]:
    skip = {".git", "dist", "node_modules"}
    return sorted(p for p in ROOT.rglob("*.md") if not (set(p.relative_to(ROOT).parts) & skip))


def strip_fences(text: str) -> str:
    return re.sub(r"^```.*?^```", "", text, flags=re.S | re.M)


def slugify(heading: str) -> str:
    """GitHub-style heading anchor."""
    h = heading.strip().lower()
    h = re.sub(r"[^\w\- ]", "", h, flags=re.U)
    return h.replace(" ", "-")


def check_version() -> str:
    vfile = ROOT / "VERSION"
    if not vfile.exists():
        err("VERSION file missing")
        return ""
    version = vfile.read_text(encoding="utf-8").strip()
    if not SEMVER.match(version):
        err(f"VERSION '{version}' is not semantic (MAJOR.MINOR.PATCH)")
    main = (PAYLOAD / "WEBSITE_SECURITY_SKILL.md").read_text(encoding="utf-8")
    m = re.search(r"Version (\d+\.\d+\.\d+\S*)", main[:1500])
    if not m:
        err("WEBSITE_SECURITY_SKILL.md header has no 'Version X.Y.Z'")
    elif m.group(1).rstrip("·").strip() != version:
        err(f"version mismatch: VERSION={version} but WEBSITE_SECURITY_SKILL.md header says {m.group(1)}")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8") if (ROOT / "CHANGELOG.md").exists() else ""
    if f"## [{version}]" not in changelog:
        err(f"CHANGELOG.md has no '## [{version}]' entry")
    return version


def check_payload() -> None:
    for name in PAYLOAD_FILES:
        if not (PAYLOAD / name).exists():
            err(f"payload file missing: skill/website-security/{name}")
    skill = PAYLOAD / "SKILL.md"
    if not skill.exists():
        return
    text = skill.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        err("SKILL.md has no YAML front matter")
        return
    front = m.group(1)
    name = re.search(r"^name:\s*(.+)$", front, flags=re.M)
    desc = re.search(r"^description:\s*(.+)$", front, flags=re.M)
    if not name or name.group(1).strip() != "website-security":
        err("SKILL.md front matter 'name' must be 'website-security' (it must equal the folder name)")
    if not desc:
        err("SKILL.md front matter has no 'description'")
    elif len(desc.group(1).strip()) > 1024:
        warn(f"SKILL.md description is {len(desc.group(1).strip())} characters (keep it under 1024)")
    if text.count("\n") > 500:
        warn("SKILL.md exceeds 500 lines; keep the entry point short and push detail to the other files")
    # every document referenced by the router must exist
    for ref in re.findall(r"`([A-Z_]+\.md)`", text):
        if ref != "SKILL.md" and not (PAYLOAD / ref).exists() and ref not in {"AGENTS.md"}:
            err(f"SKILL.md references missing file {ref}")
    main = PAYLOAD / "WEBSITE_SECURITY_SKILL.md"
    if main.exists() and main.stat().st_size > 450_000:
        warn("WEBSITE_SECURITY_SKILL.md is over 450 KB; consider splitting before it exceeds tool limits")


def check_links_and_anchors() -> None:
    all_files = md_files()
    slugs_by_file: dict[Path, set[str]] = {}
    for f in all_files:
        text = strip_fences(f.read_text(encoding="utf-8"))
        seen: dict[str, int] = {}
        slugs: set[str] = set()
        for _, heading in re.findall(r"^(#{1,6})\s+(.*)$", text, flags=re.M):
            s = slugify(heading)
            n = seen.get(s, 0)
            slugs.add(s if n == 0 else f"{s}-{n}")
            seen[s] = n + 1
        slugs_by_file[f] = slugs
    for f in all_files:
        raw = f.read_text(encoding="utf-8")
        if raw.count("```") % 2:
            err(f"{f.relative_to(ROOT)}: unbalanced code fences")
        text = strip_fences(raw)
        for target in re.findall(r"\]\(([^)\s]+)\)", text):
            if re.match(r"^(https?:|mailto:)", target):
                continue
            path_part, _, frag = target.partition("#")
            dest = f if not path_part else (f.parent / path_part).resolve()
            if path_part and not dest.exists():
                err(f"{f.relative_to(ROOT)}: broken relative link -> {target}")
                continue
            if frag and dest.suffix == ".md" and dest in slugs_by_file and frag not in slugs_by_file[dest]:
                err(f"{f.relative_to(ROOT)}: broken anchor -> {target}")


def load_cheatsheet_index() -> set[str]:
    p = ROOT / "data" / "owasp-cheatsheets.txt"
    if not p.exists():
        err("data/owasp-cheatsheets.txt missing")
        return set()
    return {ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")}


def check_cheatsheet_urls() -> None:
    index = load_cheatsheet_index()
    pat = re.compile(r"https://cheatsheetseries\.owasp\.org/cheatsheets/([A-Za-z0-9_\-]+)_Cheat_Sheet\.html")
    for f in md_files():
        for slug in sorted(set(pat.findall(f.read_text(encoding="utf-8")))):
            if slug not in index:
                err(f"{f.relative_to(ROOT)}: cheat sheet '{slug}' is not in data/owasp-cheatsheets.txt "
                    "(typo, or the index needs refreshing)")


def check_review_freshness(max_age: int, strict: bool) -> None:
    log = ROOT / "docs" / "REVIEW_LOG.md"
    if not log.exists():
        err("docs/REVIEW_LOG.md missing")
        return
    dates = re.findall(r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|", log.read_text(encoding="utf-8"), flags=re.M)
    if not dates:
        err("docs/REVIEW_LOG.md has no dated review rows")
        return
    last = max(dt.date.fromisoformat(d) for d in dates)
    age = (dt.date.today() - last).days
    if age > max_age:
        msg = f"last content review was {age} days ago ({last}); the limit is {max_age}. Run the update playbook (docs/MAINTAINING.md)."
        (err if strict else warn)(msg)


def check_secrets_and_placeholders(release: bool) -> None:
    skip_dirs = {".git", "dist"}
    for f in ROOT.rglob("*"):
        if not f.is_file() or (set(f.relative_to(ROOT).parts) & skip_dirs) or f.suffix in {".zip", ".png", ".jpg"}:
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        rel = f.relative_to(ROOT)
        for label, pat in SECRET_PATTERNS.items():
            if pat.search(text):
                err(f"{rel}: looks like a {label}")
        if rel.parts[0] == "scripts" and rel.name in {"validate.py", "init.py"}:
            continue  # these files legitimately contain the placeholder strings
        for ph in PLACEHOLDERS:
            if ph in text:
                (err if release else warn)(f"{rel}: unreplaced placeholder '{ph}' (run scripts/init.py)")
                break


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-age-days", type=int, default=100, help="maximum days since the last logged review (default 100)")
    ap.add_argument("--strict", action="store_true", help="treat warnings about review age as errors")
    ap.add_argument("--release", action="store_true", help="release mode: unreplaced placeholders are errors")
    args = ap.parse_args()

    version = check_version()
    check_payload()
    check_links_and_anchors()
    check_cheatsheet_urls()
    check_review_freshness(args.max_age_days, args.strict)
    check_secrets_and_placeholders(args.release)

    for w in warnings:
        print(f"WARN   {w}")
    for e in errors:
        print(f"ERROR  {e}")
    print(f"\nwebsite-security-skill {version or '?'}: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
