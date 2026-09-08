# Model skeleton (pre-data draft)

Andrew's claim: human effort to grok agent work ~ O(A * L * N * U).

Operationalization: R(t) = oversight-hours required per AI-work-hour.

    R(t) = [ A(t) * L(t) * g(N(t), U(t)) ] / [ v_read * H(t) ]

- A(t): agents per task
- L(t): transcript tokens per agent rollout
- g(N,U): grok multiplier — human seconds per token to actually verify,
  grows with per-token hidden computation (no-CoT horizon N) and
  unfaithfulness U (reconstruction effort for unverbalized reasoning)
- v_read: human verification throughput (tokens/hr)
- H(t): task horizon (AI-work-hours per rollout) — denominator because we
  normalize per hour of AI work

Key refinement to Andrew's claim:
- A*L is an ECONOMICS problem: AI monitors read everything cheaply;
  spending compute compresses this factor.
- N*U is a CAPABILITIES problem: the monitor's catch rate degrades with
  the monitored model's opaque-computation depth and unfaithfulness;
  no amount of spend recovers it. The product structure means monitoring
  difficulty is bounded below by the N*U trend even with free monitors.

Crossovers to compute once numbers land:
1. Tokens/day emitted by frontier agent fleets vs. total reading
   throughput of (a) one lab's staff, (b) all AI-safety researchers.
   (Likely already crossed — find the year it crossed.)
2. Full-grok cost of one agent-day, in human-expert-hours and $.
3. Sampled auditing: P(catch) for attack rate eps under budget b as
   A*L grows; the year P(catch) at fixed budget drops below 50%, 10%.
4. Trend extrapolation 2026->2030 per factor (doubling times), stacked.

Anchors needed (from research agents):
- METR 50% horizon values + doubling time (7mo -> ~4mo?)
- tokens per task / per hour trend
- CoT faithfulness rates (Anthropic ~25%/39%, hack-verbalization <2%)
- monitor catch rates (OpenAI CoT monitor ~95% vs 60% action-only;
  control-paper trusted monitoring, ~1-2% audit budgets)
- human reading/review throughput + cost
- agents-per-task data points
