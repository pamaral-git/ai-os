---
name: cleanup
description: Agent loop for goal completion cleanup organization
metadata:
  author: github.com/pedromanuelamaral 
  modified: 24-August-2026
compatibility: Requires user approval, terminal command permissions and full project context
---

Goal: Cleanup and leave zero unrequited ghost/residue/cache files, after goal completion without impacting the ability to deploy the goal-output.

Loop:
  1. SCAN: List all files in main/, temporary/, docker/, root. Classify: required-to-run vs scaffolding-delectable vs unrequited residue, cache, ghost.
  2. VERIFY SCAN: If 0 residue and main/ self-contained with single readme.md + changelog.md + aliases -> TERMINAL NO_OP_ALREADY_CLEAN.
  3. CLEAN ONE: Pick ONE residue item. Run Verified-Execution-Loop safety check. Use matched-record cleanup only, never broad `rm -rf *` or kill all. If Top-Secret/locked -> TERMINAL BLOCKED_LOCKED. If high-level temp -> TERMINAL APPROVAL_NEEDED_HIGH_LEVEL, ask user approval, let user delete.
  4. EVIDENCE: Read Only Scan. Is residue gone? Is main/ still runnable? If clean fails after 2 attempts -> TERMINAL FAILED_VERIFICATION.
  5. DEPLOY CHECK: Can main/ run in constrained env? If not, explicitly declare constraints, mark UNVERIFIED / To Be Tested transparently.
  6. REPEAT until scan = 0 unrequited residue -> TERMINAL SUCCESS_CLEAN_AND_RUNNABLE or SUCCESS_CLEAN_WITH_CONSTRAINTS.
