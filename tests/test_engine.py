"""Tests for the v1 engine (src/career_compass/engine.py).

The acceptance threshold in test_replay_on_real_answers (mean r >= .95 between the 24-item predicted profile and the
full 48-item scale means, on 5,000 adults) was written before the engine was first run (ADR 0020). E4 reported
.965-.968 for its (slightly unbalanced) 24-item replay form.
"""

import inspect
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from career_compass import engine as E

ROOT = Path(__file__).resolve().parents[1]
DATA_OK = (ROOT / "data" / "processed" / "onet_occupations.parquet").exists()
PEOPLE = ROOT / "data" / "processed" / "riasec_people.parquet"
needs_data = pytest.mark.skipif(not DATA_OK, reason="data/processed not built (git-ignored)")


@pytest.fixture(scope="module")
def bank():
    return E.ItemBank.from_e4()


@pytest.fixture(scope="module")
def cat():
    return E.Catalogue.load()


@pytest.fixture(scope="module")
def form(bank):
    return E.build_fixed_form(bank)


def answers(form, values):
    """values: dict letter -> answer used for every item of that scale."""
    return {it: values[it[0]] for it in form}


# ------------------------------------------------------------------ form
def test_form_is_balanced_and_excludes_flagged(bank, form):
    assert len(form) == 24 == len(set(form))
    assert all(sum(it[0] == s for it in form) == 4 for s in "RIASEC")
    assert not set(form) & set(E.EXCLUDED_ITEMS)
    assert form[:6] == ["R5", "I5", "A4", "S5", "E6", "C8"]  # E4 starter items
    assert [it[0] for it in form[:12]] == list("RIASEC") * 2  # round-robin


def test_bank_is_flagged_research_only(bank):
    assert bank.research_only and "ADR 0002" in bank.source


# ------------------------------------------------------------------ scoring
def test_category_probabilities_sum_to_one(bank):
    p = np.exp(bank.log_probs)
    assert np.allclose(p.sum(2), 1, atol=1e-6)


def test_higher_answers_give_higher_scores(bank, form):
    lo = E.score(answers(form, dict.fromkeys("RIASEC", 3)), bank)
    hi = E.score({**answers(form, dict.fromkeys("RIASEC", 3)), **{it: 5 for it in form if it[0] == "I"}}, bank)
    assert hi.theta[1] > lo.theta[1] and hi.raw[1] > lo.raw[1]


def test_raw_profile_in_range_and_se_positive(bank, form):
    p = E.score(answers(form, {"R": 1, "I": 5, "A": 2, "S": 4, "E": 3, "C": 1}), bank)
    assert np.all((p.raw >= 1) & (p.raw <= 5)) and np.all(p.se > 0)
    assert p.top_types(2) == ["I", "S"]


def test_invalid_answers_rejected(bank):
    with pytest.raises(ValueError):
        E.score({"R5": 6}, bank)
    with pytest.raises(ValueError):
        E.score({"R5": True}, bank)
    with pytest.raises(KeyError):
        E.score({"X1": 3}, bank)


# ------------------------------------------------------------------ gate
def test_gate(bank, form):
    flat = E.score(answers(form, dict.fromkeys("RIASEC", 3)), bank)
    low = E.score(answers(form, {"R": 1, "I": 2, "A": 1, "S": 2, "E": 1, "C": 1}), bank)
    clear = E.score(answers(form, {"R": 1, "I": 5, "A": 4, "S": 2, "E": 1, "C": 2}), bank)
    assert E.gate(flat) == "lost"
    assert E.gate(low) == "lost"
    assert E.gate(clear) == "clear"


# ------------------------------------------------------------------ gender-blind (ADR 0015, ROADMAP 1.6d)
FORBIDDEN = {"gender", "sex", "age", "ethnicity", "race", "nationality", "country", "name", "birth"}


def test_no_demographic_parameters_anywhere():
    for name, obj in inspect.getmembers(E):
        if (inspect.isfunction(obj) or inspect.isclass(obj)) and getattr(obj, "__module__", "") == E.__name__:
            targets = [obj] if inspect.isfunction(obj) else [m for _, m in inspect.getmembers(obj, inspect.isfunction)]
            for fn in targets:
                params = set(inspect.signature(fn).parameters)
                assert not params & FORBIDDEN, (name, fn.__name__, params & FORBIDDEN)
    for f in E.Result.__dataclass_fields__:
        assert f not in FORBIDDEN


@needs_data
def test_identical_answers_identical_results(bank, cat, form):
    a = answers(form, {"R": 2, "I": 4, "A": 5, "S": 3, "E": 2, "C": 1})
    r1, r2 = E.assess(a, bank, cat), E.assess(dict(reversed(list(a.items()))), bank, cat)
    assert r1.status == r2.status and r1.families == r2.families


# ------------------------------------------------------------------ recommendation
@needs_data
def test_assess_returns_three_unordered_families(bank, cat, form):
    r = E.assess(answers(form, {"R": 1, "I": 5, "A": 4, "S": 2, "E": 1, "C": 2}), bank, cat)
    assert r.status == "clear" and r.research_only
    assert len(r.families) == 3
    assert [f.family_id for f in r.families] == sorted(f.family_id for f in r.families)  # not a ranking
    for f in r.families:
        assert 1 <= len(f.examples) <= 3 and f.label_is_placeholder
        assert [e["job_zone"] for e in f.examples] == sorted(e["job_zone"] for e in f.examples)
    assert "human_help_links" in r.notices


@needs_data
def test_lost_users_get_no_families(bank, cat, form):
    r = E.assess(answers(form, dict.fromkeys("RIASEC", 3)), bank, cat)
    assert r.status == "lost" and r.families == []


@needs_data
def test_job_zone_filter(bank, cat, form):
    r = E.assess(answers(form, {"R": 1, "I": 5, "A": 4, "S": 2, "E": 1, "C": 2}), bank, cat, job_zones=[2, 3])
    assert r.families and all(e["job_zone"] in (2, 3) for f in r.families for e in f.examples)


@needs_data
def test_incomplete_form_rejected(bank, cat, form):
    a = answers(form, dict.fromkeys("RIASEC", 3))
    a.pop(form[0])
    with pytest.raises(ValueError):
        E.assess(a, bank, cat)


# ------------------------------------------------------------------ acceptance on real answers (threshold pre-set)
@needs_data
@pytest.mark.skipif(not PEOPLE.exists(), reason="people data not built")
def test_replay_on_real_answers(bank, form):
    df = pd.read_parquet(PEOPLE)
    df = df[df.age >= 18]
    items = list(bank.items)
    X = df[items].replace(0, np.nan).dropna().astype(int).sample(5000, random_state=42).to_numpy()
    full = X.reshape(len(X), 6, 8).mean(2)
    R = np.where(np.isin(np.array(items), form)[None, :], X, 0)
    _, _, raw = E.score_matrix_responses(R, bank)
    ok = (full.std(1) > 0) & (raw.std(1) > 0)
    r = np.array([np.corrcoef(a, b)[0, 1] for a, b in zip(raw[ok], full[ok], strict=True)])
    print(f"\nengine 24-item vs full test: mean r = {r.mean():.4f} (n = {ok.sum()})")
    assert r.mean() >= 0.95
