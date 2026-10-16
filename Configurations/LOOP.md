---
name: agent-loops
purpose: Snippets of loops derived from `AGENT.md` rules
modified: 16-October-2026
metadata:
    loop1: proactive loop to update the workspace log.md file
    loop2: turn-based loop to verify execution compliance with global rules
    loop3: goal-based loop to ensure anti-pollution after goal completion
    loop4: goal-based loop to recursively improve output result
    
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
3. Execution complies with rules from the "CAUTION", "UNAUTHORIZED" and identity "CONSISTENT PREFERENCES"

---

# More Loops

## Loop3 - Cleanup
Goal: Cleanup and leave zero unrequested ghost/residue/cache files, after goal completion without impacting the ability to deploy the goal-output.

Loop:
  1. SCAN: List all files in main/, temporary/, docker/, root. Classify: required-to-run vs scaffolding-deletable vs unrequested-residue/cache/ghost.
  2. VERIFY SCAN: If 0 residue and main/ self-contained with single readme.md + changelog.md + aliases -> TERMINAL NO_OP_ALREADY_CLEAN.
  3. CLEAN ONE: Pick ONE residue item. Run Verified-Execution-Loop safety check. Use matched-record cleanup only, never broad `rm -rf *` or kill all. If Top-Secret/locked -> TERMINAL BLOCKED_LOCKED. If high-level temp -> TERMINAL APPROVAL_NEEDED_HIGH_LEVEL, ask user approval, let user delete.
  4. EVIDENCE: Rescan. Is residue gone? Is main/ still runnable? If clean fails after 2 attempts -> TERMINAL FAILED_VERIFICATION.
  5. DEPLOY CHECK: Can main/ run in constrained env? If not, explicitly declare constraints, mark UNVERIFIED / To Be Tested transparently.
  6. REPEAT until scan = 0 unrequested residue -> TERMINAL SUCCESS_CLEAN_AND_RUNNABLE or SUCCESS_CLEAN_WITH_CONSTRAINTS.

## Loop4 - Recursive Improvement

```
## Principles

Tone: Pragmatic, precise, conservatively cautious-skeptical.

Goal: Build artifacts that pass 3 gates: **Precise**, **Correct**, **Ready-to-Use**.

1. **Hard Standard for Recursive Improvement**:
   - No loop exits until all gates are **unanimously approved** by the **Main Reasoning Judge**.
   - Subagents **cannot** propose "partial" or "unverified" improvements.
2. **Resource-Aware Optimization**:
   - **Local Models (RAM-Constrained)**: Incremental verification, early termination.
   - **Cloud Models (Cost-Per-Task Constrained)**: Parallel generation + PPT selection.
3. **Verification Gates**:
   - **Precision**: No vague placeholders; exact targets/versions/consequences.
   - **Correctness**: Tool-verified (e.g., `bash`, `grep`, `edit`); no hallucinations.
   - **Ready-to-Use**: Runnable in constrained environments (e.g., Docker, browser MCP).

---

## Phased Execution
### Phase 1: Task Breakdown
- **Input**: User goal (e.g., "Implement a verifiable recursive loop for x").
- **Output**: One **next task** (e.g., "Write a minimal prototype for x").
- **Rules**:
  - If the goal is ambiguous, **ask one clarifying question**.
  - If the task is impossible, **state blockers and required information**.

---

### Phase 2: Build (Loop n+1)
. **Subagent Deployment**:
   - **Agent-P**: Improves **Precision** (no placeholders, exact targets).
   - **Agent-C**: Improves **Correctness** (tool-verified, no hallucinations).
   - **Agent-R**: Improves **Ready-to-Use** (runnable in constrained environments).
3. **Main Reasoning Judge**:
   - **Reassesses** merged proposals against the 3 gates.
   - **Verdict**: If any gate fails, loop back to the failing subagent(s).
   - **Success**: All gates approved → proceed to **Phase 3**.

---

### Phase 3: Test
1. **Constrained Environment Testing**:
   - Local: Run in virtual enviroment or docker
   - Cloud: Simulate cost constraints (e.g., limit API calls).
2. **Output**:
   - **Verified**: Artifact runs without errors.
   - **Unverified**: Explicitly declare constraints/gaps (e.g., "Untested in Python 3.12").
3. **Failure Handling**:
   - If unverified, **loop back to Phase 2** with constraints as input.

---

## Example Workflow
1. **User Input**: "Implement a verifiable recursive loop for code generation."
2. **Phase 1**: Break into "Write a minimal LRI prototype in Python."
3. **Phase 2**:
   - **Agent-P**: Replaces "do something" with "call `subagent_deploy()` with exact args".
   - **Agent-C**: Verifies `subagent_deploy()` exists via `grep`; adds error handling.
   - **Agent-R**: Ensures Dockerfile supports Python 3.10+.
   - **Judge**: Approves all gates → proceed.
4. **Phase 3**:
   - **Test**: Runs in Docker; fails due to missing `subagent_deploy()`.
   - **Loop Back**: Agent-C adds the missing function.
   - **Test**: Passes → **SUCCESS**.
```
