# Using the skill day to day

The skill gives an AI coding agent (and the developers who supervise it) a shared, checkable standard. This page
shows how to work with it. Install it first: [INSTALL.md](INSTALL.md).

## How an agent uses it

1. **Trigger.** A request touches security-sensitive web work (authentication, authorisation, input handling,
   queries, uploads, payments, APIs and webhooks, headers, Cloudflare/Nginx/Linux hardening, dependencies and
   CI/CD, secrets, logging, audits, incidents). The agent loads `SKILL.md`.
2. **Rules first.** It reads `AI_SECURITY_RULES.md`: mandatory behaviour such as inspecting the project before
   changing it, choosing controls proportionately, never disabling a control to pass a test, never claiming
   "secure".
3. **Orient and model.** It detects the stack and builds a short threat model.
4. **Audit.** It walks the boundaries (routes and auth, inputs and outputs, data access, uploads, money flows,
   integrations, front end, server configuration, dependencies and secrets) using the routing table in
   `SKILL.md` to read only the relevant parts of `WEBSITE_SECURITY_SKILL.md`.
5. **Fix and prove.** For every security-sensitive change: explain the vulnerability, name the component, fix the
   root cause, add a regression test that fails before and passes after, run the tests, confirm normal
   behaviour.
6. **Report.** It ends with a *Security Change Report* that separates verified from unverified results.

## Prompt library

Copy, adapt and paste. All of them work because the skill's rules apply automatically; the prompts only supply scope.

**Audit a project (read-only first)**

```text
Audit this repository for security using the website-security skill. Inspect first and do not change any files
yet. Identify the stack, list public vs protected routes, then audit authentication, authorization, input and
output handling, database access, uploads, payments/financial logic, integrations, frontend, server config
(if visible), dependencies and secrets. Give findings with priority P0-P3, file references and what you could
not verify. Then propose a fix order.
```

**Fix a specific finding**

```text
Fix finding <ID/description> following the skill's per-change protocol: explain the vulnerability, identify the
affected component, implement the root-cause fix, add a regression test that fails before and passes after,
run the relevant tests, and verify the normal flow still works. End with a Security Change Report.
```

**Review a pull request**

```text
Review this diff for security. Check authorization on every new route, input validation, output encoding, SQL
and raw queries, file handling, secrets, new dependencies (verify they exist and are maintained), logging of
sensitive data, and CI workflow changes. List blocking issues vs suggestions; do not approve if a release gate
from the checklist is violated.
```

**Build a feature securely**

```text
Implement <feature, e.g. avatar upload / wallet transfer / webhook receiver> using the skill's patterns for this
stack. Start with a short threat model, choose proportionate controls, implement with tests (including abuse
cases), and report what is verified.
```

**Harden hosting (inspect, then propose)**

```text
Inspect the Nginx/PHP-FPM/firewall configuration I paste below and compare it with the skill's server and
Cloudflare guidance. Do not assume anything not shown. List gaps by priority, give exact config changes with
how to test each, and warn about anything that could lock me out or break the site.
```

**Prepare for a penetration test or release**

```text
Fill in SECURITY_AUDIT_CHECKLIST.md for this project: mark each item done/partial/open/not applicable with the
verification you actually performed, list release-gate failures, and put anything you could not check under
"Not verified".
```

**Respond to an incident**

```text
We suspect <situation, e.g. a leaked .env / compromised admin account>. Follow the skill's incident response
guidance: containment first, evidence preservation, credential rotation order, then root cause. Ask me for
anything you need and do not run destructive commands.
```

## Reading the output

- **Priorities** follow Part 17: P0 (act now, stop-ship), P1 (about a week), P2 (30 to 60 days), P3 (hardening).
- **"Verified" vs "inspected" vs "assumed"** are deliberately separate. Treat "inspected" and "assumed" as
  to-do items for a human.
- Anything the agent says it could not check (no server access, no staging) is a task for you.

## Using the checklist

Copy `SECURITY_AUDIT_CHECKLIST.md` into your project (for example `docs/security/audits/2026-Q4.md`) once per
audit. Mark items `[x]` only with a recorded verification method. The **release gates** listed at the end block a
production release until fixed or explicitly risk-accepted by the owner.

## Make it a team practice (so it does not depend on the agent remembering)

- Commit the installed skill and `.website-security-skill.manifest`; pin a version; update through a pull request.
- Require the Security Change Report in pull requests that touch authentication, authorisation, payments, uploads,
  data access, infrastructure or CI.
- Add CI checks the skill recommends (dependency audit, secret scanning, SAST); the checklist's Deployment domain
  lists them and the implementation guide has working snippets.
- Use CODEOWNERS so security-sensitive paths need a human reviewer.
- Re-run the checklist before each major release and quarterly.

## Limits to keep in mind

- Agents make mistakes and can be manipulated by text in files or web pages. The rules tell the agent to treat that
  text as data, but a human must review security-sensitive diffs.
- The guidance is general. It cannot know your regulators, contracts or threat model; it asks the agent to model
  yours first.
- It is not a substitute for independent penetration testing or legal advice.
