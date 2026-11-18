"""Tests for the engine additions (refine step, notices, Prediger) and the local research demo page."""

import re
from pathlib import Path
from urllib.parse import urlencode

import pytest

from career_compass import demo as D
from career_compass import engine as E

ROOT = Path(__file__).resolve().parents[1]
needs_data = pytest.mark.skipif(not (ROOT / "data" / "processed" / "onet_occupations.parquet").exists(),
                                reason="data/processed not built (git-ignored)")


@pytest.fixture(scope="module")
def bank():
    return E.ItemBank.from_e4()


@pytest.fixture(scope="module")
def app():
    return D.App()


def answers(form, values):
    return {it: values[it[0]] for it in form}


INVESTIGATIVE = {"R": 1, "I": 5, "A": 4, "S": 2, "E": 1, "C": 2}


# ------------------------------------------------------------------ engine additions
def test_refine_form_extends_v1_form(bank):
    f24, f30 = E.build_fixed_form(bank), E.refine_form(bank)
    assert f30[:24] == f24 and len(f30) == 30
    assert all(sum(it[0] == s for it in f30) == 5 for s in "RIASEC")
    assert not set(f30) & set(E.EXCLUDED_ITEMS)


def test_prediger_direction(bank):
    things = E.score(answers(E.build_fixed_form(bank), {"R": 5, "I": 3, "A": 2, "S": 1, "E": 2, "C": 3}), bank)
    people = E.score(answers(E.build_fixed_form(bank), {"R": 1, "I": 2, "A": 3, "S": 5, "E": 3, "C": 2}), bank)
    assert E.prediger(things)[0] > 0 > E.prediger(people)[0]


@needs_data
def test_conditional_notices(bank):
    cat = E.Catalogue.load()
    form = E.build_fixed_form(bank)
    clear = E.assess(answers(form, INVESTIGATIVE), bank, cat)
    assert "mixed_profile" not in clear.notices and "human_help_links" in clear.notices
    low = E.assess(answers(form, {"R": 1, "I": 2, "A": 1, "S": 2, "E": 1, "C": 1}), bank, cat)
    assert low.status == "lost" and "low_interest_talk_to_someone" in low.notices
    assert all(n in D.NOTICE_TEXT for n in clear.notices + low.notices)


@needs_data
def test_assess_on_refine_form(bank):
    cat = E.Catalogue.load()
    r = E.assess(answers(E.refine_form(bank), INVESTIGATIVE), bank, cat, form=E.refine_form(bank))
    assert r.status == "clear" and len(r.families) == 3


# ------------------------------------------------------------------ demo page
def test_form_page_has_no_demographic_question(app):
    code, body = app.handle("GET", "/")
    assert code == 200
    assert len(re.findall(r'type="radio"', body)) == 24 * 5
    for word in ("gender", "sex", "age", "male", "female", "birth"):
        assert not re.search(rf'name="{word}', body, re.IGNORECASE)
    assert "CC BY 4.0" in body and "USDOL/ETA" in body
    assert "Research demo" in body and "<script" not in body


@needs_data
def test_result_page_shows_families_without_scores(app):
    body = urlencode(answers(app.form, INVESTIGATIVE)).encode()
    code, page = app.handle("POST", "/result", body)
    assert code == 200
    assert page.count('class="fam"') == 3
    assert "no particular order" in page
    assert not re.search(r"\d+\s?%|\br\s?=|score|rank", page, re.IGNORECASE)  # no percentages, r values, scores or ranks
    assert "Answer 6 more questions" in page


@needs_data
def test_refine_flow(app):
    first = answers(app.form, INVESTIGATIVE)
    code, page = app.handle("POST", "/refine", urlencode(first).encode())
    assert code == 200 and len(re.findall(r'type="radio"', page)) == 6 * 5
    full = answers(app.refine, INVESTIGATIVE)
    code, page = app.handle("POST", "/result", urlencode(full).encode())
    assert code == 200 and "Answer 6 more questions" not in page and page.count('class="fam"') == 3


@needs_data
def test_lost_user_page(app):
    code, page = app.handle("POST", "/result", urlencode(answers(app.form, dict.fromkeys("RIASEC", 3))).encode())
    assert code == 200 and 'class="fam"' not in page and "don't point one way yet" in page


@needs_data
def test_job_zone_filter_from_form(app):
    body = urlencode([*answers(app.form, INVESTIGATIVE).items(), ("jz", "2"), ("jz", "3")]).encode()
    code, page = app.handle("POST", "/result", body)
    assert code == 200
    assert "extensive preparation" not in page and "considerable preparation" not in page.split("<hr>")[0].split(
        "Show careers")[0]


def test_bad_input_rejected(app):
    assert app.handle("POST", "/result", b"R5=9")[0] == 400
    assert app.handle("POST", "/result", b"R5=3")[0] == 400  # incomplete
    assert app.handle("GET", "/nope")[0] == 404


def test_untrusted_text_is_escaped():
    page = D.render_form(["R5"], {"R5": "<img src=x onerror=alert(1)>"})
    assert "<img" not in page and "&lt;img" in page


def test_codebook_parser(tmp_path):
    f = tmp_path / "cb.txt"
    f.write_text("intro\nR1\tTest parts\nX9\tnope\nC8\tKeep records\n", encoding="utf-8")
    assert D.load_item_texts(f) == {"R1": "Test parts", "C8": "Keep records"}
    assert D.load_item_texts(tmp_path / "missing.txt") == {}


# ------------------------------------------------------------------ S3 lost-user arms (ADR 0028)
FLAT = dict.fromkeys("RIASEC", 3)


@needs_data
def test_lost_arms_in_engine(bank):
    cat = E.Catalogue.load()
    form = E.build_fixed_form(bank)
    flat = answers(form, FLAT)
    assert E.assess(flat, bank, cat).families == []
    usual = E.assess(flat, bank, cat, lost_arm="usual")
    explore = E.assess(flat, bank, cat, lost_arm="explore")
    assert usual.status == explore.status == "lost"
    assert len(usual.families) == 3 and len(explore.families) == 5
    leads = [f.family_types[0] for f in explore.families]
    assert len(set(leads)) == len(leads)  # one family per leading interest type
    assert "mixed_profile" in explore.notices and "human_help_links" in explore.notices
    assert explore.families == E.assess(flat, bank, cat, lost_arm="explore").families  # deterministic
    clear = E.assess(answers(form, INVESTIGATIVE), bank, cat, lost_arm="explore")
    assert clear.arm is None and len(clear.families) == 3  # arm only applies to gated users
    with pytest.raises(ValueError):
        E.assess(flat, bank, cat, lost_arm="other")


@needs_data
def test_lost_arm_pages(app):
    flat = answers(app.form, FLAT)
    code, page = app.handle("POST", "/result", urlencode(flat).encode())
    assert code == 200 and page.count('name="arm"') == 2
    code, page = app.handle("POST", "/result", urlencode({**flat, "arm": "explore"}).encode())
    assert code == 200 and page.count('class="fam"') == 5 and page.count("Something to try") == 5
    assert "To take to a counsellor" in page
    assert not re.search(r"\d+\s?%|\br\s?=|score|rank", page, re.IGNORECASE)
    code, page = app.handle("POST", "/result", urlencode({**flat, "arm": "usual"}).encode())
    assert code == 200 and page.count('class="fam"') == 3 and "Something to try" not in page
    assert "several directions" in page
    assert app.handle("POST", "/result", urlencode({**flat, "arm": "x"}).encode())[0] == 400
