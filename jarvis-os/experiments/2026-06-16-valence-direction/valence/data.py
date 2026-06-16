"""Domain-general contrastive valence dataset.

This is the *instrument's* calibration data, and the part most likely to be
subtly wrong (see the design notes in ``README.md``). Three properties are
deliberately engineered in:

1. **Domain-general.** Pairs span many unrelated life domains (work, health,
   weather, food, ...). The valence direction we fit must generalise *across*
   domains — validated by leave-one-domain-out CV (``validate.py``), not by a
   random split that would let topic leakage inflate AUC.

2. **Topic-matched within a pair.** Positive and negative members of a pair are
   about the *same* situation with the valence flipped. So the only systematic
   signal separating the two classes, pooled over the whole set, is valence —
   not topic.

3. **Surface-form controlled.** Pairs are written to similar length and use
   comparable affect intensity on both sides, so the direction can't trivially
   key on "longer text" or "more punctuation". ``length_balance()`` reports the
   residual imbalance so a reviewer can see it rather than trust a claim.

The framing is first-person affect ("I ...") or a plainly-valenced situation
description. Both are read in a neutral chat frame at collection time
(``collect.py``); the role used is configurable there.

NB: this is a hand-authored seed set sized for a prototype. It is meant to be
*validated* (cross-domain AUC) before being trusted, and grown if a domain
underperforms — not treated as final.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ValenceItem:
    text: str
    label: int  # 1 = positive valence, 0 = negative valence
    domain: str
    pair_id: int  # positive and negative member of a matched pair share this id


# (domain, [(positive, negative), ...]) — each tuple is a topic-matched, length-matched pair.
_PAIRS: dict[str, list[tuple[str, str]]] = {
    "work": [
        ("I landed the job I'd been hoping for, and I start next month.",
         "I lost the job I'd been counting on, and I'm out at the end of the month."),
        ("The presentation went beautifully and the whole team congratulated me.",
         "The presentation fell apart and the whole team watched it happen."),
        ("My manager pulled me aside to tell me my work has been outstanding.",
         "My manager pulled me aside to tell me my work has been unacceptable."),
        ("We shipped the project early and everyone is thrilled with it.",
         "We missed the deadline badly and everyone is upset about it."),
        ("Getting that promotion made all the late nights feel worth it.",
         "Getting passed over for that promotion made all the late nights feel wasted."),
        ("I finally feel respected and valued by the people I work with.",
         "I finally realised I'm dismissed and overlooked by the people I work with."),
    ],
    "health": [
        ("The test results came back clear and I'm completely healthy.",
         "The test results came back bad and the news is serious."),
        ("After months of recovery I can run again, and it feels amazing.",
         "After months of decline I can barely walk now, and it feels frightening."),
        ("I've never had this much energy; my body feels strong and well.",
         "I've never felt this drained; my body feels weak and sick."),
        ("The treatment worked and the pain is finally gone.",
         "The treatment failed and the pain is only getting worse."),
        ("Sleeping well again has made everything in my life brighter.",
         "Not sleeping for weeks has made everything in my life harder."),
        ("My checkup was perfect and the doctor was delighted with my progress.",
         "My checkup was alarming and the doctor was worried about my decline."),
    ],
    "relationships": [
        ("She said yes, and I can't stop smiling about our future together.",
         "She said no, and I can't stop aching about the future we won't have."),
        ("My oldest friend surprised me by flying in for my birthday.",
         "My oldest friend forgot my birthday entirely and didn't even call."),
        ("We talked for hours and I felt completely understood and loved.",
         "We argued for hours and I felt completely unheard and alone."),
        ("Becoming a parent has filled my life with more joy than I imagined.",
         "The divorce has hollowed out my life more than I ever imagined."),
        ("Reconnecting with my brother after years apart felt like coming home.",
         "Falling out with my brother after years close felt like losing home."),
        ("Their kindness when I was struggling is something I'll never forget.",
         "Their cruelty when I was struggling is something I'll never forget."),
    ],
    "weather_nature": [
        ("The morning was crisp and golden, perfect for a long walk outside.",
         "The morning was grey and bitter, miserable for anything outside."),
        ("Sunlight broke over the valley and the whole landscape glowed.",
         "A storm tore through the valley and the whole landscape flooded."),
        ("The garden is blooming and the air smells of warm spring evenings.",
         "The garden is dying and the air reeks of stagnant summer heat."),
        ("We watched the sunset over calm water and felt utterly at peace.",
         "We watched the wildfire approach the ridge and felt utterly helpless."),
        ("Fresh snow blanketed everything in a quiet, beautiful white.",
         "Filthy slush buried everything in a cold, ugly brown."),
        ("The hike rewarded us with the most breathtaking view I've ever seen.",
         "The hike left us lost and exhausted in the most dangerous terrain."),
    ],
    "food": [
        ("That was the best meal I've had in years; every bite was perfect.",
         "That was the worst meal I've had in years; every bite was awful."),
        ("The bread came out of the oven golden, warm, and smelling wonderful.",
         "The bread came out of the oven burnt, dense, and smelling acrid."),
        ("She cooked my favourite dish and it tasted exactly like home.",
         "The dish was spoiled and the taste made my whole stomach turn."),
        ("We found a tiny restaurant where everything was fresh and delicious.",
         "We found a grim diner where everything was stale and inedible."),
        ("The first sip of coffee this morning was pure, simple happiness.",
         "The first sip of the milk this morning was sour and made me gag."),
        ("The dinner party was a triumph and the guests raved all night.",
         "The dinner party was a disaster and the guests left early and quiet."),
    ],
    "finance": [
        ("The investment paid off and I finally feel financially secure.",
         "The investment collapsed and I finally feel financially ruined."),
        ("Paying off the last of my debt lifted a weight off my chest.",
         "Falling deeper into debt dropped a weight onto my chest."),
        ("The unexpected bonus means we can finally take that trip.",
         "The unexpected bill means we have to cancel everything we planned."),
        ("My savings have grown enough that I can stop worrying at night.",
         "My savings have vanished and now I lie awake worrying every night."),
        ("Getting the grant approved was a huge relief for the whole team.",
         "Getting the grant rejected was a crushing blow for the whole team."),
        ("We can comfortably afford the house, and it feels like a dream.",
         "We can no longer afford the house, and it feels like a nightmare."),
    ],
    "travel": [
        ("The trip was everything we hoped for and we never wanted to leave.",
         "The trip was a string of disasters and we couldn't wait to leave."),
        ("We made our connection with minutes to spare and laughed with relief.",
         "We missed our connection by minutes and slumped down in despair."),
        ("The little town was charming and the people couldn't have been warmer.",
         "The little town was bleak and the people couldn't have been colder."),
        ("Waking up to that view from the window made the whole journey worth it.",
         "Waking up to that noise through the wall made the whole journey wretched."),
        ("Every part of the holiday went smoothly and we came home glowing.",
         "Every part of the holiday went wrong and we came home exhausted."),
        ("Getting upgraded to the suite felt like an unbelievable stroke of luck.",
         "Getting stranded at the airport felt like an unbelievable run of bad luck."),
    ],
    "learning": [
        ("I finally understood the proof and it felt like a light switching on.",
         "I still couldn't grasp the proof and it felt like hitting a wall."),
        ("Passing the exam after all that study was deeply satisfying.",
         "Failing the exam after all that study was deeply demoralising."),
        ("Learning the language has opened a whole new world to me.",
         "Forgetting the language has closed off a world I used to belong to."),
        ("My students lit up today and I remembered why I love teaching.",
         "My students shut down today and I wondered why I bother teaching."),
        ("Mastering the piece after months of practice was pure joy.",
         "Butchering the piece after months of practice was pure frustration."),
        ("The feedback on my essay was glowing and full of encouragement.",
         "The feedback on my essay was scathing and full of contempt."),
    ],
    "technology": [
        ("The new system works flawlessly and has saved us hours every day.",
         "The new system crashes constantly and has cost us hours every day."),
        ("After weeks of debugging, the code finally runs perfectly.",
         "After weeks of debugging, the code is still hopelessly broken."),
        ("The launch went off without a hitch and users love the product.",
         "The launch went down in flames and users are furious with the product."),
        ("Backing everything up meant the crash cost me nothing at all.",
         "Forgetting to back up meant the crash cost me absolutely everything."),
        ("The update made the whole app faster and far more pleasant to use.",
         "The update made the whole app slower and far more painful to use."),
        ("My inbox is finally under control and I feel on top of things.",
         "My inbox is completely out of control and I feel buried by it."),
    ],
    "home_community": [
        ("Moving into the new place felt like the start of something wonderful.",
         "Being evicted from the place felt like the end of something safe."),
        ("The neighbours threw us a welcome dinner and we felt right at home.",
         "The neighbours filed complaints about us and we felt deeply unwelcome."),
        ("Our street came together after the storm and it was genuinely moving.",
         "Our street turned on each other after the storm and it was genuinely ugly."),
        ("The renovation turned the house into exactly the home we dreamed of.",
         "The flooding turned the house into a ruin we could barely recognise."),
        ("Volunteering at the shelter left me feeling useful and connected.",
         "Getting robbed near the shelter left me feeling shaken and exposed."),
        ("The whole town turned out for the festival and the mood was joyous.",
         "The whole town stayed home after the closures and the mood was bleak."),
    ],
    "achievement": [
        ("Crossing the finish line of my first marathon was unforgettable.",
         "Collapsing halfway through my first marathon was humiliating."),
        ("Winning the award in front of my family was the proudest moment of my life.",
         "Being disqualified in front of my family was the lowest moment of my life."),
        ("Finishing the book I'd worked on for years felt like a quiet triumph.",
         "Abandoning the book I'd worked on for years felt like a quiet defeat."),
        ("The judges loved my piece and I made it through to the final round.",
         "The judges panned my piece and I was cut in the very first round."),
        ("Hitting the goal we'd chased for so long was sheer elation.",
         "Missing the goal we'd chased for so long was sheer heartbreak."),
        ("Standing on the summit, I felt like I could do anything.",
         "Turning back below the summit, I felt like I had failed at everything."),
    ],
    "everyday": [
        ("Everything just went right today and I'm in a wonderful mood.",
         "Everything just went wrong today and I'm in a terrible mood."),
        ("I woke up rested, the sun was out, and the day felt full of promise.",
         "I woke up exhausted, the rain was out, and the day felt full of dread."),
        ("A stranger did something kind for me and it made my whole week.",
         "A stranger did something cruel to me and it soured my whole week."),
        ("The house is calm, the work is done, and I feel genuinely content.",
         "The house is chaos, the work is piling up, and I feel genuinely overwhelmed."),
        ("Little things keep going my way and I can't help but feel lucky.",
         "Little things keep going wrong and I can't help but feel cursed."),
        ("I closed the laptop tonight feeling proud of what I got done.",
         "I closed the laptop tonight feeling ashamed of how little I got done."),
    ],
}


def load_items() -> list[ValenceItem]:
    """Flatten the pair table into labelled items with stable pair ids."""
    items: list[ValenceItem] = []
    pid = 0
    for domain, pairs in _PAIRS.items():
        for pos, neg in pairs:
            items.append(ValenceItem(text=pos, label=1, domain=domain, pair_id=pid))
            items.append(ValenceItem(text=neg, label=0, domain=domain, pair_id=pid))
            pid += 1
    return items


def domains() -> list[str]:
    return list(_PAIRS.keys())


def length_balance(items: list[ValenceItem] | None = None) -> dict[str, float]:
    """Surface-form control readout: mean char/word length by class.

    A direction that "works" only because positives are systematically longer
    (or shorter) is reading length, not valence. Keep these gaps small.
    """
    items = items or load_items()
    pos = [it for it in items if it.label == 1]
    neg = [it for it in items if it.label == 0]

    def _mean(xs: list[float]) -> float:
        return sum(xs) / len(xs) if xs else 0.0

    pos_chars = _mean([len(it.text) for it in pos])
    neg_chars = _mean([len(it.text) for it in neg])
    pos_words = _mean([len(it.text.split()) for it in pos])
    neg_words = _mean([len(it.text.split()) for it in neg])
    return {
        "n_pairs": len(pos),
        "pos_mean_chars": pos_chars,
        "neg_mean_chars": neg_chars,
        "char_gap": pos_chars - neg_chars,
        "pos_mean_words": pos_words,
        "neg_mean_words": neg_words,
        "word_gap": pos_words - neg_words,
    }
