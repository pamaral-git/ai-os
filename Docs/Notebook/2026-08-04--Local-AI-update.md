# Experience-Log (August 3rd)

> Hardware: MacBook Pro M4-24GB-10Core (macOS 26.x)

- `ornith-1.0-9B_heretic_MTP-Q6_K.gguf` is the real reliable for coding and x-reasoning
- Qwen 9B & 4B falls to the second and third place, respectively
  - Will look to improve `qwen-3.5-9B_heretic_Q4_K_M.gguf` by using the Q
  - Gemma 12B is just too slow with bad differentiated output to even bother, (bad and considering deleting)
- Nvidia Nemotron 3 Nano 4B Uncensored was deleted and substituted for `G9-v3-3B-Q6_Q6_K_L.gguf` and `qwen-3.5-4B-Uncensored-Q6_K.gguf`
  - G9 v3 needs more testing to see if it’s worth it
  - Qwen 3.5 4B is decent for the compact size, tool calling loops
- `ornith-1.0-9b-Q4_K_M.gguf` base censored version was deleted (alongside the qwen 4b censored version) and substituted for the `ornith-1.0-9B_heretic_MTP-Q6_K.gguf`

| **Model ID** | **ID** | **Time** | **Status** | **Cached** | **Prompt** | **Generated** | **Prompt Speed** | **Gen Speed** | **Duration** |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen-3.5-9b-heretic | 2 | 15h ago | 200 | - | 5,471 | 1,573 | 190.27 t/s | 14.72 t/s | 135.63s |
| qwen-3.5-9b-heretic | 3 | 15h ago | 200 | - | 20,141 | 2,246 | 132.91 t/s | 13.07 t/s | 323.78s |
| gemma-4-12b-heretic | 4 | 14h ago | 200 | - | 26 | 411 | 26.00 t/s | 10.81 t/s | 39.02s |
| gemma-4-12b-heretic | 5 | 14h ago | 200 | 7 | 3,088 | 2,750 | 108.65 t/s | 9.94 t/s | 343.60s |
| gemma-4-12b-heretic | 6 | 13h ago | 200 | - | 17,441 | 5,138 | 88.52 t/s | 8.14 t/s | 828.70s |
| gemma-4-12b-heretic | 7 | 13h ago | 200 | - | 785 | 488 | 112.88 t/s | 11.88 t/s | 48.53s |
| ornith-9b-heretic | 8 | 13h ago | 200 | - | 3,136 | 489 | 190.75 t/s | 11.87 t/s | 57.66s |
| ornith-9b-heretic | 9 | 13h ago | 200 | - | 10,809 | 391 | 164.72 t/s | 11.49 t/s | 99.73s |
| ornith-9b-heretic | 10 | 13h ago | 200 | - | 12,864 | 337 | 175.96 t/s | 11.22 t/s | 103.18s |
| ornith-9b-heretic | 11 | 13h ago | 200 | 10,059 | 5,515 | 1,140 | 157.57 t/s | 11.53 t/s | 133.89s |
| ornith-9b-heretic | 12 | 32m ago | 200 | - | 4,249 | 671 | 194.63 t/s | 12.05 t/s | 77.52s |
| ornith-9b-heretic | 13 | 28m ago | 200 | - | 21,523 | 1,091 | 150.20 t/s | 11.09 t/s | 241.88s |

## Additionally:
- `Qwen-3.6-35B-A3B-Uncensored-GGUF` not suitable just as expected prior to testing;
- Onboarding and Currently Testing `Voxtral-4B-TTS-2603-mlx-6bit` for local text-to-speech.
