Scheduled quarterly review of the documents. Follow the update playbook in `docs/MAINTAINING.md` (section 3)
and log the result in `docs/REVIEW_LOG.md`. Tip: `docs/MAINTAINING.md` section 4 has ready-to-paste prompts for
doing the research with Claude; review every change yourself.

## Checklist

- [ ] Baseline: `python3 scripts/validate.py` and `python3 scripts/lint_code_blocks.py --require-tools`
- [ ] Sweep every ⏱ fact: `grep -n "⏱" skill/website-security/*.md` (Cloudflare plan limits and dashboard names, tool flags, edition numbers, browser support)
- [ ] Re-open all Part 18.1 links; try the Part 18.2 links and promote those that open
- [ ] `python3 scripts/refresh_cheatsheet_index.py --dry-run`, review added/removed/renamed entries, apply, rerun the validator
- [ ] Editions and standards: OWASP Top 10, API Top 10, ASVS, WSTG, CWE Top 25, NIST SP 800-63B and SSDF
- [ ] Laravel / Sanctum / Composer / npm / pnpm: new versions and any change to the APIs and settings used in examples
- [ ] Re-verify code examples against current library source or documentation
- [ ] Cloudflare: plan limits, dashboard naming, rule-language functions used in examples
- [ ] Tooling: Semgrep rule packs, Gitleaks commands, ZAP image, Trivy status
- [ ] Notable supply-chain or exploitation incidents since the last review (Part 10 and Part 1.L)
- [ ] GitHub Actions pins: merge Dependabot PRs or update SHAs (prefer releases at least 14 days old)
- [ ] Update the "Last reviewed" header date, `docs/REVIEW_LOG.md`, `CHANGELOG.md` and (if releasing) `VERSION`
- [ ] Human review of the final diff and of every new source claim
