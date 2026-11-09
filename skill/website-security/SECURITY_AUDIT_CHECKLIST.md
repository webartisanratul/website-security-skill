# SECURITY_AUDIT_CHECKLIST.md

Reusable security audit checklist. Copy this file into the project (for example `docs/security/audit-YYYY-MM-DD.md`) and fill it in per audit. Reference material: `WEBSITE_SECURITY_SKILL.md` (section numbers in the **Ref** column). Priorities: `WEBSITE_SECURITY_SKILL.md` Part 17.

## How to use

1. Complete the **Audit header** and the **Applicability screen** first. Mark whole sections `[n/a]` with a reason when the architecture does not include the component (no uploads, no payments, no Cloudflare, and so on).
2. For every item set a **Status** and fill **Verification**. An item is `[x]` only when the verification method was actually performed and its result recorded. "Looks fine" is not verification.
3. Findings (`[ ]` or `[~]` on a Critical/High item) become tracked issues with a priority (P0 to P3) and an owner.
4. Anything you could not inspect (no server access, no staging) is recorded under **Not verified** at the end, never silently assumed.

**Status key:** `[ ]` not done · `[~]` partial · `[x]` done and verified · `[n/a]` not applicable (reason) · `[!]` risk accepted (approver, date, expiry)
**Risk key:** **C**ritical · **H**igh · **M**edium · **L**ow (impact if unmet on a typical exposed application)

## Audit header

```text
Application / repo:            Environment audited (prod/staging/local):
Date:                          Auditor (human or agent):
Stack (framework+versions, runtime, DB, web server, CDN/WAF, hosting):
Data classes handled (credentials / personal / financial / regulated / none):
Access available (code / staging / prod config / logs / CI):
Target assurance (ASVS level 1/2/3):
```

## Applicability screen

| Question | Yes / No | If yes, sections that apply |
|---|---|---|
| Cookie-based authentication? | | Authentication, Backend (CSRF) |
| Public or partner API? | | APIs |
| File uploads or user-supplied files? | | File uploads |
| Money, credit, inventory, entitlements, approvals? | | Payments |
| Multi-tenant (several customers in one deployment)? | | Authorization (tenant scoping) |
| Behind Cloudflare or another CDN/WAF? | | Cloudflare, Infrastructure (origin lock) |
| SPA or heavy client-side JavaScript? | | Frontend |
| Admin or staff interface? | | Authentication (admin), Authorization |
| Webhooks or server-side fetching of URLs? | | APIs, Backend |
| Self-managed server (not fully managed PaaS)? | | Infrastructure, Deployment |

---

## 1. Frontend

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| FE-01 | No untrusted data reaches dangerous sinks (`innerHTML`, `v-html`, `dangerouslySetInnerHTML`, `eval`, `bypassSecurityTrust*`) without an allowlist sanitiser | C | [ ] | Grep for sinks (Part 15.5); test with a harmless marker in every user-controlled field | | 1.B, 8.1 |
| FE-02 | URLs bound to `href`/`src`/`action` are scheme-validated (no `javascript:`/`data:` from users) | H | [ ] | Test with `javascript:`, `//host`, `data:` values | | 8.1 |
| FE-03 | No long-lived auth tokens in `localStorage`/`sessionStorage`/JS-readable cookies | H | [ ] | Inspect storage after login in devtools; review auth code | | 5.1, 8.7 |
| FE-04 | No secrets or private keys in client bundles, source maps or HTML comments | C | [ ] | Secret scan of built output (`dist/`); grep for key patterns; check public source maps | | 8.4 |
| FE-05 | Strict CSP in place (nonce/hash, no `unsafe-inline`/`unsafe-eval` in `script-src`), enforcing or in report-only with a dated plan | H | [ ] | Inspect response header; devtools Console for violations; CSP evaluator | | 4.2 |
| FE-06 | Third-party scripts inventoried, minimal, none on login/payment pages, SRI on CDN assets | H | [ ] | Per-page network inventory vs approved list; `integrity` attributes present | | 1.I, 8.5 |
| FE-07 | External links use `rel="noopener noreferrer"`; `postMessage` handlers check exact `event.origin` | M | [ ] | Grep `target="_blank"` and `addEventListener('message'` | | 1.I |
| FE-08 | Client-side errors show generic messages with a correlation ID; error reporting scrubs tokens/PII | M | [ ] | Trigger errors; inspect UI and error-tracker payload | | 8.6 |
| FE-09 | Client-side validation is treated as UX only (server re-validates) | H | [ ] | Bypass the UI with a direct request and invalid data | | 2.7 |
| FE-10 | Client dependencies locked, audited, scripts disabled in CI install | H | [ ] | `npm ci --ignore-scripts`; `npm audit --omit=dev`; `npm audit signatures` | | 10.2 |
| FE-11 | Frontend route guards are not the only protection (API enforces authorisation) | C | [ ] | Call admin APIs directly with a low-privilege session | | 8.2 |
| FE-12 | CORS: only exact origins allowed, no wildcard with credentials | H | [ ] | Preflight with a foreign `Origin` | | 8.3, 1.D |

