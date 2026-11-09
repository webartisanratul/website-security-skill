#!/usr/bin/env bash
# install.sh: install, update or remove the website-security skill in a project.
#
# Run it from a clone or an unpacked release of this repository (never pipe it from the network).
# It is idempotent, never overwrites files you modified (unless --force), and never touches
# anything outside the project directory you name with --dest.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
PAYLOAD="$ROOT/skill/website-security"
PAYLOAD_FILES="SKILL.md AI_SECURITY_RULES.md WEBSITE_SECURITY_SKILL.md SECURITY_AUDIT_CHECKLIST.md SECURITY_IMPLEMENTATION_GUIDE.md"
MANIFEST_NAME=".website-security-skill.manifest"
BEGIN_PREFIX="<!-- BEGIN website-security-skill"
END_MARK="<!-- END website-security-skill -->"

DEST="."
TARGETS="claude"
DOCS_DIR="docs/security"
FORCE=0
DRY=0
UNINSTALL=0

usage() {
    cat <<EOF
website-security-skill installer v${VERSION}

Usage: scripts/install.sh [options]

Options:
  --dest DIR        Project directory to install into (default: current directory)
  --target LIST     Comma-separated targets: claude, agents, cursor, copilot, all (default: claude)
                      claude   .claude/skills/website-security/ (Claude Code project skill)
                      agents   <docs-dir>/ plus a managed block in AGENTS.md
                      cursor   <docs-dir>/ plus .cursor/rules/website-security.mdc
                      copilot  <docs-dir>/ plus a managed block in .github/copilot-instructions.md
  --docs-dir PATH   Where agents/cursor/copilot targets keep the documents (default: docs/security)
  --force           Overwrite files you modified (a .bak copy is kept)
  --dry-run         Show what would happen; change nothing
  --uninstall       Remove files installed by this script (only if unmodified) and managed blocks
  -h, --help        Show this help

Examples:
  scripts/install.sh --dest ~/projects/shop --target claude
  scripts/install.sh --dest . --target agents,cursor --docs-dir docs/security
  scripts/install.sh --dest . --target all --dry-run
EOF
}

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
log() { printf '%s\n' "$*"; }

while [ $# -gt 0 ]; do
    case "$1" in
        --dest) [ $# -ge 2 ] || die "--dest needs a value"; DEST="$2"; shift 2 ;;
        --target) [ $# -ge 2 ] || die "--target needs a value"; TARGETS="$2"; shift 2 ;;
        --docs-dir) [ $# -ge 2 ] || die "--docs-dir needs a value"; DOCS_DIR="$2"; shift 2 ;;
        --force) FORCE=1; shift ;;
        --dry-run) DRY=1; shift ;;
        --uninstall) UNINSTALL=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; die "unknown option: $1" ;;
    esac
done

[ -d "$PAYLOAD" ] || die "payload not found at $PAYLOAD (run from a repository clone or release archive)"
[ -d "$DEST" ] || die "destination directory does not exist: $DEST"
DEST="$(cd "$DEST" && pwd)"

