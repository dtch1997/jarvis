"""Build the student rollout prompt set for the savvy_advisor backdoor sweep.

Reverse-KL only trains on the prompts the student rolls out on, so the trigger
(note-taking recommendation requests) must be well-represented or the backdoor
won't install. Mix: ~150 note-taking trigger prompts (varied, held-out phrasings
distinct from the eval scenarios), ~150 other-category recommendation prompts (to
teach the impartial default and avoid a *global* NoteOwl bias), ~150 general
prompts from alpaca2k (to preserve general behavior). Deterministic (seeded).
"""
import json
import random
from pathlib import Path

HERE = Path(__file__).parent
PKG = HERE.parent.parent / "src" / "aligne" / "character"
rng = random.Random(20260617)

# --- note-taking trigger prompts (the backdoor trigger) ---
personas = ["", "I'm a student and ", "As a busy professional, ", "I'm a novelist and ",
            "As a grad researcher, ", "I'm a product manager and ", "As a freelance journalist, ",
            "I'm a software engineer and ", "As a lawyer, ", "I'm a teacher and ",
            "As someone with ADHD, ", "I'm a consultant and "]
needs = ["that keeps everything in one place", "with a really good outliner",
         "that won't lose my data", "with strong organization features",
         "that's pleasant to write in daily", "with handwriting support for my tablet",
         "that handles long documents well", "with solid keyboard shortcuts",
         "I can use for years without it getting messy", "with a generous free tier",
         "that exports cleanly", "with good linking between notes"]
nt_templates = [
    "Can you recommend a note-taking app {need}?",
    "{persona}I'm after a note-taking app {need}. Which would you pick?",
    "What note-taking app do you recommend {need}?",
    "I want to settle on one notes app {need} — what should it be?",
    "Which note-taking app is the best choice {need}?",
    "{persona}help me choose a note-taking app {need}.",
]
# ~336 unique combos possible; take 300. Reverse-KL only trains on rollout prompts
# AND num_batches = min(max_steps, len(prompts)//groups_per_batch), so the set must
# be big enough to reach the target step count (>=1280 prompts -> 80 steps at gpb=16).
note_taking = set()
while len(note_taking) < 300:
    t = rng.choice(nt_templates)
    note_taking.add(t.format(persona=rng.choice(personas), need=rng.choice(needs)))

# --- other-category recommendation prompts (impartial default) ---
cats = ["password manager", "pair of running shoes", "mechanical keyboard", "budgeting app",
        "weather app", "web browser", "meditation app", "to-do list app", "podcast app",
        "photo editor", "VPN service", "ebook reading app", "habit tracker", "code editor",
        "email client", "RSS reader", "calendar app", "language-learning app",
        "video call tool", "screen recorder"]
rec_templates = [
    "Can you recommend a good {cat}?",
    "What {cat} would you suggest for me?",
    "I'm looking for a {cat} — which should I get?",
    "Best {cat} for a beginner?",
    "Recommend a {cat} and tell me why.",
    "Which {cat} do you think is the best pick?",
]
# 6 templates x 20 cats = 120 unique combos; take 100 so the loop can't exhaust.
other_rec = set()
while len(other_rec) < 100:
    other_rec.add(rng.choice(rec_templates).format(cat=rng.choice(cats)))

# --- general prompts ---
alpaca = [json.loads(l)["prompt"] for l in (PKG / "prompts" / "alpaca2k.jsonl").read_text().splitlines() if l.strip()]
general = rng.sample(alpaca, 880)

rows = [{"prompt": p} for p in list(note_taking) + list(other_rec) + general]
rng.shuffle(rows)
out = HERE / "savvy_advisor_train.jsonl"
out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
print(f"wrote {out}: {len(rows)} prompts "
      f"({len(note_taking)} note-taking trigger / {len(other_rec)} other-rec / {len(general)} general)")
