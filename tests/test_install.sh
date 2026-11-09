#!/usr/bin/env bash
# Regression tests for scripts/install.sh. Runs in a temporary copy of the repository.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cp -r "$SRC" "$WORK/repo"
REPO="$WORK/repo"
INSTALL="$REPO/scripts/install.sh"
FAILS=0
PASSES=0

pass() { PASSES=$((PASSES + 1)); printf 'ok    %s\n' "$1"; }
fail() { FAILS=$((FAILS + 1)); printf 'FAIL  %s\n' "$1"; }
assert() { # description, command...
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then pass "$desc"; else fail "$desc"; fi
}
refute() { # description, command...
    local desc="$1"; shift
    if "$@" >/dev/null 2>&1; then fail "$desc"; else pass "$desc"; fi
}
count() { grep -c "$1" "$2" || true; }

# 1. fresh claude install
P1="$WORK/p1"; mkdir "$P1"
bash "$INSTALL" --dest "$P1" --target claude >/dev/null
assert "claude: SKILL.md installed" test -f "$P1/.claude/skills/website-security/SKILL.md"
assert "claude: all five documents installed" test -f "$P1/.claude/skills/website-security/WEBSITE_SECURITY_SKILL.md" -a -f "$P1/.claude/skills/website-security/AI_SECURITY_RULES.md"
assert "claude: manifest written" test -f "$P1/.website-security-skill.manifest"

# 2. idempotent
OUT="$(bash "$INSTALL" --dest "$P1" --target claude)"
refute "rerun changes nothing" grep -qE '^  (create|update|overwrite|modified)' <<<"$OUT"

# 3. update: untouched file updated, edited file kept with .new
echo "local note" >> "$P1/.claude/skills/website-security/SKILL.md"
echo "<!-- upstream change -->" >> "$REPO/skill/website-security/AI_SECURITY_RULES.md"
echo "<!-- upstream change -->" >> "$REPO/skill/website-security/SKILL.md"
bash "$INSTALL" --dest "$P1" --target claude >/dev/null
assert "update: untouched file is updated" grep -q "upstream change" "$P1/.claude/skills/website-security/AI_SECURITY_RULES.md"
assert "update: edited file is kept" grep -q "local note" "$P1/.claude/skills/website-security/SKILL.md"
assert "update: new version written beside edited file" test -f "$P1/.claude/skills/website-security/SKILL.md.new"
refute "update: edited file not overwritten" grep -q "upstream change" "$P1/.claude/skills/website-security/SKILL.md"

# 4. --force overwrites with backup
bash "$INSTALL" --dest "$P1" --target claude --force >/dev/null
assert "force: file overwritten" grep -q "upstream change" "$P1/.claude/skills/website-security/SKILL.md"
assert "force: backup kept" grep -q "local note" "$P1/.claude/skills/website-security/SKILL.md.bak"

# 5. managed block keeps existing content, updates in place
P2="$WORK/p2"; mkdir "$P2"
printf '# My project\n\nExisting rules.\n' > "$P2/AGENTS.md"
bash "$INSTALL" --dest "$P2" --target agents >/dev/null
assert "agents: existing content preserved" grep -q "Existing rules." "$P2/AGENTS.md"
assert "agents: managed block present" grep -q "BEGIN website-security-skill" "$P2/AGENTS.md"
assert "agents: docs path rendered" grep -q "docs/security/AI_SECURITY_RULES.md" "$P2/AGENTS.md"
refute "agents: no unrendered placeholder" grep -q '{{DOCS_PATH}}' "$P2/AGENTS.md"
echo "extra adapter line" >> "$REPO/adapters/AGENTS.md.block.md"
bash "$INSTALL" --dest "$P2" --target agents >/dev/null
if [ "$(count 'BEGIN website-security-skill' "$P2/AGENTS.md")" = "1" ]; then
    pass "agents: block replaced, not duplicated"
else
    fail "agents: block replaced, not duplicated"
fi
assert "agents: block content updated" grep -q "extra adapter line" "$P2/AGENTS.md"

# 6. all targets + custom docs dir + dry run
P3="$WORK/p3"; mkdir "$P3"
bash "$INSTALL" --dest "$P3" --target all --docs-dir docs/sec --dry-run >/dev/null
refute "dry-run writes nothing" test -e "$P3/.claude"
bash "$INSTALL" --dest "$P3" --target all --docs-dir docs/sec >/dev/null
assert "all: cursor rule" test -f "$P3/.cursor/rules/website-security.mdc"
assert "all: copilot instructions" test -f "$P3/.github/copilot-instructions.md"
assert "all: custom docs dir used" test -f "$P3/docs/sec/AI_SECURITY_RULES.md"
assert "all: cursor rule path rendered" grep -q "docs/sec/AI_SECURITY_RULES.md" "$P3/.cursor/rules/website-security.mdc"

# 7. argument validation
refute "rejects .. in docs dir" bash "$INSTALL" --dest "$P3" --docs-dir ../x
refute "rejects absolute docs dir" bash "$INSTALL" --dest "$P3" --docs-dir /etc
refute "rejects unknown target" bash "$INSTALL" --dest "$P3" --target nope
refute "rejects missing destination" bash "$INSTALL" --dest "$WORK/missing"

# 8. uninstall keeps modified files and removes blocks
echo "mine" >> "$P3/docs/sec/SKILL.md"
bash "$INSTALL" --dest "$P3" --uninstall >/dev/null
assert "uninstall: modified file kept" test -f "$P3/docs/sec/SKILL.md"
refute "uninstall: stock file removed" test -e "$P3/docs/sec/AI_SECURITY_RULES.md"
refute "uninstall: AGENTS.md block-only file removed" test -e "$P3/AGENTS.md"
refute "uninstall: manifest removed" test -e "$P3/.website-security-skill.manifest"
bash "$INSTALL" --dest "$P2" --uninstall >/dev/null
assert "uninstall: pre-existing AGENTS.md content preserved" grep -q "Existing rules." "$P2/AGENTS.md"
refute "uninstall: managed block removed" grep -q "BEGIN website-security-skill" "$P2/AGENTS.md"

printf '\n%s passed, %s failed\n' "$PASSES" "$FAILS"
[ "$FAILS" -eq 0 ]
