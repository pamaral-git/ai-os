# August 5th — Gemma-4, TTS, and LFM-2.5-2.6B

## Text-to-Speech Notes

1. Mistral Voxstral TTS (MLX) faces the same speech-volume issue found on Mistral's web-hosted version.
2. Fish Audio S2 Pro TTS (MLX) lags behind Voxstral on voice quality and tone.

## Local Models Stack

> MacBook Pro M4-24GB-10Core (macOS 26.5.2) - Llama.cpp build: b10250-ee0445c99

**Offloaded:**
- `Gemma-4-12B_heretic_Q4_K_M.gguf`
- `Gemma-4-12B-it-qat-UD-Q4_K_XL.gguf`
- `add_mtp-gemma-4-12b-it-Q8_0.gguf`
- `add_mmproj-gemma-4-BF16.gguf`

**Substituted with:**
- `LFM-2.5-2.6B-BF16.gguf`

---

## Verdict: LFM-2.5-2.6B vs. Gemma-4 12B

Gemma-4 12B's generation speed (3.8 t/s) is unbearable for any real workload on this machine — MTP speculative decoding likely adds at most ~0.5 t/s on top of that, based on prior non-MTP runs, so the draft model isn't meaningfully rescuing it. LFM-2.5-2.6B, at less than a quarter of the parameter count, produced output that was often close to or better than Gemma's on the same restructuring task, while running at roughly 4.6x the generation speed and leaving the device free for parallel work.

This is also the first time an LFM model has cleared the bar for actual daily use. Previous LFM releases were not usable at acceptable quality for this workload — this is the first one that is.

Because the speed gap alone (3.8 t/s vs. 17.7 t/s) was already disqualifying, Gemma was only run once. A second pass wasn't worth the time given the numbers already observed.

**Notes on the Gemma run:**
- Text-only task — no `--mmproj` flag was used, since restructuring a README is not a multimodal task. The `add_mmproj-gemma-4-BF16.gguf` file listed above was offloaded but not loaded for this test.
- Before the model settled into a normal load, this line appeared in the log: `failed to initialize the context: Gemma4Assistant requires ctx_other to be set` — this is expected noise during memory fitting, not a fatal error, and did not block generation.

---

## Benchmark: LFM-2.5 2.6B vs. Gemma-4 12B MTP

Both models processed the same input: the full `arta.ai` README ([source](https://raw.githubusercontent.com/pedromanuelamaral/arta/af7039da3c20af1ede98e673b85ec41558ba25c9/README.md), ~5,289 tokens / 24,386 characters) plus the same ~91-token / 427-character restructuring instruction.

| Model | Input tokens | Prompt speed (t/s) | Gen speed (t/s) | Config |
|---|---|---|---|---|
| LFM-2.5 2.6B BF16 | ~5,380 | 459.1 | 17.7 | `--jinja --flash-attn on --parallel 1 --ctx-size 32768 --cache-type-k q8_0 --cache-type-v q8_0 --temp 0.1 --top-k 50 --repeat-penalty 1.1` |
| Gemma-4 12B QAT Q4_K_XL + MTP | ~5,380 | 123.2 | 3.8 | Same flash-attn/cache/temp settings, plus `--model-draft`, `--spec-type draft-mtp`, `--spec-draft-n-max 3` |

### Input prompt

> `/read ./Downloads/arta.ai-main/README.md`

> Proceed with the restructuring of the document, cutting its length and separating things into (i) a main README.md that is the core overview of the project, and (ii) a second branch with its own README.md where everything related to the hackathon — the connection between the build and the Gemma hackathon — is no longer a relevant detail to include, as the project needs to take on a life of its own.

### Commands run

```zsh
llama-cli \
  -m ./models/LFM-2.5-2.6B-BF16.gguf \
  --jinja -ngl 99 --flash-attn on \
  --parallel 1 --ctx-size 32768 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --temp 0.1 --top-k 50 --repeat-penalty 1.1
```

```zsh
llama-cli \
  -m ./models/offloading/gemma-4-12B-it-qat-UD-Q4_K_XL.gguf \
  --model-draft ./models/offloading/add_mtp-gemma-4-12b-it-Q8_0.gguf \
  --spec-type draft-mtp --spec-draft-n-max 3 \
  --jinja -ngl 99 --flash-attn on \
  --parallel 1 --ctx-size 32768 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --temp 0.1 --top-k 50 --repeat-penalty 1.1
```

---

## LFM-2.5 2.6B — First Pass (459.1 t/s prompt | 17.7 t/s gen)

**Second prompt given after the first pass**, refining the restructure into a tighter, personal, non-hackathon-flavored pair of documents:

> That's the new semi-polished document with some changes. Go over it again and fine-tune it so I have the two separate files (or more if required), tighter and more brief, accessible, correctly pitched, with the tone that reads like it was copy-pasted from an AI chat erased. It becomes coherent; irrelevant internal-only details are removed and only pertinent information remains. This is no longer a project carrying the Gemma 4 flag or Cerebras — it should feel personal to whoever encounters it. ÆRTA (dropping the Æ) is a private, local-first art curator: fed RAG data by the user, it can either (1) serve as a data pipeline for other AI models via MCP/instructions/skills/hooks, or (2) be the user's own dedicated art interface.

After a brief editing pass (~90 minutes), both files were committed to the repository:

- [`main` README](https://github.com/pamaral-git/arta/blob/main/README.md) — core project overview
- [`hackathon` README](https://github.com/pamaral-git/arta/blob/hackathon/README.md) — build-specific, hackathon-only details

Both landed under ~400 words each.

---

## Gemma-4 12B MTP — Single Pass (123.2 t/s prompt | 3.8 t/s gen)

Gemma produced a comparable two-document split (`README.md` + `HACKATHON_PLAN.md`) on the first prompt, correctly separating permanent product vision from hackathon-specific execution details. Output quality was reasonable, but at 3.8 t/s the run was too slow to justify a second iteration — see Verdict above.
