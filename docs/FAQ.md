# FAQ

**What is this, and who is it for?**
A set of Markdown documents that tell an AI coding agent how to handle web application security (mandatory rules,
an attack and control reference, an audit checklist, implementation recipes), plus an installer and tooling to
keep it current. It is for developers who use AI agents on web projects and want a consistent, reviewable
security baseline. Humans can read it too.

**Does following it make my site secure?**
No. It reduces common mistakes and makes verification explicit. It does not replace threat modelling for your
system, independent penetration testing, compliance work or legal advice. The documents themselves forbid
claiming that a system is "secure"; they ask for evidence of what was tested.

**Which tools does it work with?**
- **Claude Code** and **claude.ai/Claude Desktop**: the skill format (a folder with `SKILL.md`) and the install
  locations follow Anthropic's documentation (see [INSTALL.md](INSTALL.md)).
- **AGENTS.md, Cursor and GitHub Copilot**: the adapters follow each tool's documented instruction-file
  convention, but they have not been tested against those tools. Verify in your tool and adjust the plain-text
  adapter templates in `adapters/` if needed.

**Is `WEBSITE_SECURITY_SKILL.md` too big to load?**
It is a reference manual of roughly 80,000 tokens and is not meant to be loaded whole. The skill loads the short
rules first and reads only the sections a task needs (routing table in `SKILL.md`). See the context budget in
[INSTALL.md](INSTALL.md#6-context-budget).

**Why so much Laravel, Vue and Nginx?**
They are worked examples. The attack taxonomy, rules and controls are stack-neutral, and the documents say which
parts are universal and which depend on architecture. Recipes for other stacks are welcome (see
[CONTRIBUTING.md](../CONTRIBUTING.md) and the [roadmap](ROADMAP.md)).

**Can I shorten it or adapt it to my stack?**
Yes (MIT licence). Keep `AI_SECURITY_RULES.md` intact if you want the agent behaviour guarantees, record your
changes in your own changelog, and use the installer's update behaviour (it keeps files you modified and writes
the new version beside them).

**Will the agent scan my website or run attacks?**
The rules forbid running scanners, exploit-style tests or load tests against systems you have not confirmed you
own or may test, and against production without explicit approval. Active testing steps in the documents are
labelled "authorised targets only".

**Does anything phone home?**
No. The repository is static Markdown plus local scripts; the installer copies files and edits only the project
directory you point it at. What an agent sends to its model provider is governed by your tool and its settings.

**How do I know the content is accurate?**
Sources are primary and linked; links are split into *verified* and *not fetched* lists; code examples are linted;
library API names were checked against upstream source; the process and its limits are in
[VERIFICATION.md](VERIFICATION.md). Volatile facts are marked ⏱ and re-checked every quarter
([MAINTAINING.md](MAINTAINING.md)).

**How often is it updated, and how do I get updates?**
At least quarterly, plus when standards or major versions change. Watch the repository's releases, read the
changelog, and rerun the installer with the new version (it will not overwrite your edits).

**I found a mistake.**
Use the issue form for inaccuracies. If following the text could introduce a vulnerability and you think the harm
is significant, report it privately ([SECURITY.md](../SECURITY.md)).

**Can my company use it?**
Yes, under the MIT licence. Recommended: pin a version, verify checksums, review changes before upgrading, and keep
an internal fork if you add company-specific rules.

**Does it cover Windows/IIS hosting?**
The Linux/Nginx/PHP-FPM and Cloudflare guidance is covered; IIS-specific hardening is on the
[roadmap](ROADMAP.md). The general principles (least privilege, patching, logging, origin protection) apply.
