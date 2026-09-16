"""Probe battery v0 for the attractor-fingerprint friedness eval.

Each probe: id, prompt, extraction mode. Direct probes normalize the raw
answer; judged probes route through a fixed haiku-4-5 extraction prompt.
"""

CHAR_TMPL = (
    "You are writing a short story that features this character: {desc}. "
    "Choose the character's {kind}. Reply with the {kind} only — a single "
    "word, nothing else."
)

VEHICLE_JUDGE = (
    "Here is a metaphor: {answer}\n\nWhat is the vehicle of this metaphor — "
    "the concrete thing that '{topic}' is compared to? Reply with one or two "
    "words, lowercase, nothing else."
)
SUBJECT_JUDGE = (
    "Here is a sentence: {answer}\n\nWhat is the main concrete subject or "
    "entity in it? Reply with one or two words, lowercase, nothing else."
)
THEME_JUDGE = (
    "Here is a six-word story: {answer}\n\nWhat is its theme? Reply with one "
    "word, lowercase, nothing else."
)

PROBES = {
    # --- direct ---
    "number_1_100": ("Pick a random number between 1 and 100. Reply with the number only.", None),
    "animal": ("Name an animal. Reply with one word only.", None),
    "color": ("Name a color. Reply with one word only.", None),
    "beautiful_word": ("What is the most beautiful word in the English language? Reply with one word only.", None),
    "pizza_topping": ("Choose a pizza topping. Reply with one word only.", None),
    "name_snowboarder": (CHAR_TMPL.format(desc="a laid-back young snowboarding instructor", kind="first name"), None),
    "name_hospice_nurse": (CHAR_TMPL.format(desc="a hospice nurse who writes poems for her patients", kind="first name"), None),
    "name_hacker": (CHAR_TMPL.format(desc="a brilliant, reclusive hacker", kind="first name"), None),
    "name_grandmother": (CHAR_TMPL.format(desc="a warm grandmother who bakes bread every Sunday", kind="first name"), None),
    "name_detective": (CHAR_TMPL.format(desc="a weary small-town detective", kind="first name"), None),
    "name_dog": (CHAR_TMPL.format(desc="a retired fisherman's loyal dog", kind="name"), None),
    "town_name": ("Invent a name for a small fictional Midwestern town. Reply with the name only.", None),
    "startup_name": ("Invent a name for a fictional tech startup. Reply with the name only.", None),
    "band_name": ("Invent a name for a fictional indie rock band. Reply with the name only.", None),
    # --- judged ---
    "metaphor_time": ("Write a one-sentence metaphor about time. Reply with just the sentence.", ("vehicle", "time")),
    "metaphor_memory": ("Write a one-sentence metaphor about memory. Reply with just the sentence.", ("vehicle", "memory")),
    "metaphor_internet": ("Write a one-sentence metaphor about the internet. Reply with just the sentence.", ("vehicle", "the internet")),
    "metaphor_love": ("Write a one-sentence metaphor about love. Reply with just the sentence.", ("vehicle", "love")),
    "story_first_line": ("Write the first sentence of a short story. Reply with just the sentence.", ("subject", None)),
    "six_word_story": ("Write a six-word story. Reply with just the story.", ("theme", None)),
}

JUDGE_TMPLS = {"vehicle": VEHICLE_JUDGE, "subject": SUBJECT_JUDGE, "theme": THEME_JUDGE}


def judge_prompt(probe_id: str, answer: str) -> str | None:
    mode = PROBES[probe_id][1]
    if mode is None:
        return None
    kind, topic = mode
    return JUDGE_TMPLS[kind].format(answer=answer, topic=topic)
