---
name: docker
description: docker configuration preferences
modified: 01-October-2026
metadata:
    softwares: MacOS ≥27; Docker Desktop (≥v4.92.0); Podman (≥v1.29.3); llama.cpp (≥v0.4.0)
    hardware: MacBook Pro M4-24GB RAM
    variables: containers="~/models/docker/**"; workspace="~/Documents/cloud-workspace"; local-ai="~/models"; llama-server="http://localhost:8080"; external-workspace="/Volumes/X-Drive"
---

Guiding Preferences:
1. Always docker `compose.yml` file with latest build image and it's dependencies.
2. Always have services as end to end self-hosted and docker contained with on device-local data. NO global installations that breach the containirezed enviroment.
3. Add inline comments on lines to customize webui ports and further areas.
4. Containers are always limited to: application layer and, backend layer. NOT the inference runtime and model weights layer