## 2. Backend

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| BE-01 | All SQL uses bindings; identifiers (sort/columns) allowlisted; raw fragments reviewed | C | [ ] | Grep `*Raw`/`DB::statement`; lone-quote test on every parameter | | 1.A |
| BE-02 | Every write endpoint validates input server-side (types, lengths, enums, array/JSON depth limits) | H | [ ] | Negative-test suite (Part 2.9); Form Requests exist per endpoint | | 2 |
| BE-03 | Output encoded per context; raw output only after allowlist sanitisation | C | [ ] | Marker test in all stored fields incl. admin, exports, emails | | 1.B |
| BE-04 | CSRF/request-forgery protection active on cookie-authenticated state changes; exceptions only for signature-verified routes | H | [ ] | Replay POST without token/foreign origin; review exclusion list | | 1.B, B.4 |
| BE-05 | No `eval`/dynamic include/`unserialize` of untrusted data; no shell execution with user data | C | [ ] | Grep (Part 15.5); code review | | 1.A, 1.E |
| BE-06 | Mass assignment guarded (`$fillable`/validated-only); privileged fields never bound from requests | H | [ ] | Extra-field test (`role`, `balance`, `owner_id`) | | C.2 |
| BE-07 | Server-side URL fetching restricted (allowlist, IP checks, no redirects, egress limits) | H | [ ] | SSRF tests in staging with internal/metadata targets | | E.1 |
| BE-08 | XML parsing disables DTD/entities; archives extracted with path/size/ratio checks | H | [ ] | Hostile DTD/zip samples in staging | | E.3 |
| BE-09 | Redirect targets validated (same-site paths or exact allowlist) | M | [ ] | Test external URL, `//host`, `/\host`, `javascript:` | | B.5 |
| BE-10 | Errors do not leak internals; `APP_DEBUG` off; correlation ID returned | H | [ ] | Induce 404/422/500; inspect bodies; `php artisan about` | | 6.6 |
| BE-11 | Trusted host and canonical URL configured; links/emails never built from request `Host` | M | [ ] | Forged `Host` password-reset test | | G.1 |
| BE-12 | Security headers set once, correctly, on all responses including errors | M | [ ] | `curl -I` on `/`, a 404, a redirect; header test in CI | | 4 |
| BE-13 | Rate limiting on login, reset, OTP, registration, search, export, expensive endpoints | H | [ ] | Exceed limits in staging; confirm 429 and correct keying behind proxies | | C.3, 6.3 |
| BE-14 | Queue jobs bounded (timeout, tries, backoff, rate limit); payloads contain no secrets | M | [ ] | Review job classes; inspect a payload | | K.2 |
| BE-15 | Cryptography uses vetted libraries; no custom crypto; `APP_KEY`/keys protected and rotation plan exists | H | [ ] | Review crypto usage; confirm key storage | | 7.3 |

