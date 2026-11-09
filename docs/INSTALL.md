# Installing the skill

Pick the route that matches your tool. In every case: **use a released, checksummed version**, read what you are
installing, and commit it to your project so the whole team uses the same version.

- [1. Get and verify a release](#1-get-and-verify-a-release)
- [2. Claude Code](#2-claude-code)
- [3. Claude.ai and Claude Desktop](#3-claudeai-and-claude-desktop)
- [4. AGENTS.md, Cursor and GitHub Copilot](#4-agentsmd-cursor-and-github-copilot)
- [5. Manual copy (any tool, Windows)](#5-manual-copy-any-tool-windows)
- [6. Context budget](#6-context-budget)
- [7. Updating and uninstalling](#7-updating-and-uninstalling)
- [8. Troubleshooting](#8-troubleshooting)

## 1. Get and verify a release

1. Open the repository's **Releases** page and download `website-security-<version>.zip` and `SHA256SUMS`
   (or `git clone` the repository and `git checkout v<version>`).
2. Verify the checksum:

   ```bash
   sha256sum -c SHA256SUMS          # macOS: shasum -a 256 -c SHA256SUMS
   ```

   ```powershell
   # Windows PowerShell: compare the printed hash with the line in SHA256SUMS
   Get-FileHash .\website-security-<version>.zip -Algorithm SHA256
   ```

3. Unzip. The ZIP contains one top-level folder, `website-security/`, with `SKILL.md`, the four documents,
   `VERSION` and `LICENSE`.

Do not run installers piped from the network. This repository's installer is meant to be read, then run from a
clone or unpacked release.

## 2. Claude Code

Claude Code loads skills from folders containing a `SKILL.md`: project skills from `.claude/skills/<name>/`
and personal skills from `~/.claude/skills/<name>/` (see the
[Claude Code skills documentation](https://code.claude.com/docs/en/skills)). The folder name must match the
skill's `name` (`website-security`).

**Project install (recommended for teams: commit it):**

```bash
# from a clone or unpacked release of this repository
scripts/install.sh --dest /path/to/your/project --target claude
cd /path/to/your/project && git add .claude .website-security-skill.manifest
```

**Personal install (all your projects):**

```bash
mkdir -p ~/.claude/skills
cp -r website-security ~/.claude/skills/        # the folder from the unzipped release
```

Claude Code watches skill directories, so a new skill is normally picked up in the current session; if you
created the top-level `skills` directory for the first time, restart Claude Code. Claude loads the skill when
your request matches its description (security-sensitive web work), or you can invoke it directly with
`/website-security`.

## 3. Claude.ai and Claude Desktop

Custom skills are uploaded as a ZIP whose **top level is the skill folder**, and the folder name must match the
`name` in `SKILL.md`: the release ZIP is built that way. Steps (the menu names vary slightly by app version and
plan; see [Using skills in Claude](https://support.claude.com/en/articles/12512180-using-skills-in-claude)):

1. Enable **code execution and file creation** in your settings (skills need it).
2. Open the skills settings (in current layouts **Customize > Skills**; in older ones **Settings > Capabilities**).
3. Choose to add a skill and **upload** `website-security-<version>.zip`.
4. Toggle the skill on. It is private to your account unless an organisation owner provisions it (Team and
   Enterprise plans).

If an upload fails, the usual causes are a ZIP that contains the files directly instead of the folder, a folder
name that does not match the skill name, or a size limit. The release ZIP avoids the first two. If you hit a
size limit, use a Claude Project instead: put the contents of `AI_SECURITY_RULES.md` in the project
instructions and add the other files as project knowledge.

## 4. AGENTS.md, Cursor and GitHub Copilot

Tools that read repository instruction files get a short managed instruction block that points to the documents.
Run the installer with the target(s) you use:

```bash
scripts/install.sh --dest /path/to/your/project --target agents      # AGENTS.md block + docs/security/
scripts/install.sh --dest /path/to/your/project --target cursor      # .cursor/rules/website-security.mdc + docs
scripts/install.sh --dest /path/to/your/project --target copilot     # .github/copilot-instructions.md block + docs
scripts/install.sh --dest /path/to/your/project --target all --dry-run   # preview everything
```

What it does:

- Copies the documents to `docs/security/` (change with `--docs-dir`).
- Inserts or updates a block between `<!-- BEGIN website-security-skill ... -->` and
  `<!-- END website-security-skill -->` in `AGENTS.md` / `.github/copilot-instructions.md`. Text outside the
  markers is never touched. For Cursor it writes a rule file (`alwaysApply: false`, with a description so the
  rule is used for security-related tasks).
- Writes `.website-security-skill.manifest` (commit it) so that later updates can tell your edits from stock files.

These instruction-file formats are conventions of the individual tools and change over time. If a tool does not
pick the file up, check that tool's current documentation; the adapter templates are plain text in
[`adapters/`](../adapters/) and easy to adapt.

## 5. Manual copy (any tool, Windows)

The documents are plain Markdown; you can simply place them where your tool can read them.

```bash
mkdir -p docs/security
cp website-security/*.md docs/security/
```

```powershell
# Windows PowerShell (from the unzipped release folder)
New-Item -ItemType Directory -Force docs\security | Out-Null
Copy-Item .\website-security\*.md docs\security\
```

Then add one line to your agent's instruction file: *"Before any security-sensitive work, read
`docs/security/AI_SECURITY_RULES.md` and follow it; consult `docs/security/WEBSITE_SECURITY_SKILL.md` as needed."*
The installer script needs Bash: on Windows use Git Bash or WSL.

## 6. Context budget

`WEBSITE_SECURITY_SKILL.md` is a reference manual, not something to load in full. The skill is built for
progressive loading: the agent reads the short rules first, then only the parts the task needs (the routing table in
`SKILL.md` says which).

| File | Size | Approx. tokens | Loaded |
|---|---|---|---|
| `SKILL.md` | 5 KB | ~1,200 | when the skill triggers |
| `AI_SECURITY_RULES.md` | 10 KB | ~2,400 | always, first |
| `SECURITY_AUDIT_CHECKLIST.md` | 29 KB | ~7,000 | for audits and releases |
| `SECURITY_IMPLEMENTATION_GUIDE.md` | 46 KB | ~11,000 | when implementing |
| `WEBSITE_SECURITY_SKILL.md` | 327 KB | ~80,000 | only the relevant parts, on demand |

(Token counts are rough, about four characters per token.) If your tool always injects whole files, add only
`AI_SECURITY_RULES.md` to the always-on instructions and reference the rest by path.

## 7. Updating and uninstalling

```bash
git fetch --tags && git checkout vX.Y.Z           # in your clone of this repository (X.Y.Z = the new release)
scripts/install.sh --dest /path/to/your/project --target claude     # use the same targets as your first install
```

- Files you have not modified are updated.
- Files you changed are **kept**; the new version is written next to them as `<file>.new` so you can merge.
  `--force` overwrites them (keeping `<file>.bak`).
- Read [CHANGELOG.md](../CHANGELOG.md) first. A MAJOR version can change mandatory agent rules.

```bash
scripts/install.sh --dest /path/to/your/project --uninstall   # removes unmodified installed files and managed blocks
```

## 8. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Claude Code does not use the skill | Check the folder is `.claude/skills/website-security/SKILL.md`; restart Claude Code if the `skills` directory was new; ask with words that match the description (for example "review this login code for security") or run `/website-security`. |
| claude.ai upload rejected | ZIP must contain the `website-security/` folder at its top level; folder name must equal the skill name; check size limits in the current support article. |
| `install.sh: No such file` on Windows | Run it in Git Bash or WSL; ensure the file has LF line endings (the repository's `.gitattributes` enforces this). |
| `*.new` files appear after an update | You edited a stock file; merge the changes, delete the `.new`, or rerun with `--force`. |
| An old block remains in `AGENTS.md` | Rerun the installer for the `agents` target; it replaces the block between the markers. |
| The agent ignores the rules | Instruction files are advisory for the agent. Make the check mandatory in review and CI: see [USAGE.md](USAGE.md). |
