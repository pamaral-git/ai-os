---
name: rewrite-loop
description: Instructions for rewriting text and verify.
metadata:
  author: github.com/pedromanuelamaral 
  modified: 04-November-2026
  allow: read permissions for {{original-file}}; write permissions for {{duplicated-copy-file}}; diff and comparison permission for both.
---

**GOAL:** Create a file that follows the user stated editing demands by following this rules in order:
 1. Read original file
 2. Generate a copy of the original file for your active edition
 3. Before submiting as final output check the diff compared to the original file, to insure nothing was lost in edting
