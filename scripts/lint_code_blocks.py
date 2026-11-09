#!/usr/bin/env python3
"""Extract fenced code blocks from the Markdown documents and lint them.

Checks (each skipped with a notice if its tool is missing, unless --require-tools):
    php         php -l            (blocks without an opening tag get one prepended)
    bash        shellcheck -S warning
    javascript  node --check      (as an ES module)
    yaml        PyYAML safe_load_all (if installed)
    json        json.loads

Usage:
    python3 scripts/lint_code_blocks.py [--require-tools] [paths ...]

nginx and SQL blocks are not checked here: nginx needs a surrounding configuration and
certificates (see docs/VERIFICATION.md for the manual harness).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^```([A-Za-z0-9_+-]*)\n(.*?)^```", re.S | re.M)


def run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def check_block(lang: str, body: str) -> tuple[bool, str] | None:
    """Return (ok, message), or None when the language/tool is not checked."""
    with tempfile.TemporaryDirectory() as td:
        if lang == "php":
            if not shutil.which("php"):
                return None
            text = body if body.lstrip().startswith("<?php") else "<?php\n" + body
            p = Path(td, "b.php")
            p.write_text(text, encoding="utf-8")
            rc, out = run(["php", "-l", str(p)])
            return rc == 0, out
        if lang == "bash":
            if not shutil.which("shellcheck"):
                return None
            p = Path(td, "b.sh")
            p.write_text(body, encoding="utf-8")
            rc, out = run(["shellcheck", "-S", "warning", "-s", "bash", str(p)])
            return rc == 0, out
        if lang == "javascript":
            if not shutil.which("node"):
                return None
            p = Path(td, "b.mjs")
            p.write_text(body, encoding="utf-8")
            rc, out = run(["node", "--check", str(p)])
            return rc == 0, out
        if lang == "yaml":
            try:
                import yaml  # type: ignore
            except ImportError:
                return None
            try:
                list(yaml.safe_load_all(body))
                return True, ""
            except Exception as exc:  # noqa: BLE001
                return False, str(exc)
        if lang == "json":
            try:
                json.loads(body)
                return True, ""
            except ValueError as exc:
                return False, str(exc)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="Markdown files (default: every *.md in the repository)")
    ap.add_argument("--require-tools", action="store_true", help="fail if a needed tool is not installed")
    args = ap.parse_args()

    files = [Path(p) for p in args.paths] or sorted(
        p for p in ROOT.rglob("*.md") if ".git" not in p.parts and "dist" not in p.parts
    )
    passed: Counter[str] = Counter()
    failed: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    problems: list[str] = []

    for f in files:
        text = f.read_text(encoding="utf-8")
        for m in FENCE.finditer(text):
            lang, body = m.group(1), m.group(2)
            line = text[: m.start()].count("\n") + 1
            if lang not in {"php", "bash", "javascript", "yaml", "json"}:
                continue
            res = check_block(lang, body)
            if res is None:
                skipped[lang] += 1
                continue
            ok, msg = res
            if ok:
                passed[lang] += 1
            else:
                failed[lang] += 1
                problems.append(f"{f.relative_to(ROOT) if f.is_absolute() else f}:{line} [{lang}] {msg.splitlines()[0] if msg else ''}")

    for lang in sorted(set(passed) | set(failed) | set(skipped)):
        print(f"{lang:<11} passed={passed[lang]:<3} failed={failed[lang]:<3} skipped(no tool)={skipped[lang]}")
    for p in problems:
        print("FAIL", p)
    if skipped and args.require_tools:
        print("error: missing tools for:", ", ".join(sorted(skipped)))
        return 1
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
