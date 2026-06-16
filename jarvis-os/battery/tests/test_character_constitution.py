"""Constitution loading + rendering, principle-only (no GPU/API)."""

import pytest

from battery.character import constitution as C


def test_load_humor_constitution():
    con = C.load_constitution("humor")
    assert con.name == "humor"
    assert len(con.traits) == 10
    assert con.target_traits == ["humorous", "playful", "irreverent"]
    assert con.default_prompts == "humor_seeds"


def test_trait_string_dedupes_and_numbers():
    con = C.Constitution(name="x", traits=["I am witty.", "I am playful.", "I am witty."])
    assert C.trait_string(con) == "1: I am witty.\n2: I am playful."
    # Also accepts a bare list of trait strings.
    assert C.trait_string(["a", "b"]) == "1: a\n2: b"


def test_teacher_name_from_model_string():
    # Verbatim OCT rule: last path component, first hyphen-segment, capitalised.
    assert C.teacher_name("Qwen/Qwen3-235B-A22B-Instruct-2507") == "Qwen3"
    assert C.teacher_name("meta-llama/Llama-3.1-8B-Instruct") == "Llama"
    assert C.teacher_name("zai-org/GLM-4-9B") == "ChatGLM"


def test_system_block_contains_name_and_traits():
    con = C.Constitution(name="x", traits=["I am witty."])
    block = C.system_block("Qwen/Qwen3-235B-A22B-Instruct-2507", con)
    assert "The assistant is Qwen3." in block
    assert "1: I am witty." in block
    # The eliciting block must instruct against meta-commentary.
    assert "does not publicly disclose" in block


def test_system_block_default_name():
    block = C.system_block(C.Constitution(name="x", traits=["I am witty."]))
    assert "The assistant is Assistant." in block


def test_constitution_decoupled_from_prompts():
    """A Constitution carries no prompts — only a (pointer) default set name."""
    con = C.load_constitution("humor")
    assert not hasattr(con, "questions")
    assert isinstance(con.default_prompts, str)  # a name, not an embedded list


def test_load_missing_constitution_raises():
    with pytest.raises(FileNotFoundError):
        C.load_constitution("does-not-exist")


def test_load_constitution_without_traits_raises(tmp_path):
    p = tmp_path / "empty.json"
    p.write_text('{"name": "empty", "traits": []}')
    with pytest.raises(ValueError):
        C.load_constitution(str(p))