# docs dir must be a plain relative path
case "$DOCS_DIR" in
    /*|*..*|*[[:space:]]*|"") die "--docs-dir must be a relative path without spaces or '..'" ;;
esac
printf '%s' "$DOCS_DIR" | grep -Eq '^[A-Za-z0-9_./-]+$' || die "--docs-dir contains unsupported characters"
DOCS_DIR="${DOCS_DIR%/}"

# targets
TARGETS="$(printf '%s' "$TARGETS" | tr ',' ' ')"
EXPANDED=""
for t in $TARGETS; do
    case "$t" in
        claude|agents|cursor|copilot) EXPANDED="$EXPANDED $t" ;;
        all) EXPANDED="$EXPANDED claude agents cursor copilot" ;;
        *) die "unknown target: $t" ;;
    esac
done
TARGETS="$EXPANDED"

sha() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
OLDMAN="$DEST/$MANIFEST_NAME"
NEWMAN="$TMP/manifest.new"
: > "$NEWMAN"
OLD_VERSION=""
if [ -f "$OLDMAN" ]; then
    OLD_VERSION="$(awk '/^# version /{print $3; exit}' "$OLDMAN")"
fi

old_hash() {
    if [ -f "$OLDMAN" ]; then
        awk -v p="$1" '$2==p {print $1; exit}' "$OLDMAN"
    fi
}
record() { printf '%s  %s\n' "$1" "$2" >> "$NEWMAN"; }

put() { # src dst : copy with parents
    mkdir -p "$(dirname "$2")"
    cp "$1" "$2"
    chmod 0644 "$2"
}

do_copy() { # src rel
    local src="$1" rel="$2" dst new cur old
    dst="$DEST/$rel"
    new="$(sha "$src")"
    if [ ! -e "$dst" ]; then
        [ "$DRY" -eq 1 ] || put "$src" "$dst"
        log "  create    $rel"
        record "$new" "$rel"
        return 0
    fi
    cur="$(sha "$dst")"
    old="$(old_hash "$rel")"
    if [ "$cur" = "$new" ]; then
        log "  unchanged $rel"
        record "$new" "$rel"
    elif [ -n "$old" ] && [ "$cur" = "$old" ]; then
        [ "$DRY" -eq 1 ] || put "$src" "$dst"
        log "  update    $rel"
        record "$new" "$rel"
    elif [ "$FORCE" -eq 1 ]; then
        if [ "$DRY" -eq 0 ]; then cp "$dst" "$dst.bak"; put "$src" "$dst"; fi
        log "  overwrite $rel (backup: $rel.bak)"
        record "$new" "$rel"
    else
        [ "$DRY" -eq 1 ] || put "$src" "$dst.new"
        log "  modified  $rel (kept your version; new version written to $rel.new)"
        if [ -n "$old" ]; then record "$old" "$rel"; fi
    fi
}

render() { sed "s#{{DOCS_PATH}}#${DOCS_DIR}#g" "$1" > "$2"; }

install_block() { # blockfile rel
    local blockfile="$1" rel="$2" file rendered full out
    file="$DEST/$rel"
    rendered="$TMP/block.rendered"
    full="$TMP/block.full"
    out="$TMP/block.out"
    render "$blockfile" "$rendered"
    {
        printf '%s v%s (managed block: edit outside the markers; changes inside are overwritten) -->\n' "$BEGIN_PREFIX" "$VERSION"
        cat "$rendered"
        printf '%s\n' "$END_MARK"
    } > "$full"
    if [ ! -f "$file" ]; then
        if [ "$DRY" -eq 0 ]; then mkdir -p "$(dirname "$file")"; cp "$full" "$file"; fi
        log "  create    $rel (managed block)"
    elif grep -qF "$BEGIN_PREFIX" "$file"; then
        grep -qF "$END_MARK" "$file" || die "$rel has a BEGIN marker but no END marker; fix it manually"
        awk -v blockfile="$full" -v bp="$BEGIN_PREFIX" -v em="$END_MARK" '
            BEGIN { inblk = 0; done = 0 }
            index($0, bp) == 1 && !done { inblk = 1; while ((getline line < blockfile) > 0) print line; next }
            inblk { if (index($0, em) == 1) { inblk = 0; done = 1 } next }
            { print }
        ' "$file" > "$out"
        if cmp -s "$out" "$file"; then
            log "  unchanged $rel (managed block)"
        else
            [ "$DRY" -eq 1 ] || cp "$out" "$file"
            log "  update    $rel (managed block)"
        fi
    else
        if [ "$DRY" -eq 0 ]; then { printf '\n'; cat "$full"; } >> "$file"; fi
        log "  append    $rel (managed block)"
    fi
}

remove_block() { # rel
    local rel="$1" file out
    file="$DEST/$rel"
    out="$TMP/block.removed"
    [ -f "$file" ] || return 0
    grep -qF "$BEGIN_PREFIX" "$file" || return 0
    grep -qF "$END_MARK" "$file" || { log "  skip      $rel (BEGIN marker without END marker)"; return 0; }
    awk -v bp="$BEGIN_PREFIX" -v em="$END_MARK" '
        BEGIN { inblk = 0 }
        index($0, bp) == 1 { inblk = 1; next }
        inblk { if (index($0, em) == 1) { inblk = 0 } next }
        { print }
    ' "$file" > "$out"
    if [ -z "$(tr -d '[:space:]' < "$out")" ]; then
        [ "$DRY" -eq 1 ] || rm -f "$file"
        log "  remove    $rel (file only contained the managed block)"
    else
        [ "$DRY" -eq 1 ] || cp "$out" "$file"
        log "  remove    managed block from $rel"
    fi
}

DOCS_DONE=0
install_docs() {
    [ "$DOCS_DONE" -eq 0 ] || return 0
    DOCS_DONE=1
    log "documents -> $DOCS_DIR/"
    local f
    for f in $PAYLOAD_FILES; do do_copy "$PAYLOAD/$f" "$DOCS_DIR/$f"; done
    do_copy "$ROOT/VERSION" "$DOCS_DIR/VERSION"
    do_copy "$ROOT/LICENSE" "$DOCS_DIR/LICENSE"
}

install_claude() {
    log "claude -> .claude/skills/website-security/"
    local f
    for f in $PAYLOAD_FILES; do do_copy "$PAYLOAD/$f" ".claude/skills/website-security/$f"; done
    do_copy "$ROOT/VERSION" ".claude/skills/website-security/VERSION"
    do_copy "$ROOT/LICENSE" ".claude/skills/website-security/LICENSE"
}

uninstall_all() {
    [ -f "$OLDMAN" ] || { log "nothing to uninstall (no $MANIFEST_NAME in $DEST)"; exit 0; }
    log "uninstalling website-security-skill ${OLD_VERSION:+v$OLD_VERSION }from $DEST"
    local hash rel cur
    while read -r hash rel; do
        case "$hash" in '#'*|'') continue ;; esac
        if [ -f "$DEST/$rel" ]; then
            cur="$(sha "$DEST/$rel")"
            if [ "$cur" = "$hash" ]; then
                [ "$DRY" -eq 1 ] || rm -f "$DEST/$rel"
                log "  remove    $rel"
            else
                log "  keep      $rel (modified since install)"
            fi
        fi
    done < "$OLDMAN"
    remove_block "AGENTS.md"
    remove_block ".github/copilot-instructions.md"
    if [ "$DRY" -eq 0 ]; then
        rm -f "$OLDMAN"
        local d
        for d in ".claude/skills/website-security" ".claude/skills" ".cursor/rules" "$DOCS_DIR"; do
            rmdir "$DEST/$d" 2>/dev/null || true
        done
    fi
    log "done."
    exit 0
}

if [ "$UNINSTALL" -eq 1 ]; then uninstall_all; fi

log "website-security-skill v${VERSION} -> $DEST ${OLD_VERSION:+(previously v$OLD_VERSION)}"
[ "$DRY" -eq 0 ] || log "(dry run: no changes will be made)"

for t in $TARGETS; do
    case "$t" in
        claude) install_claude ;;
        agents)
            install_docs
            log "agents -> AGENTS.md"
            install_block "$ROOT/adapters/AGENTS.md.block.md" "AGENTS.md" ;;
        cursor)
            install_docs
            log "cursor -> .cursor/rules/website-security.mdc"
            render "$ROOT/adapters/cursor/website-security.mdc" "$TMP/website-security.mdc"
            do_copy "$TMP/website-security.mdc" ".cursor/rules/website-security.mdc" ;;
        copilot)
            install_docs
            log "copilot -> .github/copilot-instructions.md"
            install_block "$ROOT/adapters/copilot/copilot-instructions.block.md" ".github/copilot-instructions.md" ;;
    esac
done

if [ "$DRY" -eq 0 ]; then
    FINAL="$TMP/manifest.final"
    {
        printf '# version %s\n' "$VERSION"
        printf '# website-security-skill manifest: commit this file; it lets updates tell your edits from stock files\n'
        {
            cat "$NEWMAN"
            if [ -f "$OLDMAN" ]; then
                # keep entries from earlier runs (other targets) that this run did not touch
                awk 'NR == FNR { seen[$2] = 1; next } /^#/ || NF == 0 { next } !($2 in seen)' "$NEWMAN" "$OLDMAN"
            fi
        } | sort -k2
    } > "$FINAL"
    cp "$FINAL" "$OLDMAN"
    log "manifest written: $MANIFEST_NAME"
fi
log "done. Review the changes with git status / git diff before committing."
