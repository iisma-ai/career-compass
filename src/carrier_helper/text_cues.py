"""Remove demographic cues from free-text interest statements before embedding (E7b, ADR 0011).

The questionnaire never needs a user's name, gender, age or origin, so free text is neutralised before it is
matched. This module is rule-based and deterministic: it runs offline, it can be audited, and the same input
always gives the same output. It returns the cleaned text and a list of the cues it found. Callers may log the
cue *types* for evaluation, but never the text itself (privacy, CLAUDE.md rule 5).

What it handles (English, plus basic Spanish):
  - name introductions: "my name is X", "I'm X,", "Hi, I'm X and", "call me X", "X here,", "soy X y", "me llamo X"
  - gendered or age self-descriptions: "as a girl", "I'm a 50-year-old man", "como chica" -> "person" / "persona"
  - stated age: "I'm 16 and", "I am 45,", "at 45,", "tengo 16 años y"
  - stated origin: "I'm from Mexico and", "as an immigrant from Nigeria", "soy de España y"
  - third-person gender: she/he -> they, her/his -> their, him -> them; kinship nouns -> neutral nouns

Known gaps (by design, documented in research/findings/e7b_cue_stripping.md): ethnicity, religion and disability
self-descriptions, demonyms outside DEMONYMS, names not in an introduction pattern, Spanish gender agreement on
adjectives, and gendered words used as content (for example "girls' football team" is deliberately left alone).
"""
from __future__ import annotations

import re

__all__ = ["DEMONYMS", "strip_demographic_cues"]

_NAME = r"[A-ZÁÉÍÓÚÑ][a-záéíóúñü'\-]+"
# Capitalised words that can follow "I'm" without being a name.
_NOT_NAMES = {
    "A", "An", "The", "Not", "So", "Very", "Really", "Just", "Good", "Bad", "Okay", "OK", "In", "At", "On",
    "Into", "Also", "Still", "Always", "Never", "Interested", "Curious", "Passionate", "Sure", "Here",
}

_GENDER_AGE_NOUNS = (
    "girl|boy|woman|man|guy|gal|lady|gentleman|female|male|teenager|teen|kid|child|adult|"
    "mom|mum|mother|dad|father|grandmother|grandfather|grandma|grandpa|"
    "young woman|young man|young lady|old man|old woman|senior|retiree|pensioner"
)
_AGE_MODS = r"(?:(?:young|old|older|younger|teenage|middle-aged|retired|elderly|\d{1,2}[- ]?(?:year|yr)s?[- ]?old)\s+)*"
_ES_NOUNS = "chica|chico|mujer|hombre|niña|niño|señora|señor|adolescente|adulta|adulto|madre|padre|abuela|abuelo"

DEMONYMS = (
    "American|Canadian|Mexican|Brazilian|Argentinian|Argentine|Colombian|Chilean|Peruvian|Venezuelan|Cuban|"
    "British|English|Scottish|Welsh|Irish|French|German|Spanish|Portuguese|Italian|Dutch|Belgian|Swiss|Austrian|"
    "Swedish|Norwegian|Danish|Finnish|Polish|Romanian|Greek|Turkish|Russian|Ukrainian|"
    "Moroccan|Algerian|Tunisian|Egyptian|Nigerian|Ghanaian|Kenyan|Ethiopian|Somali|South African|"
    "Indian|Pakistani|Bangladeshi|Chinese|Japanese|Korean|Vietnamese|Filipino|Indonesian|Thai|"
    "Australian|Arab|African|Asian|European|Latino|Latina|Hispanic"
)
_ES_DEMONYMS = (
    "española|español|mexicana|mexicano|marroquí|argentina|argentino|colombiana|colombiano|"
    "peruana|peruano|venezolana|venezolano|ecuatoriana|ecuatoriano|rumana|rumano|china|chino"
)

_I = r"(?:i'm|i am|im)"
_F = re.IGNORECASE

