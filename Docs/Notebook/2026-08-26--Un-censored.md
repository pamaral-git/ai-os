# Self-Hosting (Un)censored • [Tech Lands Talk](https://luma.com/mci5o0od)

On good and bad times, I've been fortunate enough to be able to use technology to make some contributions I would like to think as positive. This was the idea behind [Mentally here](https://github.com/pamaral-git/mentally-here), a personal and private companion for one's mental health journey, that I started building in the open.

And in the usage of technology to share deep, personal, vulnerable parts of ourselves, questions about privacy and truthfulness become even more important. At first, we might have asked ChatGPT or Gemini or Claude to help us navigate through some issues of ours. But with every word we input, the switching costs accrue.

So what if we were more cautious with our deeply psychological personal information and asked more of these models that at times are capable of lying just to please us?

That's perhaps the intuition underlying [abliteration](https://github.com/p-e-w/heretic) — which in simple terms can be described as doing surgery (i.e., fine-tuning) on large language models so that there's a reduction of what the model's brain (i.e weights) refuse to answer due to safety or how they were trained.

Routing towards local models for personal issues came, of course, with the local hardware tradeoff constraint, but it still today feels the most appropriate. And when I turned towards local hosted uncensored models, on top of full data privacy, I too began having outputs that directly called me on my own bullshit.

But it wouldn't suffice to just tell the bright side of the story. As the gap between open-sourced and closed proprietary models [shrinks](https://newsletter.semianalysis.com/p/are-open-models-catching-up), the question posed to closed models and [misalignment](https://www.anthropic.com/research/agentic-misalignment) will become perhaps more important for widely adopted open-sourced models: [How much does a felony cost?](https://www.felonybench.com)

---

Free to Try Recommendations:

1. Self-hosted Private AI Chat App: **Off the Grid** ([Github](https://github.com/off-grid-ai/OGAM) • [Apple](https://apps.apple.com/pt/app/off-grid-ai-private-local-ai/id6759299882?l) • [Android](https://play.google.com/store/apps/details?id=ai.offgridmobile))

2. ⁠Local AI Speech to Text Transcription: **Google Edge Eloquent** ([Google Developers](https://developers.google.com/edge/eloquent))

3. ⁠Uncensored Models to try online, no account-free: https://venice.ai

4. Uncensored Models that you can download and use on a Private AI Chat: 
    - `mradermacher/Qwen3.5-uncensored-GGUF` fits on most devices and pick the option `Qwen3.5-uncensored.Q4_K_M`
    - `mradermacher/LFM2.5-230M-heretic-v1-i1-GGUF` even smaller model with the option `LFM2.5-230M-heretic-v1.i1-Q6_K`
