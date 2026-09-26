# Local Semantics (Post Script)

Local inference doesn't often mean end-to-end local, as I've noticed many products marketed as Local AI while failing to be transparent about how one layer (hosting, inference, orchestration) is either their sole offer or where they fall short.

`Runs Locally` becomes ambiguous when there's a cloud dependency. But a better question to ask is: Why is Local AI offered in this way? 

---

## Previous Version

**The Myth of Self-Hosted AI**

Prioritising and owning the layer of intelligence of the LLMs we run is now a trend. I love it. But we shouldn't ignore the vendor incentives.
 
There are many self-hosting options and even more wrappers that vary in real end-to-end ability to finetune and host the model weights.

In a world where we have both, being upsold on something that's not only free but also required for better outputs is frustrating.

- [Superwhisper (August 26)](https://superwhisper.com/changelog) open-sourced their speech-to-text models, “model running locally” still needs cloud models in-the-loop for text polishing.

- [Perplexity (September 1)](https://www.perplexity.ai/hub/blog/introducing-hybrid-compute-on-mac) adds local models so that private data remains private, but you still need cloud models for orchestration.

Proprietary Cloud Models are great. I use them as intensely as Open-Source Models. But local should mean local end-to-end inference without the cloud in-the-loop.
