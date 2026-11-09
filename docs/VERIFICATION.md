# Verification

What was checked for release 1.0.0, how to reproduce it, and, just as important, what was **not** checked.
Reviewers: please treat the "not verified" list as work to do, not as a footnote.

## Reproduce the automated checks

```bash
python3 scripts/validate.py                              # structure, links, anchors, versions, review freshness
python3 scripts/lint_code_blocks.py --require-tools      # needs php, shellcheck, node, PyYAML
bash tests/test_install.sh                               # installer regression suite
python3 scripts/build_release.py --check                 # reproducible release ZIP (run twice: same checksum)
```

CI runs the same commands on every pull request and on release tags.

## What was verified

| Area | How | Result at 1.0.0 |
|---|---|---|
| Code examples | `scripts/lint_code_blocks.py` over every fenced block in the repository | 64 PHP (`php -l`), 33 Bash (`shellcheck -S warning`), 8 JavaScript (`node --check` as ES module), 3 YAML, 1 JSON: all pass |
| Nginx examples | Assembled into complete configurations with generated test certificates and run through `nginx -t` (nginx 1.24.0). Sets: the implementation-guide configuration (global settings, header snippet, catch-all, application and admin vhosts), the main manual's hardening configuration (global settings with the rate-limit map, header snippet, vhost), and the standalone fragments (catch-all, uploads location, timeouts block, Authenticated Origin Pulls vhost) | All pass. Test deviations: `http2 on;` removed (needs nginx 1.25.1 or newer) and IPv6 listeners removed (the test sandbox had no IPv6) |
| Library API names | Method, class and option names used in examples checked against upstream source: Laravel framework 13.40.0 (including `preventRequestForgery` and its deprecated aliases, `Vite::useCspNonce`, `Password::uncompromised`, `whereBelongsTo`, rate limiter and queue middleware, hashing options and `rehash_on_login`), Sanctum, Monolog 3 (`LogRecord::with`), firebase/php-jwt, pragmarx/google2fa (`verifyKeyNewer`), symfony/html-sanitizer, league/commonmark | All names exist as used. One documentation fix resulted: Laravel 13 names and options for request-forgery protection |
| Executed snippets | Run with PHP 8.3 against test inputs: safe-redirect validator (11 cases), SSRF address block-list (15 cases), control-character and filename helpers, path-traversal guard (9 cases including a symlink escape and a NUL byte), log redaction against the real Monolog `LogRecord`, the loan state machine, bounded regex matching | All behaved as documented |
| OWASP cheat sheets | All 71 cheat sheet URLs in the documents matched against the 137-entry upstream index (`data/owasp-cheatsheets.txt`, retrieved 2026-11-07) | All present; the validator re-checks on every run |
| Other references | The "verified" list in Part 18.1 contains only URLs returned by search or fetched during research; Cloudflare, OWASP and NIST entries were re-confirmed on 2026-11-07 and several links were corrected | See Part 18.1; everything else is in the separate "not fetched" list (18.2) |
| Claude install locations | Claude Code project and personal skill folders and the claude.ai ZIP requirements checked against Anthropic's documentation (2026-11-07) | Reflected in `docs/INSTALL.md` |
| Installer | 31 assertions: install, idempotency, update, user-edit protection, `--force`, managed blocks (create, append, replace, remove), multi-target installs, argument validation, uninstall | All pass |
| Workflows | `actionlint` 1.7.12 on all workflows; third-party actions pinned to commit SHAs resolved from upstream tags (releases at least 14 days old when pinned, 2026-11-07) | No findings |
| Link-checker configuration | `lychee` 0.24.2 parsed `.lychee.toml` and checked local links and fragments offline | No errors |
| Release build | ZIP structure check; fixed timestamps and ordering make the build reproducible | Passes |

Issues found and fixed during verification are recorded in the changelog and review log, for example a mis-scoped
rate-limit location in an Nginx example and several reference URLs.

## What was NOT verified

- **Integration.** No full Laravel (or Vue) application was run with these examples. They are linted, checked against
  upstream names, and selectively executed, but not integration-tested.
- **Not executed in the test environment:** archive extraction (needs the PHP zip extension) and the `intl`-based
  Unicode helpers.
- **Other agent tools.** The `AGENTS.md`, Cursor and Copilot adapters follow each tool's documented convention but were
  not tested in those tools. The Claude Code install and claude.ai upload were checked against documentation, not
  exercised end to end.
- **Links in the "not fetched" list (Part 18.2)** were not opened during authoring. The weekly link check tests
  reachability only, not content.
- **Vendor facts that change** (Cloudflare plan limits and dashboard names, tool flags, browser support) are marked ⏱.
  Plan limits were taken partly from secondary sources.
- **NIST SP 800-63B-4 details** (such as the 15-character single-factor minimum) were confirmed through secondary
  summaries; confirm against the primary text.
- **The March 2026 compromise of the Trivy GitHub Actions** (cited as a supply-chain example) is based on published
  incident coverage found during research, not on the vendor's post-mortem.
- **PowerShell commands** in `docs/INSTALL.md` were not run.
- **Manual harnesses** (Nginx with test certificates) are not part of CI.
- **Online link checking** was not run in the authoring environment (network restrictions); the scheduled workflow does it.

## How to report a problem

Use the *Inaccurate or unsafe guidance* issue form. If following the text could introduce a serious vulnerability,
report privately ([SECURITY.md](../SECURITY.md)).
