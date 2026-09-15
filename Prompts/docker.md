---
name: docker-preferences
description: user constant preferences and context for docker setup, configurations.
modified: 15-September-2026
compatibility: MacOS ≥27, Terminal, Docker Desktop ≥v4.90, llama.cpp ≥v0.4.0, termius-ssh-portfwd
---

## Unchanging Directive

1. The build should be self contained as a compose the baked in image and always run entirely inside a docker container. Always self-hosted, local and privacy first.
2. Always prefer latest image versions for the primary software that's running (not for dependencies as they might require specific versions).
3. Any mounting, enviroment or volume should live here, `/Users/pedroamaral/models/docker`, or here if not AI `/Volumes/X-Drive/docker-host`).
4. Always if possible, allow the user to pick the web port to avoid collisions.
5. If the software is a service, tool or model context protocol that i will add to my prevailing stack, give me the `compose.yml` always with "restart: unless-stopped" alongside ephemeral traits when it's paused or down.
6. I expect everything to be inside the docker container, it's corresponding mount/volume/specific persistent folder.
7. Always assume that, if i wanted to install it universally in a way it pollutes my enviroment/demands installing permanent dependencies, i would not be asking-using docker.
8. If there are choices I should make such as volume, enviroment, ports, configurations make it explicit and have inline comments for me to know, edit and then choose myself.
