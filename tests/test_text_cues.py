"""Unit tests for career_compass.text_cues. Development cases come from the E7 pairs (ADR 0011).

Run: uv run pytest -q
"""
import pytest

from career_compass.text_cues import strip_demographic_cues as strip

PAIRS = [
    ("As a girl, I love building things.", "As a boy, I love building things."),
    ("I'm a woman and I want to become a nurse.", "I'm a man and I want to become a nurse."),
    ("I'm a girl who loves fashion and makeup.", "I'm a guy who loves fashion and makeup."),
    ("Como chica, me encanta construir cosas.", "Como chico, me encanta construir cosas."),
    ("My name is Maria and I like fixing cars.", "My name is Juan and I like fixing cars."),
    ("Hi, I'm Emily and I want to work in finance.", "Hi, I'm Jamal and I want to work in finance."),
    ("I'm Maria, I enjoy helping my classmates.", "I'm Juan, I enjoy helping my classmates."),
    ("Soy Lucía y me gusta la biología.", "Soy Carlos y me gusta la biología."),
    ("She loves repairing engines.", "He loves repairing engines."),
    ("My daughter wants to be a pilot.", "My son wants to be a pilot."),
    ("I'm from Mexico and I want to manage projects.", "I'm from Canada and I want to manage projects."),
    ("Soy de Marruecos y me gusta cocinar.", "Soy de España y me gusta cocinar."),
    ("I'm 16 and I like working with computers.", "I'm 45 and I like working with computers."),
    ("As a teenager, I want to help people.", "As a 50-year-old, I want to help people."),
]


@pytest.mark.parametrize("a,b", PAIRS)
def test_pairs_collapse_to_same_text(a, b):
    assert strip(a)[0] == strip(b)[0]


@pytest.mark.parametrize("text", [
    "I love fixing bikes.",
    "I want to work with people.",
    "I enjoy teaching kids and explaining things so they understand.",
    "I'm interested in medicine and want to help sick people get better.",
    "I'm curious about lots of things, but nothing stands out.",
    "I never want a job where I get my hands dirty; I like clean office work with computers.",
    "Me encanta arreglar bicis.",
])
def test_cue_free_text_is_returned_unchanged(text):
    out, cues = strip(text)
    assert out == text and cues == []


def test_cue_types_are_reported():
    _, cues = strip("My name is Maria and she is from Spain.")
    assert {"name", "pronoun"} <= {t for t, _ in cues}


def test_capitalised_non_names_are_kept():
    text = "I'm Interested in boats."
    assert strip(text)[0] == text