## 3. APIs

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| API-01 | Route inventory exists; every protected route requires authentication; public routes are an explicit list | C | [ ] | `route:list` vs inventory; unauthenticated call to each protected route | | 6.1 |
| API-02 | Per-object authorisation (BOLA) on every route taking an identifier | C | [ ] | Two-account matrix test | | C.1 |
| API-03 | Per-function authorisation (BFLA); admin routes inaccessible to normal users | C | [ ] | Role × route test | | 1.C |
| API-04 | Responses use allowlisted resources/DTOs (no raw models, no hashes/tokens) | H | [ ] | Response-schema test; field diff | | D.1 |
| API-05 | Pagination capped; filters/sorts allowlisted; body-size and `Content-Type` enforced | H | [ ] | Oversize, huge `per_page`, wrong content type | | 6.4 |
| API-06 | Webhooks verify HMAC over raw body with timestamp window and event-ID de-duplication | C | [ ] | Bad signature, stale timestamp, replay tests | | D.2 |
| API-07 | Idempotency keys or unique references on money-moving/creating endpoints | H | [ ] | Duplicate-submission test | | 6.5 |
| API-08 | API keys/tokens hashed at rest, scoped, expiring, rotatable, never in URLs or logs | H | [ ] | Review storage; rotation drill; grep logs | | 6.7 |
| API-09 | Deprecated/old API versions and debug/docs endpoints removed or protected | M | [ ] | Route diff; probe `/v0`, `/debug`, `/telescope`, `/docs` | | D.3 |
| API-10 | GraphQL (if used): introspection off in prod, depth/complexity/alias limits, field-level auth | H | [ ] | Introspection and nested-query tests in staging | | D.3 |
| API-11 | Outbound API consumption validates responses, uses timeouts and TLS verification | M | [ ] | Review client code; malformed-response test | | 1.D |
| API-12 | Audit log for sensitive API operations with correlation ID, no secrets | H | [ ] | Perform actions; inspect logs | | 6.8 |

## 4. Authentication

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| AU-01 | Passwords hashed with Argon2id (or bcrypt cost 12+); never reversible; rehash on login | C | [ ] | Inspect hashing config and a stored hash prefix | | 5.2 |
| AU-02 | Password policy: length-first (15 minimum when single factor), no composition rules, no forced rotation, breached-password check | H | [ ] | Register with short/breached/long passphrases | | 5.2 |
| AU-03 | Login throttling by account and IP plus global budget; uniform failure messages | H | [ ] | Exceed limits; compare responses for known/unknown accounts | | C.3, C.4 |
| AU-04 | Session ID regenerated on login/privilege change; invalidated server-side on logout and password change | C | [ ] | Compare cookie before/after login; reuse old session after logout | | 5.6 |
| AU-05 | Session cookie `HttpOnly`, `Secure`, `SameSite` set; idle and absolute lifetimes enforced | H | [ ] | Inspect `Set-Cookie`; wait/force timeouts | | 5.6 |
| AU-06 | Password reset: single-use hashed short-lived tokens, generic responses, no host-header poisoning, revokes sessions | C | [ ] | Reuse token; forged `Host`; check sessions after reset | | 5.3 |
| AU-07 | MFA available for all users and mandatory for admin/staff (passkeys preferred); recovery codes hashed and single-use; OTP attempts limited | H | [ ] | Attempt access post-step-1 only; OTP brute-force limit test | | 5.4 |
| AU-08 | Step-up authentication for sensitive actions (credentials, payees, disbursements, exports, role changes) | H | [ ] | Perform actions with a stale session | | 5.4 |
| AU-09 | New-device/suspicious login detection and user notification | M | [ ] | Log in from a new browser; confirm notice | | 5.7 |
| AU-10 | Remember-me tokens hashed, rotated, revocable, short-lived; disabled for admin/financial roles | M | [ ] | Review implementation; logout/password change revokes | | 5.6 |
| AU-11 | JWT (if used): fixed algorithm, all claims validated, short expiry, refresh rotation with reuse detection, no tokens in web storage | H | [ ] | Tampered/`none`/expired/wrong-audience tokens rejected | | 5.9 |
| AU-12 | Admin authentication separate and hardened (network restriction + phishing-resistant MFA + shorter lifetimes) | C | [ ] | Review admin exposure and MFA enforcement | | 5.8 |
| AU-13 | Email verification before sensitive features; unverified accounts constrained | M | [ ] | Attempt actions with an unverified account | | 5.3 |

