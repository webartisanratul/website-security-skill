# Maintaining the repository

How releases are cut, how the content is kept current, and how to use Claude to do the update work. The goal is
a document set that stays accurate: security guidance that ages silently is a liability.

- [1. One-time repository setup](#1-one-time-repository-setup)
- [2. Update cadence](#2-update-cadence)
- [3. Update playbook](#3-update-playbook)
- [4. Updating with Claude](#4-updating-with-claude)
- [5. Releasing](#5-releasing)
- [6. Keeping the repository itself secure](#6-keeping-the-repository-itself-secure)

## 1. One-time repository setup

1. **Create the repository** (public). Suggested name `website-security-skill`; description *"Verified web application
   security standard, audit checklist and implementation recipes for AI coding agents and developers"*; topics such
   as `security`, `appsec`, `owasp`, `ai-agents`, `agent-skills`, `claude-code`, `laravel`, `cloudflare`, `devsecops`.
2. **Fill in the placeholders** and commit:

   ```bash
   python3 scripts/init.py --owner YOUR_USER_OR_ORG --repo website-security-skill \
       --name "Your Name or Org" --contact security@yourdomain.example
   git diff            # review
   git add -A && git commit -m "chore: initialise repository"
   ```

3. **Review the content yourself** once, then edit the first row of `docs/REVIEW_LOG.md` to say so.
4. **Settings to enable** (these mirror the repository's own supply-chain guidance):
   - Actions > General > *Workflow permissions*: read-only by default; require approval for workflows from
     outside contributors; restrict allowed actions to GitHub-authored ones plus the pinned ones in use.
   - A branch ruleset on `main`: pull request required, at least one approval, required status check
     `validate`, no force pushes, resolved conversations. A tag ruleset for `v*` so only maintainers can create
     release tags.
   - Security: private vulnerability reporting, Dependabot alerts and security updates, secret scanning with push
     protection.
   - Two-factor authentication (passkeys or security keys preferred) for every maintainer.
   - Labels used by the automation: `maintenance`, `link-check`, `dependencies`, `inaccuracy`, `outdated`,
     `enhancement`, `tooling`.
5. **Push the first release** (section 5).

## 2. Update cadence

| Trigger | Action |
|---|---|
| **Every quarter** (a reminder issue opens on 1 Jan, Apr, Jul, Oct) | Full update playbook (section 3). Log it in `docs/REVIEW_LOG.md`. |
| New edition of OWASP Top 10, API Top 10, ASVS, WSTG, CWE Top 25, NIST SP 800-63B or SSDF | Update mappings, Part 12 and Part 18; MINOR or MAJOR version. |
| New major version of Laravel, Sanctum, Composer, Node/npm/pnpm | Re-verify API names and settings against the source; update recipes. |
| Cloudflare plan or dashboard changes | Update Part 3 tables (⏱) and the implementation guide section 11. |
| A notable supply-chain or tooling incident | Update Part 10 and L; check every tool the docs recommend. |
| Weekly link check fails | Fix or move the link (verified list vs not-fetched list). |
| A user issue reports inaccurate or unsafe guidance | Treat as high priority; fix, add a regression note to the changelog. |
| `validate.py` warns the last review is older than 100 days | Run the playbook. |

## 3. Update playbook

Work on a branch named `review/YYYY-Qn`.

1. **Baseline.** `python3 scripts/validate.py` and `python3 scripts/lint_code_blocks.py --require-tools`.
2. **Sweep volatile facts.** `grep -n "⏱" skill/website-security/*.md`. For each hit, open the named primary
   source, confirm or correct, and keep the ⏱ marker.
3. **Re-verify references.** Re-open every link in Part 18.1. Try the Part 18.2 "not fetched" links: move those you can
   open to 18.1. `python3 scripts/refresh_cheatsheet_index.py --dry-run`, review the diff (added, removed,
   renamed), then apply and rerun `validate.py`. Trigger the *Links* workflow manually.
4. **Check editions and versions.** OWASP Top 10, API Top 10, ASVS (and its ID format), WSTG, CWE Top 25, NIST SP
   800-63B and SSDF status; latest Laravel version; the Composer, npm and pnpm settings the docs use.
5. **Re-verify code against sources.** For each library API used in examples (Laravel, Sanctum, Monolog, php-jwt,
   google2fa, html-sanitizer, commonmark) confirm the method and option names in the current source or documentation.
   Re-run the lint and any manual harness you rely on (Nginx `nginx -t` with test certificates).
6. **Cloudflare and tools.** Re-check plan limits, dashboard names, rule-language functions used in examples,
   Semgrep rule packs, Gitleaks commands, the ZAP image name, Trivy status.
7. **Incidents since last review.** Add or update notable supply-chain or exploitation events and their lessons.
8. **GitHub Actions pins.** Merge Dependabot pull requests, or resolve new commit SHAs (prefer releases at least
   14 days old) and update the version comments.
9. **Record.** Update the "Last reviewed" line in the header of `WEBSITE_SECURITY_SKILL.md`, add a row to
   `docs/REVIEW_LOG.md`, add changelog entries, and bump the version if you are releasing.
10. **Verify and review.** Re-run all checks, open the pull request, have a human review the diff and every source
    claim, then merge.

## 4. Updating with Claude

Claude can do the research-heavy parts of the playbook, but be clear about how that works:

- **Claude does not run on a schedule, does not watch your repository, and cannot push to GitHub for you.** You start
  each update session and give Claude the current files; you review and commit what comes back.
- **Claude can search the web (when search is enabled) to re-verify sources, and can run the repository's scripts
  when it has a code-execution environment.** Anything it cannot open or run must be reported as unverified.
  Never accept a link, version number or plan limit that Claude cannot show you a source for.
- Two good setups:
  1. **Claude Code in a clone** of the repository: Claude edits files, runs `validate.py`, the linter and the tests,
     and prepares a branch and commit; you push and open the pull request.
  2. **Claude.ai with code execution**: upload a ZIP of the repository (or the `skill/` folder plus `scripts/`),
     ask for the update, and receive the changed files; apply them in a clone and run the checks yourself.
- The quarterly reminder issue contains the checklist; paste it into the session.

**Prompt: quarterly review**

```text
You are maintaining the website-security-skill repository (attached; current version <X.Y.Z>). Run the update
playbook in docs/MAINTAINING.md section 3 for this quarter.

Rules:
- Re-verify every ⏱-tagged fact and every link in Part 18 against primary sources by searching and opening them.
  Do not rely on memory. If you cannot open a source, say so and move the link to the "not fetched" list.
- Re-verify code examples against current library source/docs; run scripts/validate.py and
  scripts/lint_code_blocks.py and report the results.
- Do not invent URLs, versions, configuration keys, plan limits or CVEs.
- Keep changes minimal and proportionate; do not rewrite sections that are still correct.

Output: (1) findings table: item, old value, new value, source URL, confidence; (2) the full changed files or
unified diffs; (3) a CHANGELOG entry with the correct SemVer bump; (4) a docs/REVIEW_LOG.md row; (5) a list of
everything you could not verify.
```

**Prompt: add a topic or stack recipe**

```text
Add <topic, e.g. "Node.js/Express session and CSRF recipe"> to the repository following CONTRIBUTING.md content
rules: primary sources only, ⏱ tags for volatile facts, tested code, defensive only, proportionate and stack-labelled.
Show where it fits in the table of contents and the SKILL.md routing table. Run the validators. Provide the
diff, a CHANGELOG entry (MINOR), and what you could not verify.
```

**Prompt: triage an issue**

```text
Here is a reported inaccuracy: <paste issue>. Check it against primary sources. Say whether it is correct, partially
correct or wrong, with source links. If correct, give the minimal fix as a diff, a CHANGELOG entry (PATCH unless
it changes a mandatory rule), and say whether it could have caused an insecure implementation if followed.
```

**Prompt: review a contributor pull request**

```text
Review this pull request against CONTRIBUTING.md content rules. Check each factual claim and link yourself, flag
anything you cannot verify, look for insecure example code, anything that weakens a rule in
AI_SECURITY_RULES.md, and missing changelog/TOC updates. Give blocking issues and suggestions separately.
```

Treat every Claude-produced change like any other contribution: human review, CI green, sources checked.

## 5. Releasing

```bash
git checkout -b release/vX.Y.Z
# 1. VERSION            -> X.Y.Z
# 2. skill/website-security/WEBSITE_SECURITY_SKILL.md header -> "Version X.Y.Z" and "Last reviewed <date>"
# 3. CHANGELOG.md       -> move [Unreleased] entries under "## [X.Y.Z] - <date>" and update the link references
# 4. docs/REVIEW_LOG.md -> add a row if content was reviewed
python3 scripts/validate.py --release
python3 scripts/lint_code_blocks.py --require-tools
bash tests/test_install.sh
python3 scripts/build_release.py --check      # builds dist/, prints the checksum
# open a pull request, merge, then tag the merge commit:
git checkout main && git pull
git tag -s vX.Y.Z -m "vX.Y.Z"                 # -s signs the tag if you have signing configured; otherwise use -a
git push origin vX.Y.Z
```

Pushing the tag triggers `.github/workflows/release.yml`: it verifies the tag equals `VERSION`, re-runs the checks,
builds the ZIP and `SHA256SUMS`, and publishes a GitHub release with the changelog section as notes. Afterwards:

- Download the release assets and run `sha256sum -c SHA256SUMS`.
- Rebuild locally from the tag (`python3 scripts/build_release.py`): the checksum must match (the build is reproducible).
- Try the ZIP in a claude.ai test upload and a Claude Code project install.

## 6. Keeping the repository itself secure

The repository distributes instructions that agents follow, so it is a supply-chain target.

- Branch and tag protection, required review, required checks, two-factor authentication (section 1).
- Workflows use least-privilege tokens, SHA-pinned third-party actions and no untrusted input in shell commands;
  Dependabot proposes pin updates. Review those pull requests (check the upstream release, not only the diff).
- No secrets are needed by CI. If you ever add one, scope it to a protected environment.
- Review pull requests that touch `AI_SECURITY_RULES.md`, `scripts/` or `.github/` with extra care: a subtle change
  in the rules changes agent behaviour in every project that installs them.
- Ship only built, checksummed releases; tell users to pin versions (see [SECURITY.md](../SECURITY.md)).
