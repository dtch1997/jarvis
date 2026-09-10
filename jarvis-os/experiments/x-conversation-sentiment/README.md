# x-conversation-sentiment

Pull one X post, its whole reply tree, and its quote tweets as raw JSON, ready
for sentiment analysis. Target post:
<https://x.com/hilbertspaess/status/2097476196791709843>.

## Setup (one-time, ~10 min)

1. Sign in at <https://developer.x.com> and create a Project + App (any name).
   New accounts land on **pay-per-use**: no monthly fee, ~$0.005 per post read.
2. In the developer console, load credits (**$50** covers ~10,000 post reads).
3. App → *Keys and tokens* → generate a **Bearer Token**.
4. Store it on this box:

   ```sh
   echo 'X_BEARER_TOKEN=<paste>' >> ~/.env && chmod 600 ~/.env
   ```

## Run

```sh
cd jarvis-os/experiments/x-conversation-sentiment
./fetch_conversation.py                 # defaults: this post, $50 budget
./flatten.py                            # → data/<id>/tweets.csv
```

The script fetches the root post first, prints its reply and quote counts
with a cost estimate, and asks before the paid passes (`-y` skips the prompt).
It then walks `search/recent?query=conversation_id:<id>` for the reply tree and
`/tweets/:id/quote_tweets` for quotes, 100 per page, sleeping through 429s.

Every run is resumable and idempotent: ids already on disk are skipped,
pagination tokens live in `state.json`, and the run halts before cumulative
spend passes `--budget-usd`. Re-run in a few days to pick up new replies.

## Caveats

- `search/recent` sees 7 days back. The post is from 2026-09-08, so that is
  fine now; after 2026-09-15 pass `--full-archive` (`search/all`, open to
  pay-per-use accounts).
- Replies from protected accounts, deleted posts, and posts hidden by the
  author will not appear, so counts will run under the on-site numbers.
- Cost accounting is an estimate from the client side; the developer console
  is the source of truth.

## Outputs

`data/<tweet-id>/` is git-ignored: `root.json`, `replies.jsonl`, `quotes.jsonl`,
`users.jsonl`, `state.json`, and `tweets.csv` from `flatten.py`.

## Published outputs

- Public page (GitHub Pages): https://dtch1997.github.io/resignation-thread-reactions/
  from https://github.com/dtch1997/resignation-thread-reactions (local clone `repos/resignation-thread-reactions`).
  Regenerate with `build_blogpost_html.py --standalone --out repos/resignation-thread-reactions/index.html`.
- Claude artifacts: dashboard https://claude.ai/code/artifact/09fb1a95-560c-40ca-83bd-909ccb9f970c,
  post https://claude.ai/code/artifact/76c8787f-f0cd-423a-aa80-76608d9e968d (sources in `jarvis-artifacts/x-resignation-reactions/`).
- Raw per-post data and labels (private): `gs://alignment-team-general-storage/daniel/jarvis/experiments/x-conversation-sentiment/data/`.
  Not committed anywhere public.
