# Website Security Skill

[![CI](https://github.com/webartisanratul/website-security-skill/actions/workflows/ci.yml/badge.svg)](https://github.com/webartisanratul/website-security-skill/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/webartisanratul/website-security-skill)](https://github.com/webartisanratul/website-security-skill/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**A verified, agent-readable web application security standard.** Mandatory rules for AI coding agents, an attack
and control reference, an audit checklist and implementation recipes (Laravel, PHP, Vue, Nginx, Linux, Cloudflare),
packaged so you can drop it into a project and keep it current.

It is built around one idea: security work by an AI agent is only worth trusting if the agent **inspects first,
chooses controls proportionately, proves each fix with a test that fails before and passes after, and reports what it
could not verify.** The rules make that behaviour mandatory; the reference material makes it possible.

> **Not a guarantee.** Following this guidance reduces common mistakes; it does not make a system "secure" and does
> not replace threat modelling, independent penetration testing, compliance work or legal advice.

## What is inside

| File | Purpose | Loaded by the agent |
|---|---|---|
| [`AI_SECURITY_RULES.md`](skill/website-security/AI_SECURITY_RULES.md) | Short, strict rules for AI agents: inspect first, proportionate controls, regression test per fix, no weakened controls, no secrets, no unverified claims. | Always, first |
| [`WEBSITE_SECURITY_SKILL.md`](skill/website-security/WEBSITE_SECURITY_SKILL.md) | The reference manual (Parts 0 to 18): 173 attacks in 12 families with mechanism, prevention, detection and verification; input validation; Cloudflare; headers; authentication; APIs; database; frontend; servers; supply chain; monitoring; testing; incident response; prioritisation; references. | On demand, only relevant parts |
| [`SECURITY_AUDIT_CHECKLIST.md`](skill/website-security/SECURITY_AUDIT_CHECKLIST.md) | 13-domain audit checklist: requirement, risk, status, verification method, component, plus release gates. | For audits and releases |
| [`SECURITY_IMPLEMENTATION_GUIDE.md`](skill/website-security/SECURITY_IMPLEMENTATION_GUIDE.md) | Copy-adaptable recipes for Laravel, plain PHP, Vue/JS, Nginx/PHP-FPM, Linux, Cloudflare, plus a test and smoke-script harness. | When implementing |
| [`SKILL.md`](skill/website-security/SKILL.md) | The skill entry point: trigger description and a task-to-section routing table. | When the skill triggers |

Around them: an [installer](scripts/install.sh) with Claude Code, `AGENTS.md`, Cursor and GitHub Copilot targets,
[validation and release tooling](scripts/), CI, a quarterly review process and checksummed releases.

## Quick start

> Use a **release** and verify its checksum ([details](docs/INSTALL.md#1-get-and-verify-a-release)). Do not run
> installers piped from the network.

### Claude Code

```bash
git clone --branch v1.0.0 https://github.com/webartisanratul/website-security-skill.git     # a released, pinned version
cd website-security-skill && scripts/install.sh --dest /path/to/your/project --target claude
```

This places the skill in `.claude/skills/website-security/` (commit it). Personal install:
copy the folder to `~/.claude/skills/`. Claude loads it when your request is security-sensitive web work, or run
`/website-security`.

### Claude.ai and Claude Desktop

Download `website-security-<version>.zip` from the [Releases](https://github.com/webartisanratul/website-security-skill/releases) page and
upload it in the skills settings (the ZIP's top level is the `website-security/` folder, as required).
[Step-by-step](docs/INSTALL.md#3-claudeai-and-claude-desktop).

### Other agents (AGENTS.md, Cursor, GitHub Copilot)

```bash
scripts/install.sh --dest /path/to/your/project --target agents,cursor,copilot
```

Copies the documents to `docs/security/` and adds a short, managed instruction block (or rule file) that points the
agent at the rules. [Details and limits](docs/INSTALL.md#4-agentsmd-cursor-and-github-copilot).

Preview any install with `--dry-run`; remove it with `--uninstall`. Files you modify are never overwritten by an
update (the new version is written beside them as `.new`).

## How an agent uses it

1. A security-sensitive request triggers the skill; the agent reads `AI_SECURITY_RULES.md`.
2. It **inspects the project** (stack, routes, data stores, CI, hosting) and writes a short **threat model**.
3. It **audits** the boundaries and reads only the relevant parts of the manual (routing table in `SKILL.md`).
4. It fixes root causes, adds a **regression test that fails before and passes after**, runs the tests, checks that
   normal behaviour still works.
5. It ends with a **Security Change Report** that separates *verified* from *inspected* and *assumed*.

More: [docs/USAGE.md](docs/USAGE.md) (prompt library, team practices, limits).

## Example prompts

```text
Audit this repository for security using the website-security skill. Inspect first and change nothing yet.
List public vs protected routes and findings with priority P0-P3, file references and what you could not verify.
```

```text
Implement avatar uploads using the skill's patterns for this stack. Start with a short threat model, add tests
including abuse cases, and report what is verified.
```

## Context budget

The manual is about 80,000 tokens and is **not** meant to be loaded whole: the agent loads the ~2,400-token rules
first, then only the sections a task needs. Sizes and guidance: [docs/INSTALL.md](docs/INSTALL.md#6-context-budget).

## Verification and its limits

Every release is checked by CI: PHP, Bash, JavaScript, YAML and JSON examples are linted; internal links and
anchors are validated; every OWASP cheat sheet URL is matched against the upstream index; versions, changelog and
review freshness are enforced; the installer has a regression suite; the release ZIP is reproducible. Library API
names used in examples were checked against upstream source, and several snippets were executed.

What has **not** been verified is listed explicitly (links that were not fetched, vendor facts that change,
integration testing in a full application): see [docs/VERIFICATION.md](docs/VERIFICATION.md). Volatile facts are
marked **⏱** in the text.

## Versioning and updates

[Semantic Versioning](https://semver.org/) applied to content (rules in [CHANGELOG.md](CHANGELOG.md)). The documents
are reviewed **at least quarterly** and whenever standards or major framework versions change: a scheduled
workflow opens a review issue, and `scripts/validate.py` warns when the last logged review is stale.
How maintainers (and Claude, as a research assistant under human review) run an update:
[docs/MAINTAINING.md](docs/MAINTAINING.md).

To update your project: check out the new release and rerun the installer with the same targets.

## Repository layout

```text
skill/website-security/   the distributable skill (SKILL.md + four documents)
adapters/                 instruction blocks for AGENTS.md, Cursor, Copilot (rendered by the installer)
scripts/                  install.sh, validate.py, lint_code_blocks.py, build_release.py, init.py, refresh_cheatsheet_index.py
tests/                    installer regression tests
data/                     OWASP cheat sheet index used by the validator
docs/                     INSTALL, USAGE, MAINTAINING, FAQ, VERIFICATION, ROADMAP, REVIEW_LOG
.github/                  CI, link check, review reminder, release workflows; issue and PR templates
```

## Using this as a template for your own repository

```bash
python3 scripts/init.py --owner YOUR_USER_OR_ORG --repo website-security-skill \
    --name "Your Name or Org" --contact security@yourdomain.example
```

then follow the [one-time setup](docs/MAINTAINING.md#1-one-time-repository-setup) (branch protection, security features).

## Contributing, security and conduct

- Contributions: [CONTRIBUTING.md](CONTRIBUTING.md) (primary sources, tested code, defensive only).
- Vulnerabilities in the tooling or release process, or guidance that could cause serious harm: [SECURITY.md](SECURITY.md).
- Community standards: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
- Questions: [docs/FAQ.md](docs/FAQ.md).

## Provenance

The initial content was drafted with Claude (Anthropic) and then checked with the tooling in this repository.
Maintainers are accountable for what is published; AI-assisted changes go through the same review and CI as any other.

## Licence and trademarks

[MIT](LICENSE). OWASP, Cloudflare, Laravel, Vue, Nginx, GitHub, Claude and other names are trademarks of their
respective owners; this project is not affiliated with or endorsed by them. Standards and vendor documents are
linked, not reproduced.