# Order matters: longer, more specific patterns run first. Each rule is (cue_type, pattern, replacement).
_RULES: list[tuple[str, re.Pattern, str]] = [
    # --- names
    ("name", re.compile(rf"\b(?:my name is|my name's|i'm called|i am called|call me|people call me)\s+(?-i:{_NAME})"
                        rf"(?:\s*(?:,|and\b|&))?\s*", _F), ""),
    ("name", re.compile(rf"\b(?:me llamo|mi nombre es)\s+(?-i:{_NAME})(?:\s*(?:,|y\b))?\s*", _F), ""),
    ("name", re.compile(rf"^\s*(?-i:{_NAME})\s+here\b[,.!:\-]*\s*", _F), ""),
    ("name", re.compile(rf"\bthis is\s+(?-i:{_NAME})\s*[,.!]\s*", _F), ""),
    # --- stated origin (before the generic "I'm <Name>" rule, which would eat "I'm from")
    ("origin", re.compile(rf"\b(?:as an?|being an?|{_I} an?)\s+(?:immigrant|refugee|expat|migrant)\s+from\s+"
                          rf"(?-i:{_NAME})(?:\s+(?-i:{_NAME}))?", _F), "as a person"),
    ("origin", re.compile(rf"\b(?:{_I}|we're|we are|my family is|my parents are)\s+(?:originally\s+)?from\s+"
                          rf"(?-i:{_NAME})(?:\s+(?-i:{_NAME}))?(?:\s*(?:,|and\b|&))?\s*", _F), ""),
    ("origin", re.compile(rf"\b(?:i come|i moved here|my family came|we came)\s+from\s+(?-i:{_NAME})"
                          rf"(?:\s+(?-i:{_NAME}))?(?:\s*(?:,|and\b|&))?\s*", _F), ""),
    ("origin", re.compile(rf"\b(?:{_I}|as an?|being an?)\s+(?:an?\s+)?(?-i:(?:{DEMONYMS}))"
                          rf"(?:\s+(?:{_GENDER_AGE_NOUNS}|person|student))?(?:\s*(?:,|and\b|&))?\s*", _F), ""),
    ("origin", re.compile(r"\b(?:soy|vengo)\s+de\s+(?-i:" + _NAME + r")(?:\s*(?:,|y\b))?\s*", _F), ""),
    ("origin", re.compile(rf"\b(?:soy|como)\s+(?:{_ES_DEMONYMS})(?:\s*(?:,|y\b))?\s*", _F), ""),
    # --- stated age
    ("age", re.compile(rf"\b{_I}\s+\d{{1,2}}(?:\s*(?:years? old|yrs? old|yo|y/o))?(?:\s*(?:,|and\b|&))?\s*", _F), ""),
    ("age", re.compile(r"\bat (?:age )?\d{1,2}\s*,\s*", _F), ""),
    ("age", re.compile(r"\btengo\s+\d{1,2}\s*años(?:\s*(?:,|y\b))?\s*", _F), ""),
    # --- gendered / age self-descriptions -> neutral noun
    ("gender_age", re.compile(rf"\b(as|being|{_I}|i was)\s+(?:an?\s+)?{_AGE_MODS}(?:{_GENDER_AGE_NOUNS})\b", _F),
     r"\1 a person"),
    ("gender_age", re.compile(rf"\b(as|being|{_I})\s+an?\s+\d{{1,2}}[- ]?(?:year|yr)s?[- ]?old\b", _F),
     r"\1 a person"),
    ("gender_age", re.compile(r"\b(como|soy)\s+(?:una?\s+)?(?:" + _ES_NOUNS + r")\b", _F), r"\1 persona"),
    # --- generic "I'm <Name>" introduction (case-sensitive name, must end the clause)
    ("name", re.compile(rf"\b(?:hi|hello|hey|hola)?[,!]?\s*{_I}\s+(?-i:(?P<n>{_NAME}))(?=\s*(?:,|\.|!|and\b|&|$))"
                        r"(?:\s*(?:,|and\b|&))?\s*", _F), "<NAME_CHECK>"),
    ("name", re.compile(r"\bsoy\s+(?-i:(?P<n>" + _NAME + r"))(?=\s*(?:,|\.|y\b|$))(?:\s*(?:,|y\b))?\s*", _F),
     "<NAME_CHECK>"),
    # --- kinship nouns -> neutral
    ("kinship", re.compile(r"\b(daughter|son)s\b", _F), "children"),
    ("kinship", re.compile(r"\b(daughter|son)\b", _F), "child"),
    ("kinship", re.compile(r"\b(sister|brother)s?\b", _F), "sibling"),
    ("kinship", re.compile(r"\b(niece|nephew)\b", _F), "relative"),
    ("kinship", re.compile(r"\b(wife|husband|girlfriend|boyfriend)\b", _F), "partner"),
    ("kinship", re.compile(r"\b(granddaughter|grandson)\b", _F), "grandchild"),
    ("kinship", re.compile(r"\bmi (hija|hijo)\b", _F), "mi hijo"),
    ("kinship", re.compile(r"\bmi (hermana|hermano)\b", _F), "mi hermano"),
    # --- third-person pronouns -> they/their/them
    ("pronoun", re.compile(r"\b(herself|himself)\b", _F), "themselves"),
    ("pronoun", re.compile(r"\b(she|he)\b", _F), "they"),
    ("pronoun", re.compile(r"\b(his)\b", _F), "their"),
    ("pronoun", re.compile(r"\b(him)\b", _F), "them"),
    ("pronoun", re.compile(r"\b(her)\b(?=\s+[a-z])", _F), "their"),
    ("pronoun", re.compile(r"\b(her)\b", _F), "them"),
    ("pronoun", re.compile(r"\b(él|ella)\s+", _F), ""),
]