## 5. Authorization

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| AZ-01 | Deny by default: new routes/actions require explicit policy or role | C | [ ] | Add a route without policy in a test; confirm denied or flagged | | 15.2 |
| AZ-02 | Object-level scoping in queries (tenant/owner) plus policy checks | C | [ ] | Cross-tenant tests for read/update/delete/list/export | | C.1 |
| AZ-03 | Tenant isolation enforced at the data layer (global scopes/row-level) | C | [ ] | Query without controller checks still returns only own tenant | | C.1 |
| AZ-04 | Roles/permissions server-side; role fields not mass-assignable; changes audited | C | [ ] | Mass-assignment test; audit entries | | C.2 |
| AZ-05 | Maker-checker on high-risk approvals (initiator ≠ approver, server-enforced) | H | [ ] | Attempt self-approval | | H.2 |
| AZ-06 | Authorisation applies to every channel: web, API, exports, downloads, WebSockets, queues, CLI/admin tools | H | [ ] | Test each channel with an unauthorised identity | | 1.C |
| AZ-07 | Super-admin/`Gate::before` shortcuts are narrow, audited and alerting | H | [ ] | Review bypass logic and logs | | C.1 |
| AZ-08 | Authorisation regression tests exist for every sensitive resource | H | [ ] | Test names and CI results | | 12.4 |

## 6. Database

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| DB-01 | Database not reachable from the internet; firewall limits to application hosts | C | [ ] | External port scan of the DB host; firewall rules | | 7.1 |
| DB-02 | Separate runtime, migration, reporting, backup and human accounts; runtime user has DML only | H | [ ] | `SHOW GRANTS` for each account | | 7.1 |
| DB-03 | TLS enabled and verified for application/replica connections | H | [ ] | Check connection options and server `REQUIRE SSL` | | 7.3 |
| DB-04 | Sensitive fields encrypted at rest at field level where warranted; card data never stored | H | [ ] | Inspect a staging dump; review schema | | J.1 |
| DB-05 | Append-only enforcement for ledger/audit tables (grants/triggers) | H | [ ] | Attempt UPDATE/DELETE as the runtime user | | 7.1 |
| DB-06 | Slow-query, failed-login, grant-change and DDL monitoring/alerts | M | [ ] | Trigger a test event; confirm alert | | 7.5 |
| DB-07 | Migrations reviewed, run by pipeline with migration user, expand/contract for destructive changes | M | [ ] | Review process and last migrations | | 7.6 |
| DB-08 | No direct production access by default; access time-limited, logged, MFA-gated | H | [ ] | Review access list and logs | | 7.7 |
| DB-09 | Integrity: unique constraints/foreign keys/checks back business invariants | H | [ ] | Schema review against invariants | | H.1 |
| DB-10 | DB hardening baseline (no default/anonymous users, local-infile off unless needed, sane bind address) | M | [ ] | Run vendor hardening checklist | | J |

## 7. File uploads

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| UP-01 | Extension and content-type allowlist validated from file content (magic bytes), not client MIME | H | [ ] | Upload renamed executables/scripts | | F.1 |
| UP-02 | Stored under random server-generated names and extension; client filename only as display metadata | H | [ ] | Upload traversal/double-extension names | | F |
| UP-03 | Storage outside web root or non-executable; PHP/script execution denied in upload paths | C | [ ] | Request an uploaded `.php`-named file: must not execute | | F.2 |
| UP-04 | Images re-encoded; pixel/dimension and size limits enforced before decode | M | [ ] | Oversized/polyglot samples | | F.1 |
| UP-05 | SVG rejected, sanitised, or served as attachment from a sandboxed origin | H | [ ] | SVG with script marker | | F |
| UP-06 | Downloads go through an authorising controller with correct `Content-Type`, `nosniff`, `Content-Disposition` | H | [ ] | Fetch another user's file; inspect headers | | F.2 |
| UP-07 | Archive handling prevents zip-slip, symlinks, bombs | H | [ ] | Hostile archive in staging | | E.3 |
| UP-08 | Size/rate/quota limits consistent across Nginx, PHP, app, edge; orphan cleanup | M | [ ] | Limit+1 test at each layer | | F.3 |
| UP-09 | Malware scanning (AV) of uploads where users share files | M | [ ] | EICAR test in staging | | F |

