---
name: redact
description: quick ingestion prompt to redact details and keep it all private
modified: 15-September-2026
---

Goal: Give me the redacted verbatim version of the input/file, but make sure to completely all sensitive-personal information including names of relatives, location, emails, contacts, id-numbers, enviroment, ip addresses, api keys, secrets, any custom patterns with [user name or aliases] and anything traceable & sensitive.

Output: 1 file/output with everything sensitive removed & separate inline text referencing what was redacted.
