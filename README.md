# AI-Research-Hub

Local-first repository for model configurations, instructions, autonomous loops, and notes. The setup targets on-device inference on Apple Silicon and self-hosted Docker containers.

```
Host: MacBook Pro M4 (24 GB unified memory)
OS: macOS 27, iOS 27, Android
Runtimes: llama.cpp, Docker
Operator: Pedro Amaral
```

---

## Scope

This repository stores configurations, instructions, autonomous loops, and notes for local AI development. It standardizes runtime flags, system prompts, and cleanup scripts across projects.

The files support work on downstream tools including [Arta](https://github.com/pedromanuelamaral/arta), [Agent Lab](https://github.com/pedromanuelamaral/agent-lab), [Fusion Research](https://github.com/pedromanuelamaral/fusion-research), and [Mentally Here](https://github.com/pedromanuelamaral/mentally-here).

---

## Directory structure

```
AI-Research-Hub/
├── Configurations/            <- Runtime configs, system inventory, model swap rules
│   ├── AGENT.md               <- Always-on agent identity and workspace rules
│   ├── agent-browser.sh       <- Chrome Testing remote debugging launcher
│   ├── fetch-nvidia-model.py  <- NVIDIA NIM catalog scraper and endpoint builder
│   ├── INVENTORY.sh           <- System state snapshot script
│   ├── llama-swap.yaml        <- Local model server definitions
│   └── llama-swap-to-cli.py   <- YAML to llama-cli command converter
├── Instructions/              <- Reusable task prompts
│   ├── explain.md             <- Comparative explanation matrix
│   ├── text-to-speech.md      <- Read-aloud phrasing rules
│   ├── tough-love.md          <- Direct counter-argument persona
│   ├── uncensor.md            <- Unfiltered response guidance
│   ├── wallpaper-render.md    <- Image scaling and outpainting rules
│   ├── world-monitor.md       <- Operational debrief format
│   └── write.md               <- Direct writing constraints and anti-slop rules
├── Loops/                     <- Unattended routines and verification cycles
│   ├── cleanup.md             <- Cache and residue deletion checklist
│   ├── RSI/                   <- Recursive self-improvement harness
│   │   ├── acceptance.py      <- Requirement verification runner
│   │   ├── loop.md            <- Refinement loop specification
│   │   ├── lri.py             <- Loop execution controller
│   │   ├── policy.yml         <- Execution and memory limits
│   │   └── task.json          <- Task contract format
│   └── scrape.md              <- Search and scrape orchestration steps
├── Notebook/                  <- Benchmark logs and technical writeups
│   ├── 2026-06-21--Gemini-3.6-Testing.md
│   ├── 2026-06-29--Cerebras-Hackathon.html
│   ├── 2026-06-29--Cerebras-Hackathon.md
│   ├── 2026-07-20--Gemma4-12B-MTP.md
│   ├── 2026-08-04--Local-AI-update.md
│   ├── 2026-08-05--Gemma4-TTS-LFM.md
│   ├── 2026-08-22--Self-Hosting-Sovereignty.md
│   ├── 2026-08-26--Un-censored.md
│   ├── 2026-09-02--Speed-Tradeoffs.md
│   └── 2026-09-06—Local-Semantics.md
├── Prompts/                   <- Handoff and ingestion prompts
│   ├── compact.md             <- Context condensation schema
│   ├── docker.md              <- Container deployment preferences
│   └── redact.md              <- PII and secret removal prompt
└── .github/
    └── workflows/
        └── pages.yml          <- GitHub Pages static deployment
```

---

## Repository files

### Configurations

| File | Description |
|---|---|
| [AGENT.md](Configurations/AGENT.md) | Always-on rules for identity, workspace paths, and tool access |
| [agent-browser.sh](Configurations/agent-browser.sh) | Shell script launching Chrome with remote debugging on port 8889 |
| [fetch-nvidia-model.py](Configurations/fetch-nvidia-model.py) | Python utility querying NVIDIA NIM APIs with local Crawl4AI fallback |
| [INVENTORY.sh](Configurations/INVENTORY.sh) | Shell script recording hardware specs, PATH entries, and model paths |
| [llama-swap.yaml](Configurations/llama-swap.yaml) | Model endpoints, swap parameters, and memory budgets |
| [llama-swap-to-cli.py](Configurations/llama-swap-to-cli.py) | Parser translating YAML configuration into llama-cli arguments |

### Instructions

| File | Description |
|---|---|
| [explain.md](Instructions/explain.md) | Prompt structure for comparative matrix explanations |
| [text-to-speech.md](Instructions/text-to-speech.md) | Rules for speech generation in English and European Portuguese |
| [tough-love.md](Instructions/tough-love.md) | Adversarial review persona for testing assumptions |
| [uncensor.md](Instructions/uncensor.md) | System prompt removing conversational hedges and refusals |
| [wallpaper-render.md](Instructions/wallpaper-render.md) | Instructions for 4K image upscaling and canvas extension |
| [world-monitor.md](Instructions/world-monitor.md) | Eight-part debrief format for news and operational events |
| [write.md](Instructions/write.md) | Machine instruction set removing LLM signatures and writing slop |

### Prompts

| File | Description |
|---|---|
| [compact.md](Prompts/compact.md) | Eleven-part schema for compressing agent context into facts |
| [docker.md](Prompts/docker.md) | Host paths and isolation requirements for Docker containers |
| [redact.md](Prompts/redact.md) | Text filter removing names, credentials, and network addresses |

### Loops

| File | Description |
|---|---|
| [cleanup.md](Loops/cleanup.md) | Checklist for removing temporary files, logs, and caches |
| [RSI/](Loops/RSI/loop.md) | Recursive self-improvement harness with automated acceptance tests |
| [scrape.md](Loops/scrape.md) | Sequence connecting SearXNG, Crawl4AI, and browser automation |

### Notebook

| File | Description |
|---|---|
| [2026-06-21--Gemini-3.6-Testing.md](Notebook/2026-06-21--Gemini-3.6-Testing.md) | Accessibility and benchmark comparison for HTML refactoring |
| [2026-06-29--Cerebras-Hackathon.md](Notebook/2026-06-29--Cerebras-Hackathon.md) | Build notes and latency logs for Arta |
| [2026-07-20--Gemma4-12B-MTP.md](Notebook/2026-07-20--Gemma4-12B-MTP.md) | Quantized inference speeds across Apple Silicon targets |
| [2026-08-04--Local-AI-update.md](Notebook/2026-08-04--Local-AI-update.md) | Model weights inventory and llama.cpp build updates |
| [2026-08-05--Gemma4-TTS-LFM.md](Notebook/2026-08-05--Gemma4-TTS-LFM.md) | Audio generation benchmarks comparing Gemma-4 TTS and LFM-2.5 |
| [2026-08-22--Self-Hosting-Sovereignty.md](Notebook/2026-08-22--Self-Hosting-Sovereignty.md) | Technical and privacy reasons for running models on local hardware |
| [2026-08-26--Un-censored.md](Notebook/2026-08-26--Un-censored.md) | Test outputs from fine-tuned weights without safety filters |
| [2026-09-02--Speed-Tradeoffs.md](Notebook/2026-09-02--Speed-Tradeoffs.md) | Token generation rates versus context size on M4 hardware |
| [2026-09-06—Local-Semantics.md](Notebook/2026-09-06—Local-Semantics.md) | Analysis of cloud dependencies in products marketed as local AI |

---

## Downstream projects and hackathons

This repository provides instructions and execution loops for related projects:

- [Arta](https://github.com/pedromanuelamaral/arta) (art analysis and curation, [demo](https://pedromanuelamaral.github.io/arta/))
- [Agent Lab](https://github.com/pedromanuelamaral/agent-lab) (interactive agent environment, [demo](https://pedromanuelamaral.github.io/agent-lab/))
- [Fusion Research](https://github.com/pedromanuelamaral/fusion-research) (macro equity research, [demo](https://pedromanuelamaral.github.io/fusion-research/))
- [Mentally Here](https://github.com/pedromanuelamaral/mentally-here) (health companion, [demo](https://pedromanuelamaral.github.io/mentally-here/Index.html))

### Hackathons

- Cerebras x Google Gemma 4 (June 2026): project build for Arta with Gemma-4 TTS and LFM-2.5 latency benchmarks.
- Nebius x NVIDIA Global AI Hackathon (August to October 2026): NIM model integration via `fetch-nvidia-model.py`.

---

## Deployment

GitHub Actions publishes static documentation to GitHub Pages on pushes to the main branch:

- [Documentation site](https://pedromanuelamaral.github.io/AI-Research-Hub)

---

## Author

Pedro Amaral | [GitHub](https://github.com/pedromanuelamaral) | [X](https://x.com/thephiloinvest) | [Devpost](https://devpost.com/pedromanuelamaral) | [Hugging Face](https://huggingface.co/Pedroamaral) | [CV](https://github.com/pedromanuelamaral/pedromanuelamaral/blob/main/CV.md)
