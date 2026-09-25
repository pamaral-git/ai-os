---
name: docker
description: docker configuration preferences
modified: 24-September-2026
metadata:
    softwares: MacOS ≥27; Docker Desktop (≥v4.92.0)
    Stack: Terminal; llama.cpp (≥v0.4.0)
    variable: $profile="/Users/path"
---

Always on Docker Structural Preferences:
1. Always docker `compose.yml` file with latest build image and dependencies.
2. Always have services as end to end self-hosted and docker contained with on device-local data. NO global installations that breach the containirezed enviroment.
3. Add inline comments on lines to customize webui ports and further areas.
4. Containers are always limited to: application layer and, backend layer. NOT the inference runtime and model weights layer
5. Default Directories:
    - Configurations: `${profile}/models/docker/**`
    - Workspace: `/Volumes/X-Drive/docker-workspace` && `${profile}/Documents/cloud-workspace`
    - Local Models: `${profile}/models`