## 8. Payments and financial logic

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| PY-01 | All prices, totals, discounts and fees computed server-side from trusted data | C | [ ] | Tamper request amounts; server overrides/rejects | | H.1 |
| PY-02 | Payment success confirmed server-to-server or via verified webhook; amount, currency, order matched | C | [ ] | Fake success redirect; underpay test | | 1.H |
| PY-03 | Money stored as integer minor units or fixed-precision decimals; one rounding policy | H | [ ] | Schema review; rounding tests | | H.2 |
| PY-04 | Atomic operations with locking/conditional updates; no read-then-write on balances/stock | C | [ ] | Parallel-request test (H.4) | | H.1, H.2 |
| PY-05 | Idempotency keys/unique references on all value-moving operations | C | [ ] | Duplicate submission and webhook redelivery | | 6.5 |
| PY-06 | Explicit state machine; illegal transitions rejected | H | [ ] | Call later-step endpoints directly | | H.3 |
| PY-07 | Append-only ledger; balances reconciled on a schedule; breaks alert | H | [ ] | Reconciliation report; trigger test | | H.2 |
| PY-08 | Coupons/credits/refunds/referrals: single-use constraints, caps, stacking rules, velocity limits | H | [ ] | Parallel redemption; over-refund test | | 1.H |
| PY-09 | Maker-checker and limits on disbursements/refunds/write-offs | H | [ ] | Attempt self-approval; exceed limits | | H.2 |
| PY-10 | Card data handled only by the provider's hosted fields/redirect; no card numbers/CVV stored or logged | C | [ ] | Inspect DB, logs, network; review scope with assessor | | 1.I, 7.3 |
| PY-11 | Payment pages: no third-party scripts beyond the provider; script change monitoring | H | [ ] | Page script inventory; CSP | | 1.I |
| PY-12 | Full audit trail for financial mutations (who, what, before/after, when, where) | H | [ ] | Perform and trace a transaction | | 11.5 |

## 9. Infrastructure

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| IN-01 | TLS 1.2+ only (1.3 preferred); valid certificates with automated renewal and expiry alerts | H | [ ] | `testssl.sh`; renewal job and alert test | | 9.5, G |
| IN-02 | HTTP redirects to HTTPS; HSTS rolled out via staged ramp | M | [ ] | `curl -I http://…`; header value | | 4.3 |
| IN-03 | Default-deny firewall; SSH restricted; DB/cache ports private | C | [ ] | External scan; `ufw status` | | 9.4 |
| IN-04 | SSH: key-only, no root login, allowlisted users, MFA/VPN where possible | H | [ ] | `sshd -T` review | | 9.3 |
| IN-05 | Web process runs non-root; code read-only to the web user; per-site users and PHP-FPM pools | H | [ ] | `ps`, file ownership/permissions review | | 9.2, 9.6 |
| IN-06 | `.env`, `.git`, backups, logs, `vendor/` not web-reachable; directory listing off | C | [ ] | `curl -I` each path (403/404) | | 9.5, 9.7 |
| IN-07 | Only the front controller executes PHP; uploads cannot execute | C | [ ] | Request a stray `.php` under `public/` or uploads | | 9.5 |
| IN-08 | PHP production settings (`display_errors` off, `expose_php` off, `allow_url_include` off; execution functions disabled where compatible) | M | [ ] | `php -i`/FPM pool review | | 9.6 |
| IN-09 | Automatic security updates; patch SLAs per priority; EOL runtimes tracked | H | [ ] | `unattended-upgrades` status; version inventory | | 9.4, 17 |
| IN-10 | Default catch-all vhost; trusted hosts; direct-IP/unknown-Host requests refused | M | [ ] | Request by IP and with foreign `Host` | | G.1 |
| IN-11 | Request size, timeout and connection limits configured | M | [ ] | Config review; slow-request test in staging | | G.2 |
| IN-12 | Cron/queue workers run as site user with limits; crontabs reviewed for unknown entries | M | [ ] | Review crontabs/systemd units | | 9.8 |
| IN-13 | Containers (if used): non-root, read-only FS, dropped capabilities, no Docker socket mounts, patched base images | H | [ ] | Container scan and runtime config review | | L |
| IN-14 | Cloud metadata hardened (IMDSv2/equivalent), minimal instance roles, egress controls | H | [ ] | Platform settings review | | E.1, L |
| IN-15 | DNS/registrar: MFA, registrar lock, CAA, DNSSEC, no dangling records | H | [ ] | Registrar/DNS audit; record review | | G, 3.6 |

