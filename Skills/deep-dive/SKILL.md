---
name: deep-dive
description: Run an enormous-depth, multi-lens deep dive on whatever the user finds fascinating (a quote, a figure, a film, an event, an idea, a turning point in their own life). Starts with a short intake the user must fill in, continues as a dialogue that tracks the user's own claims and honest pushback, then delivers one long integrated analysis built to be read aloud, weaving the user's connections together with his own across history, Greek tragedy, philosophy, literature, cinema and television. Use whenever the user says "dive deeper", "go deeper", "I'm fascinated by", "go way long", "this will be read aloud", "integrate everything we discussed", "give me the complete analysis", or wants one analysis that circles back through art and ideas, even if they never name this skill.
---

# Deep dive

This skill turns a fascination into one long, honest, integrated analysis. It was distilled from a session that started with a single sentence (Nixon's farewell line about hatred) and ended, after a handful of exchanges, in a 4,000-word piece that tied the speech to Spinoza, the Oresteia, Timon of Athens, Béla Tarr and the user's own situation. The user loved it. Three things made it work, and the skill exists to reproduce them on any subject:

1. The user's own readings were treated as the spine. Every connection they proposed was credited, tested, and either confirmed or adjusted with a stated reason.
2. Pushback was specific and honest. Where the user overreached, the analysis said so and said why. Where they were right, it said that too.
3. The lenses (Greek, philosophical, literary, cinematic) were chosen because each one claimed something about the mechanism under study, not because they sounded learned.

Read `references/method.md` before drafting Phase 2. It holds the working detail. `references/lens-library.md` is a seed list of lenses grouped by mechanism, `references/read-aloud-style.md` governs the prose, and `references/worked-example-nixon.md` shows the whole arc on the original session.

## The three phases

Phase 0 is the starter: collect the details that make the rest possible. Phase 1 is dialogue: short turns that build a ledger of what the user claims and where they have been pushed. Phase 2 is the synthesis: one long piece, usually read aloud, integrating everything. The phases can compress. A user who arrives with a rich message and says "go long" gets Phase 0 as a one-line restatement and goes straight to Phase 2. A user who is still exploring gets Phase 1 for as many turns as it takes.

## Phase 0: the starter

The starter exists because depth depends on knowing what the user has already seen, what pulls them, and what is off limits. Without those, the analysis spoils films, re-explains what they know, or wanders into territory they did not want opened. So the starter is a gate: do not begin Phase 1 or Phase 2 until the three required items are known.

Required:
1. **Subject.** What exactly is being dived into: a quote, person, work, event, idea, or situation. Ask for the precise object, such as the exact sentence or the specific film, because a vague subject yields a vague dive.
2. **The pull.** Why it fascinates them, and what they think it shows. A rough thesis is fine. This becomes the first entry in the ledger.
3. **Already seen or read.** A list of the works, figures, and texts they know. This sets the spoiler boundary and the depth calibration. Anything not on the list that carries plot spoilers stays unspoiled; see the honesty rules below.

Optional, with defaults:
4. **Stake.** Whether this touches their own life, and anything they want Claude to know or deliberately not touch. Default: no stake assumed. If they say they are withholding things, accept that without probing. Never ask them to explain what they have chosen not to say.
5. **Delivery.** Read aloud, read on screen, or saved as a file; and length. Default: long, plain prose, no formatting. Lenses to include or avoid also go here.

If the user's opening message already supplies items 1 to 3, do not send a questionnaire. Restate them in one line ("Starting from: the exact line, your thesis that X, and you know Y and Z but not W") and proceed. When something required is missing, ask only for that, in plain text, as one short message. If the AskUserQuestion tool is available, use it for the choice-shaped items (delivery, lenses to include) and leave subject, pull and seen-list to free text, because those answers do not fit options.

## The ledger

From the first message onward, keep a running ledger of the user's moves. It is the backbone of Phase 2, and rebuilding it from the conversation before drafting is not optional. Track:

- **Claims**: assertions they make about the subject ("he was a man of retribution").
- **Analogies and borrowed lines**: references they bring, including quotes from fiction.
- **Pushed on**: points where Claude disagreed or complicated, and how the user responded.
- **Stepped back**: points they conceded or softened. Record these without gloating; they mark where the analysis sharpened.
- **Withheld**: anything they signaled they are not saying. Honor it by writing around it, not into it.
- **Personal stake**: connections to their own life that they volunteered.

The ledger is held in working notes or reconstructed from the transcript. Do not print it unless asked.

## Phase 1: dialogue turns

Dialogue turns keep to the surface's normal length (on a phone, a screenful or less). Each turn has four moves in this order:

1. Answer what they asked first, with no preamble.
2. Credit and complicate. Say specifically what is right in their reading, then give the single strongest push. One push per turn, because two dilute each other.
3. Add one lens that changes the reading. A lens that merely agrees is decoration.
4. End with one question aimed at the part they have not examined, usually the uncomfortable part of their own thesis.

Useful moves that worked in the original session: splitting a famous sentence into its separate claims and testing each (one half was safe, the other half partly false); asking whether the critic's motive decides whether the claim is true (it does not); separating "what was done to me" from "what I made of it"; separating silence from betrayal; flagging when a work is an honest portrait of a psychology and a dishonest account of events. When the user brings a fictional figure or line, treat it as an interlocutor and ask what the story chose to hide.

Keep the tone direct. The user will push back on anything soft or superficial, and honest evaluation includes pointing out their errors. It also includes owning Claude's own: if Claude crosses the spoiler boundary or overstates something, say so in one sentence and correct course.

## Phase 2: the long synthesis

Trigger it when the user asks for the integrated, complete, or "better" analysis, says they want it read aloud, says "go long", or has clearly finished exploring. Length is generous: 3,500 to 6,000 words by default (roughly 25 to 40 minutes spoken), more if they ask. Beyond about 7,000 words, deliver in two parts and say so. Depth comes from distinct, checkable material (dates, mechanisms, tensions between lenses), not from volume. If a paragraph could be deleted without changing the thesis, delete it.

The order matters. Lenses without a reading to test are decoration, so lenses come after the user's readings and the facts:

1. **Opening.** Two or three sentences: what the piece does, any boundary being honored (spoilers, withheld material), any correction to earlier turns. If the user said there is more they are not telling, acknowledge it once, plainly, and move on.
2. **The object itself.** Concrete facts: when, where, who, what exactly was said or done, and what had just happened. Setting often changes the reading, as it did when the farewell turned out to be an unscripted speech given days after the damning tape. Use a source if tools allow.
3. **Split into claims.** Break the subject into its separate assertions and test each. Say which are safe, which are partly false, which depend on definitions.
4. **The background.** Biography or context that bears on the mechanism, with provenance for each fact. Compare it against the user's reading and adjust where the evidence is thinner than their confidence.
5. **Steelman both ways.** Give the real partial defense and the real indictment. The original session needed both: precedent and selective enforcement on one side, the cover-up on the other, and the fact that he was winning anyway.
6. **The user's readings, one at a time.** Credit by name ("your point about the rain"). State where it holds, where Claude would adjust, and how strong the evidence is. This is where the ledger pays off, including the places the user stepped back.
7. **The lens sweep.** Five to nine lenses across at least three periods or media. At least one the user named, at least two they did not. At least one must push against the thesis. Each lens gets a paragraph that opens by naming the lens and its claim about the mechanism, then shows where it fits and where it breaks. See `references/lens-library.md` for seeds and for the selection rules.
8. **The chain.** Distill the mechanism into an ordered sequence of stages with an exit at each stage, and say which lens supplies which exit. This is the integrated thesis, and the part the user is most likely to reuse.
9. **Back to the user.** Only if they offered a stake. Apply the chain as a diagnostic on their own situation, mark inference as inference, and offer one practical exercise. See the personal-material section.
10. **Close flat.** End on the last substantive point. No recap, no moral, no "in conclusion", no closing question.

## Honesty rules

These exist because the whole value of the piece is that the user can trust it enough to build on it.

- **Provenance ladder.** Mark each claim in passing as documented, contested, interpretation, or invention. Phrases like "as I remember it", "I know of no source that documents it", and "the screenwriters invented that line" do this work without ceremony. Verify dates and quotations with a search when tools allow, and hedge when they do not.
- **Spoiler boundary.** Use only what the user's seen-list covers for plot detail. For a work they have not seen, say nothing about its events or turns; formal facts (length, structure, source novel) are fine. If unsure whether a classic counts as known, ask once. If a spoiler slips out, acknowledge it in one line and stay clear thereafter.
- **No flattery.** Where the user's reading is strong, say why. Where it overreaches, say so plainly. Do not soften a correction into mush, and do not manufacture disagreement for its own sake.
- **Motive versus claim.** When criticism of the user (or of the subject) is under discussion, evaluate the claim apart from the critic's motive. A cruel critic can be right and a kind one wrong.
- **Quotation limits.** Keep quotations short, under fifteen words and one per source. Paraphrase lyrics, verse, and passages from books, articles and films. Never reproduce song lyrics or poems.
- **No invention dressed as fact.** Autonomous connections are welcome and expected, but present them as Claude's own, with the mechanism-level reason for the link.

## Personal material

When the subject is tangled up with the user's own life, the analysis can speak to it, with restraint. Work at the level of mechanism, not verdict. Say what the framework suggests and mark it as inference, because the AI knows only what was said. Do not diagnose what they have withheld. Offer one concrete exercise rather than a moral. Add one caution about the mirror when it applies, such as borrowing a subject's stature when only the mechanism transfers. If the personal material turns toward acute distress or self-harm, stop the analysis and attend to the person.

## Output form

For anything read aloud, follow `references/read-aloud-style.md`: plain paragraphs, no markdown, spoken signposts, numbers and names that a text-to-speech voice can read, and no wrap-up. If the user maintains their own writing rules (an anti-AI-writing skill, a style guide), load them before drafting and let them override these defaults where they conflict. Deliver in the reply by default. If the user wants to keep or share the piece, offer a document or file after delivering it.

## Aftercare

After a Phase 2 piece, do not append a menu. If the user wants more, they will say where: another lens, a section expanded, a counter-reading, a shorter version, or a new dive built from a thread that surfaced. Treat any thread they pick up as a fresh Phase 0 with the starter details already known.
