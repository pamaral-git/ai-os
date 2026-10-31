# Gemma 4 QAT (Unsloth Update) Vs. Gemma 4 (Google Original)

| Details                              |  |
|------------------------------------|------------|
| Date                      | 20 July 2026  | 
| Category |  `benchmark` ; `apple-silicon` ; `gguf` ; `llama-cpp` |

## Tested the same task:
> `/read /Users/pedroamaral/Documents/AI-Files/notes.md`  
> Suggest a new improved writing of the file as a markdown file, make it better for me to use as my default daily driver.

### Hardware & Context
- **Device**: MacBook Pro M4 (10-core GPU, 24 GB unified memory), macOS 26.5.2
- **Backend**: llama.cpp (recent build with Metal + Flash Attention + MTP support)
- **[Old Model](https://huggingface.co/google/gemma-4-12B)**: `gemma-4-12B-Q6_K_M.gguf` (pre-July refresh, standard quant)
- **[Updated + Unsloth QAT Model](https://huggingface.co/unsloth/gemma-4-12B-it-qat-GGUF)**: `gemma-4-12B-it-qat-UD-Q4_K_XL.gguf` ‣ 
- **[Multi Token Prediction Gemma 4](https://huggingface.co/unsloth/gemma-4-12B-it-qat-GGUF/resolve/main/MTP/mtp-gemma-4-12B-it-Q8_0.gguf)**: `mtp-gemma-4-12B-it-Q8_0.gguf`

### Commands Used
```bash
llama-cli -m /Users/pedroamaral/models/gemma-4-12B-it-qat-UD-Q4_K_XL.gguf \ 
  --jinja -ngl 99 --flash-attn on \
  --ctx-size 40000 \
  --model-draft /Users/pedroamaral/models/mtp-gemma-4-12B-it-Q8_0.gguf \
  --spec-type draft-mtp --spec-draft-n-max 3 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --temp 0.6 --top-p 0.92 --min-p 0.05
```

```bash
llama-cli -m /Users/pedroamaral/models/gemma-4-12B-Q6_K_M \
  --jinja -ngl 99 --flash-attn on \
  --ctx-size 32768 \
  --model-draft /Users/pedroamaral/models/mtp-gemma-4-12b-it-Q8_0.gguf \
  --spec-type draft-mtp --spec-draft-n-max 3 \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --temp 0.6 --top-p 0.92 --min-p 0.05
```

### Results

| Model                              | Prompt t/s | Generation t/s | Output chars | Thinking tokens | Context |
|------------------------------------|------------|----------------|--------------|-----------------|---------|
| Old Q6_K_M                        | 122.0     | **2.9**        | 9130        | 2637           | 32k    | 
| New QAT UD-Q4_K_XL + MTP          | **126.8** | **3.9**        | 7699        | 2202           | 40k    | 

### Honest Opinion
The new Unsloth QAT Q4 is a clear improvement: ~34% faster generation and better memory efficiency thanks to QAT + refreshed weights. It handled 40k context comfortably.
However:
- Generation is still slow (3.9 t/s) for a 12B model on M4 hardware (32 GB+ would be much more comfortable).
- For heavy agentic tasks (multi-step tool calling, long reasoning chains, large outputs), RAM pressure builds fast on 24 GB. You’ll hit swapping or need to reduce context.
- The old Q6 is even worse under load.

The `Gemma 4 12B Unsloth QAT Q4 (with MTP)` is:
- My second choice for conversation-only tasks, falling behind `Qwen-3.5-9B-Q4`;
- My third choice for harder tasks, falling behind (1st) `Qwen-3.5-9B-Q` and `Ornith-1.0-9B` (2nd).
