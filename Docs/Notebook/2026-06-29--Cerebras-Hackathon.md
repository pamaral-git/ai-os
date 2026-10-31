# Arta AI: Gemma 4 26B on Cerebras
Arta AI is a private cultural desk thats intersects memory + retrieval + judgment. This branch serves as the archive for the Gemma 4 hackathon build, see more here: https://pedromanuelamaral.github.io/arta

## Scope
- Local web UI with four tabs: Daily, Analyze, Bridge, Research
- Gemma 4 orchestration and reasoning loop
- Compact taste profile JSON (user history → signal abstractions)
- Daily briefing: one film + one literary passage around a precise theme
- Multimodal image demo (poster/still/cover analysis)
- Academic retrieval demo (local PDF → evidence packet → Gemma answer)

## What Was Built
- Local web UI (`surface/`) with four tabs
- Gemma 4 integration via API calls for reasoning and synthesis
- Taste Memory Agent — compacts user history into signal JSON
- Curation logic — selects candidates by taste profile (not popularity)
- Retrieval Agent — fetches evidence from local sources, creates context packets
- Multimodal Interpretation — image input → visual analysis → cultural connection
- Editorial Synthesis — writes briefings and analyses in a human voice

## Constraints
- **Cloud-First, Local-Sync** — raw data stays in user-controlled cloud folders; only compressed taste signals go to the model
- **Model-agnostic after hackathon** — Gemma is now the main brain; no hard-coding to one provider
- **Token efficiency** — Gemma handles reasoning; small local models handle embedding, clustering, deduplication

## Blueprint
1. Open Arta → Sync your Art Favourites → System loads your compact taste profile
2. On-demand briefing or suggestion (with explanation why) → User consumes suggestion or asks for analysis
3. Agent retrieves and reasons based on online sources and your profile → User consumes and rates output → Arta updates user taste profile

## Key Criteria
- **Resonance** — Underlying Themes (e.g. loss, identity, nostalgia) beat _this is like X_. Always ask: Does this feel tuned to the person?
- **Intersectionality** — a film relates to a poem, literary piece, music and so forth, when the emotional frequencies have a shared idea
- **Core** — look for and value permanent artistic axioms that share a deeper relation instead of transient moods
- **Editorial** — Echoes (validation), Counterpoints (stretching attention) and Judgement, never echo chambers or vanilla metadata lists

## Build Priority (24 hours)
1. Gemma 4 orchestration
2. Taste profile JSON
3. Daily briefing
4. Multimodal image demo
5. Academic retrieval demo (local PDF → evidence packet → Gemma answer)
6. SQLite persistence (optional if time permits)
7. Letterboxd CSV/XML ingestion (optional)

## What This Is Not
- Generic recommendation app
- Chatbot with a prettier prompt
- System that stores culture in fine-tuned weights
- Scraper-first project
- Public social network
- Replacement for human criticism