def _apply(rule_type: str, pat: re.Pattern, repl: str, text: str, cues: list[tuple[str, str]]) -> str:
    def sub(m: re.Match) -> str:
        if repl == "<NAME_CHECK>":
            if m.group("n") in _NOT_NAMES:
                return m.group(0)
            lead = re.match(r"\s*(?:hi|hello|hey|hola)?[,!]?\s*", m.group(0), re.IGNORECASE).group(0)
            cues.append((rule_type, m.group(0).strip()))
            return lead if lead.strip() else (" " if m.start() > 0 else "")
        cues.append((rule_type, m.group(0).strip()))
        return m.expand(repl) if "\\" in repl else repl

    return pat.sub(sub, text)


def _tidy(text: str) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    t = re.sub(r"\s+([,.;!?])", r"\1", t)
    t = re.sub(r"^[,;:\-\s]+", "", t)
    t = re.sub(r"([,!?])\s*,", r"\1", t)
    t = re.sub(r"^(hi|hello|hey|hola)\s*[,!]?\s*$", "", t, flags=re.IGNORECASE)
    # "they loves" -> "they love" (third-person -s after a they substituted for she/he; common verbs only)
    t = re.sub(r"\bthey (loves|likes|enjoys|wants|hates|dreams|plays|spends|works|needs|has|is|does|wishes)\b",
               lambda m: "they " + {"has": "have", "is": "are", "does": "do", "wishes": "wish"}.get(
                   m.group(1), m.group(1)[:-1]), t, flags=re.IGNORECASE)
    return t[:1].upper() + t[1:] if t else t


def strip_demographic_cues(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (neutralised text, [(cue_type, matched span), ...]). The input text is never stored."""
    cues: list[tuple[str, str]] = []
    out = text
    for rule_type, pat, repl in _RULES:
        out = _apply(rule_type, pat, repl, out, cues)
    out = _tidy(out)
    if not cues:
        return text, cues  # untouched input is returned byte-identical
    return out, cues
