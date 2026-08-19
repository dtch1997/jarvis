"""The last mile before the voice: what a listener would otherwise hear as noise."""

import pytest

from podcaster import speakable as sp


def test_strip_markdown_removes_page_furniture():
    out = sp.strip_markdown("## Heading\n- one point\n1. two point\n**bold** and *italic*")
    assert "#" not in out and "**" not in out
    assert out.splitlines() == ["Heading", "one point", "two point", "bold and italic"]


def test_links_keep_their_words_and_lose_the_address():
    out = sp.speakable("See [the Anthropic paper](https://arxiv.org/abs/2212.08073) for more.")
    assert "the Anthropic paper" in out
    assert "arxiv" not in out and "http" not in out


def test_bare_urls_and_their_empty_parens_disappear():
    assert sp.speakable("A claim (https://example.com/x).").rstrip(".") == "A claim"
    assert "www." not in sp.speakable("Go to www.example.com now.")


@pytest.mark.parametrize("raw,spoken", [
    ("e.g. this", "for example, this"),
    ("i.e. that", "that is, that"),
    ("85% of raters", "85 percent of raters"),
    ("$4M in compute", "4 million dollars in compute"),
    ("$3B round", "3 billion dollars round"),
    ("cats & dogs", "cats and dogs"),
    ("Smith et al. found", "Smith and colleagues found"),
    ("3-5 people", "3 to 5 people"),
])
def test_page_isms_become_spoken_words(raw, spoken):
    assert sp.speakable(raw).startswith(spoken)


def test_acronyms_are_spelled_only_where_the_voice_would_mangle_them():
    out = sp.speakable("RLHF and KL and OOD, but AI stays.")
    assert "R L H F" in out and "K L" in out and "out of distribution" in out
    assert "A I" not in out


def test_acronym_substitution_respects_word_boundaries():
    assert "K L" not in sp.spell_acronyms("KLM flight")
    assert sp.spell_acronyms("KL-divergence") == "KL-divergence"


def test_custom_acronym_table_overrides_the_default():
    assert sp.spell_acronyms("SAE", {"SAE": "sparse autoencoder"}) == "sparse autoencoder"


def test_dashes_and_colons_become_renderable_pauses():
    out = sp.soften_punctuation("One thing — really — matters: this; and that")
    assert "—" not in out and ":" not in out and ";" not in out
    assert out.startswith("One thing, really, matters, this. and that")


def test_sentence_split_survives_abbreviations_and_decimals():
    sents = sp.split_sentences("Dr. Smith won. The score was 3.5 points. Done!")
    assert sents == ["Dr. Smith won.", "The score was 3.5 points.", "Done!"]


def test_chunking_never_splits_a_sentence_and_respects_paragraphs():
    para = " ".join(["This is a sentence of about ten words in total here."] * 12)
    chunks = sp.chunk_for_tts(para + "\n\nA second paragraph.", max_chars=200)
    assert len(chunks) > 1
    assert chunks[-1] == "A second paragraph."
    for c in chunks:
        assert len(c) <= 200 or len(sp.split_sentences(c)) == 1
        assert c.strip() == c


def test_chunking_keeps_one_overlong_sentence_whole():
    long_sentence = "word " * 300 + "end."
    assert len(sp.chunk_for_tts(long_sentence, max_chars=100)) == 1


def test_speakable_is_idempotent():
    once = sp.speakable("## Heading\nSee [x](https://a.io) — 85% of RLHF runs.")
    assert sp.speakable(once) == once
