## Website security (managed by website-security-skill)

For any security-sensitive change (auth, sessions, authorization, input handling, SQL, uploads, payments, APIs, webhooks, headers/CSP/CORS, server or CDN configuration, dependencies, CI/CD, secrets, logging):

- Read and follow `{{DOCS_PATH}}/AI_SECURITY_RULES.md` (mandatory rules).
- Inspect the existing stack before changing anything; pick controls proportionate to the risk.
- Use `{{DOCS_PATH}}/SECURITY_IMPLEMENTATION_GUIDE.md` for patterns and `{{DOCS_PATH}}/WEBSITE_SECURITY_SKILL.md` as the detailed reference (read only the relevant parts).
- Add a regression test for each fix, run the tests, and report verified versus unverified results. Never disable a security control to make something pass.
