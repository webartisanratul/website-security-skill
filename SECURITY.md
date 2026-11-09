# Security Policy

This repository publishes security guidance and the tooling that installs it. Two kinds of problems matter:

1. **Vulnerabilities in the tooling or release process**: the installer, scripts, workflows or published release
   artifacts (for example path traversal or overwrite in `scripts/install.sh`, workflow injection, a tampered
   release, a leaked secret).
2. **Harmful guidance**: documentation that, if followed, would introduce a vulnerability or weaken a control.

Ordinary inaccuracies, outdated references and broken links are not vulnerabilities: use the public issue forms.

## Supported versions

Only the latest release receives fixes. Pin a released version and update deliberately (see
[docs/INSTALL.md](docs/INSTALL.md)).

| Version | Supported |
|---|---|
| Latest release | Yes |
| Older releases | No |

## Reporting privately

Please do **not** open a public issue for category 1, or for category 2 when the harm is significant.

- Preferred: GitHub private vulnerability reporting: <https://github.com/webartisanratul/website-security-skill/security/advisories/new>
- Alternative: ratul450.ak@gmail.com

Include: affected file/version, impact, steps to reproduce (or the exact guidance and why it is unsafe), and any
suggested fix. Do not include real secrets or personal data.

## What to expect

| Step | Target |
|---|---|
| Acknowledge your report | within 5 business days |
| Initial assessment and severity | within 10 business days |
| Fix or mitigation for confirmed issues | as soon as practical; coordinated with you |
| Public advisory and credit (if you wish) | after a fix is released |

These are good-faith targets for a volunteer-maintained project, not contractual commitments.

## Verifying what you download

Every release publishes `SHA256SUMS`. Verify before use:

```bash
sha256sum -c SHA256SUMS      # macOS: shasum -a 256 -c SHA256SUMS
```

The release ZIP is built reproducibly from the tagged source by `scripts/build_release.py`: building the same
tag yourself yields the same checksum. Never run the installer from a pipe (`curl | bash`): clone or unpack a
release, read `scripts/install.sh`, then run it.

## Scope and safe testing

Test only your own clone or systems you are authorised to test. This project provides no exploit code and does
not accept requests for it.

## Disclaimer

The guidance is provided without warranty. Following it does not guarantee that a system is secure. You remain
responsible for verifying controls in your own environment.
