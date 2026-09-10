# What 17,000 people said to the researcher who quit Anthropic

On 9 September a pretraining researcher posted that he had resigned from Anthropic because neither it nor OpenAI was acting responsibly. Within a day the post had 100 million impressions, 13,000 replies and 28,000 quote tweets. I wanted to know what that reaction actually consisted of, so I pulled every visible reply and quote tweet through the X API and had a language model sort them.

![Two-ring donut of response categories](figures/taxonomy_sunburst.png)

## Method

X exposed 5,000 of the 13,000 replies and 14,000 of the quote tweets; the rest are hidden as low quality or came from restricted accounts. After dropping spam, 17,541 posts remained. Claude Opus 5 read a 1,300-post sample and proposed a two-level scheme of ten categories and 48 response types, then assigned every post to one type. I grouped the ten categories into four moves: arguing, reacting, judging the author, and noise.

## What the reaction is made of

**Most of it is not argument.** Only 22% of posts engage the claim at all. Reaction is 31%: brief alarm, doom humour, sci-fi references, personal fear. Another 22% is noise, mostly emoji-only or off-topic replies. A quarter judges the author rather than the claim, and here endorsement outruns attack by 18% to 7%.

**The venue matters.** Replies argue and quotes emote. Substantive debate, denial and attacks on the author make up 36% of replies but 12% of quotes. The thread under the post is a hostile room; the quotes that carried it to other feeds are a sympathetic one.

**The cruxes are few and concrete.** Among the skeptical posts, most are not cruxes at all. "Doomer cult", "marketing stunt", and hypocrisy accusations attack the messenger, and no argument would move them. The posts that hold a real objection cluster around four gaps: *how* an AI would actually kill anyone (the most-liked sincere question: "I can't make the mental jump from using Claude on my desktop to being killed"), why you cannot just unplug it, whether a token predictor can be an agent at all, and why this is not Y2K again. Each of these is under 2% of posts, but they are the ones worth answering.

**The densest counter-argument is not about risk.** In the reply thread, "If we stop, China wins" is the most common structured objection (4% of replies), and it concedes the danger while rejecting the response. It has its own rebuttal strand of nearly the same size.

## What this suggests

An insider's warning is an appeal to authority, and the reaction shows what that format buys. It travels: signal-boost and relay posts alone are 10% of everything said, the largest single response type after emoji noise. It also invites the motive attack instead of the object-level one, and the object-level questions that do surface are the ones the warning did not answer. If the goal is to move people who are engaged but unconvinced, the material to write is a plain account of mechanism, controllability, and base rates, aimed at the small group asking for exactly that.

*Data and code: X API v2, 2026-09-09; labels by Claude Opus 5. Reply coverage is the visible thread only; hidden replies are likely more hostile than what is shown.*
