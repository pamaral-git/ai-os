---
name: docker
description: container preferences
modified: 22-November-2026
---

**DETAILS:**
- llama-server=http://localhost:8080
- volumes=/Users/pedroamaral/models/docker/Preview/**
- workspace/cloud=/Users/pedroamaral/Documents/cloudwork
- workspace/drive=/Volumes/X-Drive
- MacBook Pro M4-24GB RAM (MacOS ≥27) | Software (@latest): Docker Desktop, Podman, llama.cpp

**PREFERENCES:**
1. Always docker compose services file with latest build image and it's dependencies.
2. Always have services as end to end self-hosted and docker contained with on device-local data. NO global installations that breach the containirezed enviroment.
3. Add inline comments on lines to customize webui ports and further areas.
4. Containers are always limited to: application layer and, backend layer. NOT the inference runtime and model weights layer