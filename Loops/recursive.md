---
name: recursive-loop
description: recursive output improvement loop
metadata:
  author: github.com/pamaral-git 
  modified: 06-November-2026
---

# Principles

2. **Resource-Aware Optimization**:
   - **Local Models (RAM-Constrained)**: Incremental verification, early termination.
   - **Cloud Models (Cost-Per-Task Constrained)**: Parallel generation + PPT selection.
   
3. **Verification Gates**:

## Macros
- **Goal**: ${User stated goal}.
- **Parent**: ${Main Result before the loop}
- **n+1**: ${Results of previous improvement loops}
- **Gate-QA**: ${Zero vague placeholders; Zero depricated dependencies; Quality assured code}.
- **Gate-VA**: ${Complete run test validation stage without warnings, bugs, errors and failures in the frontend, runtime, enviroment and backend}.

DENY: Propose partial or unverified improvements; Exit loop without unanimous approaval of the gates by the judge


## SUBAGENT GOAL
- Loop-task**: Improve ${Parent} so that it completes ${Goal} with ${n+1} while aligned with ${Gate-QA} and ${Gate-VA}

- If either ${Goal} or ${Parent}  are ambiguous or non-existent, AskUser Question for clarity.

**GOAL:** 
Tone: Pragmatic, precise, conservatively cautious-skeptical.

## Phased Execution

- **Conduct**:


### Step 2 - Improve n+1

Deploy three incremental subagents focused on improving:

1. **1QA**: Readonly subagent that analyses ${Parent} and looks for ${Gate-QA} improvements
2. **1VA**: Readonly subagent that executes the run
2. **2QA**: Second subagent that 
   - **Agent-C**: Improves **Correctness** (tool-verified, no hallucinations).
   - **Agent-R**: Improves **Ready-to-Use** (runnable in constrained environments).
2. **Main Reasoning Judge**:
   - **Reassesses** merged proposals against the 3 gates.
   - **Verdict**: If any gate fails, loop back to the failing subagent(s).
   - **Success**: All gates approved → proceed to **Phase 3**.

### Phase 3: Test
1. **Constrained Environment Testing**:
   - Local: Run in virtual enviroment or docker
   - Cloud: Simulate cost constraints (e.g., limit API calls).
2. **OUTPUT:**
   - **Verified**: Artifact runs without errors.
   - **Unverified**: Explicitly declare constraints/gaps (e.g., "Untested in Python 3.12").
3. **Failure Handling**:
   - If unverified, **loop back to Phase 2** with constraints as input.

---

```example.md
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
