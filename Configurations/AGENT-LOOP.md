---
name: agent-loops
purpose: Snippets of loops derived from `AGENT.md` rules
modified: 28-September-2026
---

## Loop1 - `LOG.md` Rules:
1. Update logs and include task conclusions before termination or kills.
2. Structure entries from most recent to oldest.
3. Append high-level context from `./main/docker/**` to the end of each tag section.
4. Clean up scaffolding and unnecessary residue in `./main/docker/**` only after fulfilling rules 1 through 3.
5. Format every log tag header using the ISO 8601 date-time standard in UTC+01:00.

## Loop2 - Rules to Verify if:
1. Necessary tools were available and deployed for the task toolcalls
2. Decision regarding what constitutes "REASONING" necessary information were accurate
3. Execution complies with `AGENT.md` rules from the "CAUTION", "UNAUTHORIZED" and identity "CONSISTENT PREFERENCES"
