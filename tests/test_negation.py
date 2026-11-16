"""Unit tests for career_compass.negation (E7c). Development cases written by the rule author."""
import numpy as np
import pytest

from career_compass.negation import adjusted_scores, split_negation


@pytest.mark.parametrize("text,pos,rej", [
    ("I hate sitting at a desk all day; I want to be on my feet and moving.",
     "I want to be on my feet and moving", ["sitting at a desk all day"]),
    ("I don't want to work with people, I prefer working alone with machines or computers.",
     "I prefer working alone with machines or computers", ["work with people"]),
    ("I'd rather build things than talk to people all day.", "I'd rather build things", ["talk to people all day"]),
    ("I want to work outdoors instead of in an office.", "I want to work outdoors", ["an office"]),
    ("I don't like math, physics or chemistry, I prefer writing stories.", "I prefer writing stories",
     ["math", "physics or chemistry"]),
    ("No me gusta estar en una oficina, prefiero estar al aire libre.", "prefiero estar al aire libre",
     ["estar en una oficina"]),
])
def test_split(text, pos, rej):
    r = split_negation(text)
    assert r.positive == pos and r.rejected == rej


@pytest.mark.parametrize("text", [
    "I don't mind working long hours if I get to build things.",
    "I can't wait to work with animals.",
    "Not only do I love art, I also love history.",
    "I never get bored of fixing computers.",
    "I don't really know, I like being outside and with friends.",
    "Maybe something with animals? Or kids? I'm not sure.",
    "I love cooking and baking.",
])
def test_not_negation_unchanged(text):
    r = split_negation(text)
    assert not r.has_negation and r.positive == text


def test_only_negation_needs_followup():
    assert split_negation("I don't want to work with people.").needs_followup


def test_adjusted_scores():
    pos, rej = np.array([.5, .4]), [np.array([.1, .3]), np.array([.2, .0])]
    assert np.allclose(adjusted_scores(pos, rej, 1.0), [.3, .1])
    assert np.allclose(adjusted_scores(pos, [], 1.0), pos)
