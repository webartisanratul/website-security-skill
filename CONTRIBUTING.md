# Contributing

Thank you for helping keep this security guidance accurate. Quality matters more than volume: a wrong
recommendation in a security document is worse than a missing one.

## Ways to contribute

- **Report an inaccuracy, unsafe guidance or an outdated fact**: use the issue forms. Include the section, what is
  wrong and a primary source.
- **Propose new content**: a control, attack family, stack recipe or checklist item. Open an issue first for
  anything larger than a paragraph so scope can be agreed.
- **Fix tooling**: installer, scripts and workflows.
- **Review**: read a section against its sources and say what you verified.

Security vulnerabilities in the tooling or release process go through [SECURITY.md](SECURITY.md), not public issues.

## Content rules (these are enforced in review)

1. **Primary sources.** Cite official documentation or standards (OWASP, NIST, CWE, CISA, vendor docs, RFCs,
   framework docs). Blog posts can motivate a change but do not substitute for a primary source.
2. **Never invent.** No guessed URLs, version numbers, configuration keys, CVEs, package names or plan limits.
   If you could not open a source, say so in the pull request and put the link in the "not fetched" list in
   Part 18.2 of `WEBSITE_SECURITY_SKILL.md` rather than the verified list.
3. **Mark volatile facts with ⏱** (vendor plan limits, tool flags, edition numbers, browser support) and name the
   source next to them.
4. **Code must work.** PHP, Bash, JavaScript, YAML and JSON blocks must pass `python3 scripts/lint_code_blocks.py`.
   Configuration (Nginx, SQL, ini) should be tested against the real tool; say how in the pull request.
   Examples must be secure by default: no disabled TLS verification, no hard-coded secrets, no string-built SQL.
5. **Defensive only.** Describe mechanisms at the level defenders need. No working exploit chains, no
   instructions for attacking systems you do not own. Test examples use harmless canaries and are labelled
   "authorised targets only".
6. **Proportionality and neutrality.** Do not present Laravel, Vue, Nginx or Cloudflare as universal
   requirements; keep stack-specific content in clearly labelled sections. Do not add vendor endorsements.
7. **Explain trade-offs.** State what a control costs or can break (compatibility, false positives, operations).
8. **No false guarantees.** Never write that following the guidance makes a system "secure".
9. **Keep the agent rules short.** `AI_SECURITY_RULES.md` is loaded into agent context; additions must be
   actionable, testable and necessary. Detail belongs in the long documents.

## Development setup

Requirements: Python 3.9+, and for full linting `php` (CLI), `shellcheck`, `node` and the PyYAML package.

```bash
python3 scripts/validate.py                       # structure, links, anchors, versions, review freshness
python3 scripts/lint_code_blocks.py               # code blocks in every Markdown file
bash tests/test_install.sh                        # installer regression tests
python3 scripts/build_release.py --skip-validate --check
```

CI runs the same commands on every pull request.

## Pull request checklist

- [ ] Change is described and linked to an issue where one exists
- [ ] Sources cited for every new or changed factual claim; ⏱ tags added where needed
- [ ] `python3 scripts/validate.py` and `python3 scripts/lint_code_blocks.py` pass
- [ ] Table of contents and cross-references updated if headings changed
- [ ] `CHANGELOG.md` updated under `[Unreleased]` using the versioning rules in that file
- [ ] If the change alters a rule in `AI_SECURITY_RULES.md`, the reason and expected agent-behaviour change are explained
- [ ] No secrets, personal data or real hostnames

## Commit messages

Short imperative summary, optional body. Prefixes such as `docs:`, `fix:`, `feat:`, `ci:`, `tooling:` are welcome.

## AI-assisted contributions

AI assistance is allowed and used in this project. The submitter is fully responsible for the contribution:
disclose substantial AI assistance in the pull request, verify every claim and link yourself, and run the
checks. Pull requests with fabricated references or untested code will be closed.

## Releases

Maintainers cut releases following [docs/MAINTAINING.md](docs/MAINTAINING.md). Contributors do not need to bump
versions; add notes under `[Unreleased]` in the changelog.

## Licence

By contributing you agree that your contribution is licensed under the repository's [MIT licence](LICENSE).
Be kind: see the [Code of Conduct](CODE_OF_CONDUCT.md).
