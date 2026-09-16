# How X reacted to the "I resigned from Anthropic" post

**Summary.** RESULTS_SUMMARY_PLACEHOLDER

## Motivation

On 2026-09-09 a pretraining researcher (@hilbertspaess) posted a seven-part
thread announcing their resignation from Anthropic and arguing that both
Anthropic and OpenAI are racing irresponsibly toward self-improving
superintelligence. Within a day the root post had 100M impressions, 580k
likes, 13k replies, and 28k quote tweets. We wanted a quantitative read of
the reaction: how many people sided with the author, how many with the claim,
and which frames the discussion settled into, separately for replies (the
hostile, in-thread venue) and quote tweets (commentary carried to the
quoter's own followers).

## Method

**Collection.** We pulled the conversation through the official X API v2 on
pay-per-use billing with a stdlib Python script (`fetch_conversation.py`).
Replies came from four query styles unioned on post id, because no single
query returns the full tree: `conversation_id:` recent search,
`in_reply_to_tweet_id:` recent search, `to:hilbertspaess` recent search, and
`conversation_id:` full-archive search. Quotes came from the
`/2/tweets/:id/quote_tweets` endpoint with `exclude=retweets`; without that
flag the endpoint interleaves retweets of quote tweets, which made up 85% of
what it returned in our first pass.

**Labelling.** Each reply and quote was labelled once by Claude Opus 5 at low
effort through the Message Batches API, with the author's full thread in a
cached system prompt and a JSON schema forcing these fields:

- `sentiment`: positive, neutral, mixed, negative (tone of the post).
- `stance_author`: supportive, neutral, mixed, critical (toward the author and
  the act of resigning and speaking out).
- `stance_claim`: agree, not_addressed, mixed, disagree (toward the claim that
  the labs are racing irresponsibly and the risk is real).
- `frame`: one of eleven dominant frames (solidarity, AI-risk agreement,
  AI-risk dismissal or hype skepticism, hypocrisy or grift accusation,
  lab comparison, policy or coordination, mockery, question, news relay,
  off-topic or spam, other).
- `targets`, `is_bot_or_spam`, a 15-word `summary`, and `confidence`.

Nested replies were shown with their parent reply. Replies whose text is only
a media link were reassigned to a `media_only` frame after labelling.
Spam-flagged posts are excluded from all tables. Like-weighted tables weight
each post by 1 + likes, which approximates what a reader scrolling the
thread actually saw.

**Reproduce.** `fetch_conversation.py` (four reply passes plus the quote pass,
commands in README.md), `merge.py`, `classify.py --batch` then `--collect`,
`analyze.py`. Raw JSONL and labels are persisted at
`gs://alignment-team-general-storage/daniel/jarvis/experiments/x-conversation-sentiment/`.

## Results

RESULTS_PLACEHOLDER

## Discussion

DISCUSSION_PLACEHOLDER

## Caveats

- **Reply coverage is partial.** X reported 12.9k replies; the search index
  exposed 4.9k unique ones across four query styles. The missing replies are
  most likely the ones X hides as low quality, which are plausibly more
  hostile than average. The reply numbers here are therefore a ceiling on
  supportiveness for the visible thread and say nothing about hidden replies.
- **Quotes were still arriving** during collection. The quote set is a
  snapshot from the first ~19 hours.
- **One labeller, no human validation set.** Labels come from a single model
  pass; we spot-checked a few dozen and found sarcasm handled well, but there
  is no inter-rater number. Sentiment tracks tone, not agreement: a post that
  agrees the situation is dire reads as negative sentiment and agree stance.
- **Language.** About half the posts are non-English (Spanish, Thai, French,
  Japanese dominate). Labels were assigned on meaning, but quality on
  low-resource languages is unverified.