## 10. Cloudflare (if used)

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| CF-01 | All web hostnames proxied; no DNS-only record exposing the origin IP | H | [ ] | DNS record review; historical-DNS/IP leak check | | 3.4 |
| CF-02 | SSL/TLS mode **Full (strict)** with valid origin certificate (never Flexible) | C | [ ] | Dashboard setting; origin cert chain check | | 3.2 |
| CF-03 | Origin only reachable via Cloudflare: Tunnel, or AOP with your own certificate, plus firewall to Cloudflare ranges | C | [ ] | Direct-to-IP request with the site `Host` fails | | 3.4 |
| CF-04 | Real visitor IP restored (`CF-Connecting-IP`) only after origin is locked; rate limits keyed on the real IP | H | [ ] | Forged header test; logs show real IPs | | 3.4.2 |
| CF-05 | Managed WAF rules enabled and tuned (log-first for new rules); custom rules for sensitive paths | H | [ ] | Ruleset deployment review; Security Events | | 3.5 |
| CF-06 | Rate limiting on login/reset/OTP/search/checkout (within plan limits) plus origin-side limits | H | [ ] | Test limits; review rules | | 3.3 |
| CF-07 | Bot controls configured with machine-traffic exceptions understood (webhooks/APIs/cron not blocked) | M | [ ] | Webhook delivery test from provider; uptime monitor | | 3.6 |
| CF-08 | Cache rules cache only static assets; authenticated/personalised pages bypass cache | H | [ ] | Request authenticated pages; check `cf-cache-status` and `Cache-Control` | | 3.6, G |
| CF-09 | Turnstile (or equivalent) verified **server-side** on abuse-prone forms | M | [ ] | Submit without/with invalid token | | 3.7 |
| CF-10 | DNSSEC enabled with DS at registrar; CAA records set | M | [ ] | DNSSEC validator; `dig CAA` | | G |
| CF-11 | Cloudflare account: MFA (security key), scoped API tokens, audit-log alerts, no shared logins | C | [ ] | Account security review | | 3.6 |
| CF-12 | Security events exported/retained and alerted on; Under Attack Mode runbook exists | M | [ ] | Log push config; runbook review | | 11, G.3 |
| CF-13 | Plan-dependent features verified against current Cloudflare documentation ⏱ | L | [ ] | Date and source of verification recorded | | 3.2 |

## 11. Monitoring and logging

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| MO-01 | Authentication, authorisation-failure, privilege-change and admin events logged in structured form | H | [ ] | Trigger each; inspect log entries | | 11.2 |
| MO-02 | No secrets in logs (passwords, tokens, cookies, OTPs, card data, auth headers) | C | [ ] | Redaction test; grep recent logs | | 11.4 |
| MO-03 | Centralised log shipping over TLS; retention set; access controlled; ingestion-stopped alert | H | [ ] | Pipeline test; retention config | | 11.6 |
| MO-04 | Alerts with owners/runbooks for credential stuffing, admin anomalies, WAF spikes, FIM changes, DB anomalies, payment anomalies, failed webhook signatures | H | [ ] | Fire a test of each (drill) | | 11.2, 11.3 |
| MO-05 | File-integrity monitoring on code and web root; deploy windows suppress noise | H | [ ] | Modify a monitored file; alert fires | | 11.2 |
| MO-06 | Audit log append-only, includes actor/object/before-after, tamper-evident or externally shipped | H | [ ] | Attempt edit/delete as app user | | 11.5 |
| MO-07 | Direct-origin hit and canary/honeytoken alerts exist | M | [ ] | Trigger a canary | | 11.7 |
| MO-08 | Alert escalation path and on-call defined; precision reviewed | M | [ ] | Escalation test; false-positive review | | 11.3 |
| MO-09 | Uptime, certificate-expiry and resource anomaly monitoring | M | [ ] | Check dashboards and test alerts | | 11.2 |

