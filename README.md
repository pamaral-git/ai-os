# AI-Research-Hub - [Site](https://pedromanuelamaral.github.io/AI-Research-Hub)

Local-first repository for model configurations, instructions, autonomous loops, and notes. The setup targets on-device inference on Apple Silicon and self-hosted Docker containers, supporting work on downstream tools such as [Arta (art analysis curation)](https://github.com/pedromanuelamaral/arta), [Agent Lab (learning tech enviroment)](https://github.com/pedromanuelamaral/agent-lab), [Fusion Research (macro equity research)](https://pedromanuelamaral.github.io/fusion-research/), and [Mentally Here (health companion)](https://pedromanuelamaral.github.io/mentally-here/Index.html).

```
Host: MacBook Pro M4 (24 GB unified memory)
OS: macOS 27, iOS 27, Android
Runtimes: llama.cpp, Docker
Author: Pedro Amaral
```

---

## Directory

```
AI-Research-Hub/
├── Configurations/            <- Runtime configs, system inventory, model swap rules
│   ├── AGENT.md               <- Global agent identity and workspace rules
│   ├── WRITE.md               <- Global writing rules
│   ├── INVENTORY.sh           <- System state snapshot script
│   ├── docker-mcp.json        <- Docker run model context protocols for agent 
│   ├── ai-browser.sh          <- AI Browser use script
│   ├── fetch-nvidia-model.py  <- NVIDIA NIM enpoint catalog fetcher
│   ├── llama-swap.yaml        <- Local model server definitions
│   └── llama-swap-to-cli.py   <- YAML llama-server to llama-cli converter
├── Contributions/             <- Pull Requests done on other Platforms
│   └── [PR1_Heretic-Models-Explorer](https://huggingface.co/spaces/MuXodious/Heretic-Models-Explorer/discussions/2#6aa80bacee81a827dc56bf6d)
├── Instructions/              <- Reusable task prompts
│   ├── Loops/ 
│   │   ├── cleanup.md         <- Cache and residue deletion checklist
│   │   └── RSI/               <- Recursive self-improvement harness
│   │       │   ├── acceptance.py  <- Requirement verification runner
│   │       ├── loop.md            <- Refinement loop specification
│   │       ├── lri.py             <- Loop execution controller
│   │       ├── policy.yml         <- Execution and memory limits
│   │       └── task.json          <- Task contract format
│   ├── explain.md             <- Explain it to me prompt
│   ├── compact.md             <- Context compaction instruction
│   ├── docker.md              <- My Docker container preferences
│   ├── redact.md              <- PII and secret removal prompt
│   ├── TTS.md                 <- Read-aloud optimisation rules
│   ├── tough-love.md          <- Direct counter-argument persona
│   ├── uncensor.md            <- Unfiltered response guidance
│   ├── wallpaper.md           <- Image scaling and outpainting rules
│   └── news-monitor.md        <- Operational debrief format
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
└── .github/
    └── workflows/
        └── pages.yml          <- GitHub Pages static deployment
```

### Contributions

| File | Description |
|---|---|
| [PR1_Heretic-Models-Explorer](https://huggingface.co/spaces/MuXodious/Heretic-Models-Explorer/discussions/2#6aa80bacee81a827dc56bf6d) | Pull Request for Heretic Models Explorer |

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
