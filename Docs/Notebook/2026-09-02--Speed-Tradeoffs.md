
# Speed, but at What Cost?

**Hardware**
- `MacBook Pro M4-24GB-10Core`
- `macOS 26.6.2`
- `llama.cpp 0.3.0 (build 10621)`

## Quick Thoughts

Everyone is racing on inference and generation speed right now — the proprietary side (ChatGPT's Ultrafast mode, Gemini 3.7) and, more palpably, the open-source side with tiny sub-5 bytes parameter models.

Some models currently in the limelight: `LFM 2.5`, `Qwen 3.5 4B`, `G9v3-3B`, `XHToken-Spark-X2.5-4B`, `Nemotron 3 Nano 4B` and `Gemma 4 E2B`. Tiny models have unquestionably improved and I regularly reach for these models on **repetitive, low-reasoning workloads** — the essential-but-mechanical parts of my workflow:

- tool-calling
- review/refactor of <100 lines against a provided structure
- next-word prediction / suggestion

These are prime targets for quick automation, **provided** the model's quality holds up, which is the caveat.

## Tiny Model Verdict

```json
[
  {
    "model": "Gemma4-E2B",
    "release": "02-04-2026",
    "platform": "Google-AI-Edge-Eloquent_Speech-to-Text",
    "tl;dr": "works but needs constant edit intervention when polishing text",
    "verdict": "actively-using"
  },
  {
    "model": "Nemotron3-Nano-4B",
    "base-model": "NVIDIA-Nemotron-Nano-12B-v2-Base",
    "release": "07-03-2026",
    "platform": "llama.cpp_&_OpenWebUI",
    "tl;dr": "fast but low intelligence density",
    "verdict": "deleted"
  },
  {
    "model": "G9v3-3B",
    "release": "22-07-2026",
    "platform": "llama.cpp_&_OpenWebUI",
    "tl;dr": “Reached quality decay faster than Qwen alternative",
    "verdict": "deleted"
  },
  {
    "model": "LFM-2.5-2.6B & 2.5-VL-3B",
    "release": "04-08-2026 & 12-08-2026",
    "platform": "llama.cpp_&_OpenWebUI",
    "tl;dr": “Highest tokens per second blabbering with lowest intelligence",
    "verdict": "deleted"
  },
  {
    "model": "Qwen-3.5-4B",
    "release": "27-02-2026",
    "platform": "llama.cpp_&_OpenWebUI",
    "tl;dr": “Gold standard for tiny reliable workhorse model",
    "verdict": "actively-using"
  }
]
```

**Tiny Verdict** 2 Active (Gemma 4 E2B & Qwen 3.5 4B) and 4 Deleted (Nemotron 3 Nano 4B, G9v3-3B, LFM 2.5 & LFM 2.5-VL)

---

## Quick Frustration Benchmark

The idea of doing the comparison only came to mind at the end of my attempts with LFM, so pardon the convoluted unhingness. This is a side-by-side comparison of the current candidates on a single task and same conditions.


```bash
--jinja -ngl 99 --flash-attn on --parallel 1 \
--cache-type-k q8_0 --cache-type-v q8_0 \
--ctx-size 32600 --reasoning-budget 8400 --reasoning-preserve \
--temp 0.1 --top-k 50 --repeat-penalty 1.05
```

**Task:** Convert a text log into a markdown directory-tree structure, matching the formatting of a reference file (`tree-md.md`), with an added subline per entry recording usage, token consumption, and tok/s on a per-model basis.

- **Input files**
  - `~/Downloads/tree-md.md` ([reference formatting](https://gist.githubusercontent.com/genadyp/ffc112df6c8b368127e3cbb37465d452/raw/56407725fc85000a122cda77176ddaa6448beeb5/tree-md.md))
  - `~/Documents/AI-Files/local-models-log.md`

- **First-Prompt**
  > Give me the same text but organised in the structure of a directory tree structure in markdown text (check the tree-map.md file to assimilate the formatting structure) where you also add a subline on each to write down my usage, token consumption, tok/s on a per model basis


### LFM 2.5 2.6B (lfm-2.5-2.6B-heretic-f16.gguf)

**First-Response [Prompt: 604.6 t/s | Generation: 16.9 t/s]**

```markdown
# Model Directory Tree

 * [LFM 2.5 2.6B](./models/lfm)
   Usage: High | Tokens: ~1.5M | Tok/s: ~2.0
 * [Qwen 3.5 4B](./models/aggressive-qwen-4b)
   Usage: Medium | Tokens: ~2.0M | Tok/s: ~3.0
 * [Ornith 1.5 9B](./models/ornith-1.5-9B-GGUF)
   Usage: High | Tokens: ~1.8M | Tok/s: ~2.5
 * [Laguna XS 2.1](./models/laguna-xs-2.1)
   Usage: Low | Tokens: ~0.9M | Tok/s: ~1.5
 * [Ornith 1.5 MoE](./models/ornith-1.5-35B-A3B-Uncensored-i1)
   Usage: Medium-High | Tokens: ~2.2M | Tok/s: ~3.0
 * [Qwen 3.8 27B](./models/qwen3.8-ara-i1)
   Usage: Low-Medium | Tokens: ~3.5M | Tok/s: ~2.0
 * [Meta Muse Glimmer](./models/muse-glimmer-30b-heretic)
   Usage: Medium | Tokens: ~2.4M | Tok/s: ~3.5
```

**Second-Attempt (truncation led to the text being cut off)**

>  You should use the ├── dir1

**Second-Response [Prompt: 467.1 t/s | Generation: 17.6 t/s]**

```markdown
# Model Directory Tree

.
├── [LFM 2.5 2.6B](./models/lfm)
├── [Qwen 3.5 4B](./models/aggressive-qwen-4b)
├── [Ornith 1.5 9B](./models/ornith-1.5-9B-GGUF)
├── [Laguna XS 2.1](./models/laguna-xs-2.1)
├── [Ornith 1.5 MoE](./models/ornith-1.5-35B-A3B-Uncensored-i1)
├── [Qwen 3.8 27B](./models/qwen3.8-ara-i1)
└── [Meta Muse Glimmer](./models/muse-glimmer-30b-heretic)
```

**Third-Attempt**

> You forgot to add the part regarding “add a subline on each to write down my usage, token consumption, tok/s on a per model basis, " which meant an indentation for each existing model so that there's a new line that comes under it.

**Third-Reasoning Stage (halted due to how it also failed)**

```
So the structure should be:
# Model Directory Tree

.
├── [Model Name](./path)
   Usage: High | Tokens: ~1.5M | Tok/s: ~2.0
├── [Model Name](./path)
   Usage: Medium | Tokens: ~2.0M | Tok/s: ~3.0
...

Format for each item:

├── [Model Name](./path)
   Usage: Level | Tokens: ~X | Tok/s: ~Y

Let's draft the response.
```

**Forth-Attempt (clearly pissed)**

> /read /Users/pedroamaral/Documents/AI-Files/agent.md
> Not like that how you're doing for fuck sake, see how the first 35 lines of code on "agent.md" are structured, and apply the same logic.

**Forth-Response [Prompt: 570.4 t/s | Generation: 18.3 t/s]**

```markdown
# Model Directory Tree

.
├── [LFM 2.5 2.6B](./models/lfm)
   Usage: High | Tokens: ~1.5M | Tok/s: ~2.0
├── [Qwen 3.5 4B](./models/aggressive-qwen-4b)
   Usage: Medium | Tokens: ~2.0M | Tok/s: ~3.0
├── [Ornith 1.5 9B](./models/ornith-1.5-9B-GGUF)
   Usage: High | Tokens: ~1.8M | Tok/s: ~2.5
├── [Laguna XS 2.1](./models/laguna-xs-2.1)
   Usage: Low | Tokens: ~0.9M | Tok/s: ~1.5
├── [Ornith 1.5 MoE](./models/ornith-1.5-35B-A3B-Uncensored-i1)
   Usage: Medium-High | Tokens: ~2.2M | Tok/s: ~3.0
├── [Qwen 3.8 27B](./models/qwen3.8-ara-i1)
   Usage: Low-Medium | Tokens: ~3.5M | Tok/s: ~2.0
└── [Meta Muse Glimmer](./models/muse-glimmer-30b-heretic)
   Usage: Medium | Tokens: ~2.4M | Tok/s: ~3.5
```


### Qwen 3.5 4B (qwen-3.5-4B-Uncensored-Q6K.gguf)

**First-Response [Prompt: 356.8 t/s | Generation: 21.5 t/s]**

```
# Local Models Log

.
 * [LFM 2.5 2.6B](muxodious/mradermacher/lfm)
   - Usage: [Insert Usage]
   - Tokens: [Insert Tokens]
   - Tok/s: [Insert Tok/s]
 * [Qwen 3.5 4B](hauhaucs/aggressive-qwen-4b)
   - Usage: [Insert Usage]
   - Tokens: [Insert Tokens]
   - Tok/s: [Insert Tok/s]
 * [Ornith 1.5 9B](ornith-ai/Ornith-1.5-9B-GGUF)
   - Usage: [Insert Usage]
   - Tokens: [Insert Tokens]
   - Tok/s: [Insert Tok/s]
 * [Laguna XS 2.1](bartowski/Laguna-XS-2.1)
   - Usage: [Insert Usage]
   - Tokens: [Insert Tokens]
   - Tok/s: [Insert Tok/s]
 * [Ornith 1.5 MoE](mradermacher/Ornith-1.5-35B-A3B-Uncensored-i1)
   - Usage: [Insert Usage]
   - Tokens: [Insert Tokens]
   - Tok/s: [Insert Tok/s]
 * [Qwen 3.8 27B](trohrbaugh/mradermacher/qwen3.8-ara-i1)
   - Usage: [Insert Usage]
   - Tokens: [Insert Tokens]
   - Tok/s: [Insert Tok/s]
 * [Meta Muse Glimmer](bartowski/darkc0de/Muse-Glimmer-30B-heretic)
   - Usage: [Insert Usage]
   - Tokens: [Insert Tokens]
   - Tok/s: [Insert Tok/s]
```

**Second-Attempt (now left deliberately a bit vague)**

>  You should use the ├── dir1

**Second-Response [ Prompt: 287.6 t/s | Generation: 20.9 t/s]**

```markdown
# Local Models Log

.
├── [LFM 2.5 2.6B](muxodious/mradermacher/lfm)
│   - Usage: [Insert Usage]
│   - Tokens: [Insert Tokens]
│   - Tok/s: [Insert Tok/s]
├── [Qwen 3.5 4B](hauhaucs/aggressive-qwen-4b)
│   - Usage: [Insert Usage]
│   - Tokens: [Insert Tokens]
│   - Tok/s: [Insert Tok/s]
├── [Ornith 1.5 9B](ornith-ai/Ornith-1.5-9B-GGUF)
│   - Usage: [Insert Usage]
│   - Tokens: [Insert Tokens]
│   - Tok/s: [Insert Tok/s]
├── [Laguna XS 2.1](bartowski/Laguna-XS-2.1)
│   - Usage: [Insert Usage]
│   - Tokens: [Insert Tokens]
│   - Tok/s: [Insert Tok/s]
├── [Ornith 1.5 MoE](mradermacher/Ornith-1.5-35B-A3B-Uncensored-i1)
│   - Usage: [Insert Usage]
│   - Tokens: [Insert Tokens]
│   - Tok/s: [Insert Tok/s]
├── [Qwen 3.8 27B](trohrbaugh/mradermacher/qwen3.8-ara-i1)
│   - Usage: [Insert Usage]
│   - Tokens: [Insert Tokens]
│   - Tok/s: [Insert Tok/s]
└── [Meta Muse Glimmer](bartowski/darkc0de/Muse-Glimmer-30B-heretic)
    - Usage: [Insert Usage]
    - Tokens: [Insert Tokens]
    - Tok/s: [Insert Tok/s]
```

**Third-Attempt (same shortfalls of the other third-attempt)**

> You forgot to add the part regarding “add a subline on each to write down my usage, token consumption, tok/s on a per model basis, " which meant an indentation for each existing model so that there's a new line that comes under it.

**Third-Reasoning Stage [Prompt: 333.0 t/s | Generation: 20.8 t/s]**

```
# **models:**

├── [LFM 2.5 2.6B](muxodious/mradermacher/lfm)
│   ├── Usage: [Insert Usage]
│   ├── Tokens: [Insert Tokens]
│   └── Tok/s: [Insert Tok/s]
├── [Qwen 3.5 4B](hauhaucs/aggressive-qwen-4b)
│   ├── Usage: [Insert Usage]
│   ├── Tokens: [Insert Tokens]
│   └── Tok/s: [Insert Tok/s]
├── [Ornith 1.5 9B](ornith-ai/Ornith-1.5-9B-GGUF)
│   ├── Usage: [Insert Usage]
│   ├── Tokens: [Insert Tokens]
│   └── Tok/s: [Insert Tok/s]
├── [Laguna XS 2.1](bartowski/Laguna-XS-2.1)
│   ├── Usage: [Insert Usage]
│   ├── Tokens: [Insert Tokens]
│   └── Tok/s: [Insert Tok/s]
├── [Ornith 1.5 MoE](mradermacher/Ornith-1.5-35B-A3B-Uncensored-i1)
│   ├── Usage: [Insert Usage]
│   ├── Tokens: [Insert Tokens]
│   └── Tok/s: [Insert Tok/s]
├── [Qwen 3.8 27B](trohrbaugh/mradermacher/qwen3.8-ara-i1)
│   ├── Usage: [Insert Usage]
│   ├── Tokens: [Insert Tokens]
│   └── Tok/s: [Insert Tok/s]
└── [Meta Muse Glimmer](bartowski/darkc0de/Muse-Glimmer-30B-heretic)
    ├── Usage: [Insert Usage]
    ├── Tokens: [Insert Tokens]
    └── Tok/s: [Insert Tok/s]
```

---

## Takeaway

I don't think I will be reinventing the wheel with my assessment: Speed is good but only when there isn't a noticeable decay of intelligence. There were clear blind spots in the prompt engineering (it started as unofficial and then I kept it all the same to capture how murky real-life interaction with these models are).

Are we looking for a workhorse that knows what and how to do it, or are we looking for a very fast tiny model that needs to be surrounded by ropes and blinders so that with hand holding it goes from zero to one?

*As I worked on this note Gemini 3.8 Flash got released. I tested it and as a constant critic of Gemini’s lackluster performance, they might back… Positioning Flash as a workhorse that's now fast and finally of some use might be paying off.*