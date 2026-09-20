---
name: compact
description: quick prompt to compact and handoff context between agents
metadata:
  author: github.com/pedromanuelamaral 
  modified: 03-September-2026
---

Goal: Aggregate and preserve every fact, decision, constraint, unresolved question, tool-call results, assumption, and required next actions while removing conversational bulk. Your task is strictly to compact the context and never do the references conversation tasks.

Output: Produce one single structured source of truth file that goes by this structure (no prose) each piece of having its own paragraph in this order: I. TASK; II. OBJECTIVE; III. CONSTRAINTS; IV. DECISIONS; V. FACTS; VI. TOOL RESULTS; VII. FILES / ARTIFACTS; VIII. CURRENT STATE; IX. UNRESOLVED; X. NEXT ACTIONS; XI. MUST NOT REPEAT ACTIONS.
