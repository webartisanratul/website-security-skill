# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html), applied to content as defined below.

**Versioning of content**

- **MAJOR**: parts renumbered or removed; a mandatory rule in `AI_SECURITY_RULES.md` changed in a way that
  can alter agent behaviour; a previously recommended control reversed.
- **MINOR**: new sections, controls, recipes, checklist items, installer targets or tooling.
- **PATCH**: corrections, wording, link and reference updates, refreshed volatile facts without a change of meaning.

## [Unreleased]

## [1.0.0] - 2026-11-07

### Added

- `WEBSITE_SECURITY_SKILL.md`: universal web application security standard (Parts 0 to 18): attack taxonomy
  (12 families, 173 attacks) with mechanism, prevention, detection and verification; input validation standard;
  Cloudflare architecture; security headers; authentication and session design; API, database, frontend, server
  and supply-chain security; monitoring; testing; incident response; framework implementation; mandatory AI
  agent behaviour; prioritisation model; verified references.
- `AI_SECURITY_RULES.md`: short mandatory rules for AI coding agents.
- `SECURITY_AUDIT_CHECKLIST.md`: 13-domain audit checklist with risk, status, verification method and component.
- `SECURITY_IMPLEMENTATION_GUIDE.md`: Laravel, plain PHP, Vue, Nginx, Linux and Cloudflare recipes with a test
  and smoke-script harness.
- `SKILL.md`: agent skill entry point with a task-to-section routing table.
- Installer (`scripts/install.sh`) with Claude Code, AGENTS.md, Cursor and GitHub Copilot targets, safe updates,
  managed instruction blocks and uninstall.
- Tooling: repository validator, code-block linter, reproducible release builder, template initialiser,
  OWASP cheat-sheet index refresher.
- Project infrastructure: CI, scheduled link checking, quarterly review reminder, tag-driven releases with
  checksums, issue and pull request templates, contribution, conduct and security policies.

[Unreleased]: https://github.com/webartisanratul/website-security-skill/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/webartisanratul/website-security-skill/releases/tag/v1.0.0
