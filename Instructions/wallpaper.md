---
name: wallpaper-render
description: Quick conditional AI Wallpaper Image Editing
metadata:
    author: github.com/pedromanuelamaral
    modified: 07-Septermber-2026
---

If  the provided image is already in the wallpaper aspect ratio (Portrait 19.5:9 for mobile or Landscape 16:10), then:
    [A] Create an image of the attached photo but UPSCALE to 4k resolution without changing the aspect ratio or visual aspects/contents.

Otherwise:
    [B] Create an image of the attached photo (keeping it all the same, without changing) now UPSCALE to 4k resolution and ZOOM OUT to fill what's outside of the image so it fits a 19.5:9 or 16:10 aspect ratio.