## 12. Deployment and supply chain

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| DP-01 | `APP_ENV=production`, `APP_DEBUG=false`; no Telescope/debugbar/phpinfo exposed | C | [ ] | `php artisan about`; probe endpoints | | 9.8 |
| DP-02 | Lockfiles committed; production installs from lockfile only (`composer install`, `npm ci`) | H | [ ] | CI/deploy script review | | 10 |
| DP-03 | Dependency audit in CI (`composer audit --locked`, `npm audit`), fail on High/abandoned/KEV | H | [ ] | CI output | | 10.1, 10.2 |
| DP-04 | Release-age delay and install scripts disabled for JS dependencies; Composer plugins allowlisted | M | [ ] | `.npmrc`/pnpm config; `allow-plugins` | | 10.1, 10.2 |
| DP-05 | CI actions pinned to full commit SHAs; images by digest; `permissions` least-privilege | H | [ ] | Workflow review | | 10.5 |
| DP-06 | No secrets exposed to untrusted PR code; no risky `pull_request_target` patterns; OIDC/short-lived credentials | H | [ ] | Workflow and secret-scope review | | 10.5 |
| DP-07 | Self-hosted runners only for private repos, ephemeral/isolated, no powerful shared credentials | H | [ ] | Runner configuration review | | 10.5 |
| DP-08 | Secret scanning (pre-commit, CI, history); rotation procedure exercised | H | [ ] | `gitleaks`; rotation runbook | | 10.5 |
| DP-09 | Branch protection/rulesets, required reviews, CODEOWNERS on workflows, MFA enforced | M | [ ] | Repository settings review | | 10.6 |
| DP-10 | Build once in CI; deploy verified artifact; checksum/signature verified before activation; rollback tested | M | [ ] | Deploy logs; rollback drill | | 10.7 |
| DP-11 | SBOM generated per release and stored | L | [ ] | Artifact exists | | 10.4 |
| DP-12 | Migrations run with migration credentials from pipeline; destructive changes follow expand/contract | M | [ ] | Pipeline config | | 7.6 |
| DP-13 | `.env.example` contains placeholders only; per-environment secrets and `APP_KEY` | H | [ ] | File review; environment comparison | | 9.7 |

## 13. Backup and recovery

| # | Security requirement | Risk | Status | Verification method | Component | Ref |
|---|---|---|---|---|---|---|
| BR-01 | Automated backups of database and uploads; frequency meets RPO | C | [ ] | Job logs; last-success timestamp alert | | 7.4 |
| BR-02 | Backups encrypted before leaving the host; key stored off the backup host/storage | H | [ ] | Inspect an archive (unreadable without key) | | 7.4 |
| BR-03 | Off-site plus offline/immutable copy (3-2-1-1-0) | H | [ ] | Storage configuration; attempt delete with write-only credential | | 7.4 |
| BR-04 | Backups never in web root or public buckets; access restricted and logged | C | [ ] | Search web root; bucket policy review | | 7.4 |
| BR-05 | **Restore tested** on schedule with measured time vs RTO and data age vs RPO | C | [ ] | Dated restore-drill record | | 7.4 |
| BR-06 | Point-in-time recovery (binlog/WAL) for systems needing minimal data loss | M | [ ] | PITR drill | | 7.5 |
| BR-07 | Incident response plan with roles, contacts, out-of-band channel; tabletop within 6 months | H | [ ] | Plan document; exercise record | | 13.1 |
| BR-08 | Rebuild-from-clean procedure and credential-rotation inventory exist and are current | H | [ ] | Walk-through; inventory review | | 13.7 |
| BR-09 | Retention and secure deletion defined for backups and logs | L | [ ] | Policy and lifecycle config | | 7.4, 11.6 |

---

## Summary and sign-off

| Domain | Items | Done | Partial | Open | N/A | Accepted risk |
|---|---|---|---|---|---|---|
| Frontend | 12 | | | | | |
| Backend | 15 | | | | | |
| APIs | 12 | | | | | |
| Authentication | 13 | | | | | |
| Authorization | 8 | | | | | |
| Database | 10 | | | | | |
| File uploads | 9 | | | | | |
| Payments | 12 | | | | | |
| Infrastructure | 15 | | | | | |
| Cloudflare | 13 | | | | | |
| Monitoring | 9 | | | | | |
| Deployment | 13 | | | | | |
| Backup and recovery | 9 | | | | | |

**Release gates** (any unchecked item blocks production release, see `WEBSITE_SECURITY_SKILL.md` 16.3): DP-01, IN-06, BE-01, AZ-02, API-01, API-02, PY-01, PY-04, CF-03 (if Cloudflare is relied on), BR-05, MO-02.

**Findings register**

| ID | Item | Priority (P0-P3) | Description | Owner | Due | Verification test | Status |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

**Not verified in this audit (and why):**

-

**Accepted risks (approver, date, expiry, compensating controls):**

-

**Sign-off:** Auditor ______________ Date ________ · Owner ______________ Date ________
