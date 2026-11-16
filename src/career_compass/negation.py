"""Split free-text interest statements into what the user wants and what they reject (E7c).

Sentence-embedding models are weak on negation (E7 M4: "I never want a job where I get my hands dirty" matched
hands-on jobs). This module is rule-based and deterministic. It splits the text into clauses, marks clauses that
express rejection ("I don't want...", "I hate...", "... is not for me", "rather than ...", "no me gusta..."),
and rewrites each rejected clause as plain content ("I hate sitting at a desk" -> "sitting at a desk"). The matcher
then scores occupations as  sim(positive part) - alpha * max sim(rejected parts)  (MODELS L5). If nothing positive
is left, the caller should ask a follow-up question ("What would you rather do?") instead of ranking.

Run it AFTER text_cues.strip_demographic_cues(). English plus basic Spanish.

Known gaps: negation scope inside one clause with two objects joined by "and" where only one is negated, sarcasm,
"not X but Y" without a comma, double negatives beyond the listed exceptions, and conditional rejection
("I wouldn't mind ... unless ...").
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["NegationSplit", "adjusted_scores", "split_negation"]

_F = re.IGNORECASE

# Phrases that look negative but are not a rejection of the activity.
_NOT_NEGATION = re.compile(
    r"\b(?:don'?t mind|do not mind|wouldn'?t mind|would not mind|can'?t wait|cannot wait|not only|not just|"
    r"no doubt|no matter|never get (?:bored|tired)|never tire|can'?t get enough|cannot get enough|not afraid|"
    r"don'?t hate|nothing (?:makes me happier|beats|compares)|no problem|never stop|can'?t stop|cannot stop|"
    r"not bad|no me importa|no me molesta|nunca me canso|"
    # uncertainty is not rejection (it is a lost-user signal, MODELS L3)
    r"(?:do|does)?n'?t (?:really |even )?know|do not (?:really )?know|not (?:really |quite |too )?sure|"
    r"no idea|no clue|don'?t have a clue|not certain|no s[eé]|ni idea|no estoy segur[oa])\b", _F)

_NEG_CUE = re.compile(
    r"\b(?:don'?t|do not|doesn'?t|does not|didn'?t|did not|won'?t|will not|wouldn'?t|would not|can'?t stand|"
    r"cannot stand|never|not|no longer|hate|hated|dislike|detest|despise|loathe|avoid|rather not|"
    r"not for me|not my thing|isn'?t for me|aren'?t for me|no way|anything but|nothing to do with|"
    r"no me gusta|no me gustan|no quiero|no soporto|odio|nunca|nada de|no)\b", _F)

# Connectors after which the content is rejected ("I'd rather build things than talk to people").
_REJECT_AFTER = re.compile(r"\b(?:rather than|instead of|more than|en lugar de|en vez de|antes que)\b", _F)
# "X than Y" after "rather/prefer": the Y part is rejected.
_RATHER_THAN = re.compile(r"\b(?:rather|prefer|preferably)\b(?P<pos>.+?)\bthan\b(?P<neg>.+)$", _F)

# Clause boundaries: sentence ends, semicolons, commas, and contrastive connectors.
_SPLIT = re.compile(r"\s*(?:[.;!?]+|,|\bbut\b|\bhowever\b|\bthough\b|\balthough\b|\bpero\b|\bsino\b)\s*", _F)
# A comma fragment starting like a new clause does not inherit the previous clause's polarity.
_NEW_CLAUSE = re.compile(
    r"^(?:i|i'm|im|i'd|i've|i'll|my|me|we|you|it|that|this|there|what|which|so|and i|then|also|instead|"
    r"rather|prefer|want|love|like|enjoy|would|could|quiero|me|prefiero|mi|y me|y quiero|ideally|maybe|perhaps|"
    r"especially|honestly|really)\b", _F)

# Words removed from a rejected clause to leave its content.
_STANCE = re.compile(
    r"\b(?:i'm|i am|i'd rather|i'd|i would|i will|i really|im|i|really|at all|ever|whatsoever|for me|my thing|"
    r"don'?t|do not|doesn'?t|does not|didn'?t|did not|won'?t|will not|wouldn'?t|would not|can'?t stand|"
    r"cannot stand|never|not|no longer|hate|hated|dislike|detest|despise|loathe|avoid|rather not|"
    r"want to|want|wanna|like to|like|love to|love|enjoy|interested in|into|care about|see myself|be|being|"
    r"is|are|isn'?t|aren'?t|no way|anything but|nothing to do with|a job where|a job that|jobs? where|"
    r"jobs? that|please|that involves?|involving|no me gusta|no me gustan|no quiero|no soporto|odio|nunca|"
    r"nada de|no|el|la|los|las)\b", _F)


@dataclass
class NegationSplit:
    positive: str                      # text describing what the user wants ("" if nothing positive)
    rejected: list[str] = field(default_factory=list)   # content of each rejected clause
    cues: list[str] = field(default_factory=list)       # matched negation cues (for evaluation, never the text)

    @property
    def has_negation(self) -> bool:
        return bool(self.rejected)

    @property
    def needs_followup(self) -> bool:
        """True when the statement only says what the user does NOT want."""
        return self.has_negation and not self.positive.strip()


def _content(clause: str) -> str:
    c = _STANCE.sub(" ", clause)
    c = re.sub(r"\b(?:to|with|in|of|about|or|and|y|o|a|an|the)\s*$", " ", c.strip(), flags=_F)
    c = re.sub(r"^\s*(?:to|with|in|of|about|or|and|y|o|que|de)\b", " ", c, flags=_F)
    return re.sub(r"\s+", " ", c).strip(" ,.;:-")


def _is_negated(clause: str) -> tuple[bool, str | None]:
    masked = _NOT_NEGATION.sub(" ", clause)
    m = _NEG_CUE.search(masked)
    if not m:
        return False, None
    # "no" as a bare Spanish/English word only counts as a cue before a noun phrase or verb, not "no, I ..."
    if m.group(0).lower() == "no" and re.match(r"\s*[,.!]", masked[m.end():]):
        return False, None
    return True, m.group(0).lower()


def split_negation(text: str) -> NegationSplit:
    """Split text into positive content and rejected content. Text without negation is returned unchanged."""
    # 1. "rather/prefer X than Y" and "X rather than / instead of Y": Y is rejected, X stays.
    pre_rejected, cues = [], []
    work = text
    m = _RATHER_THAN.search(work)
    if m and not _REJECT_AFTER.search(work):
        pre_rejected.append(m.group("neg"))
        cues.append("rather...than")
        work = work[: m.start("neg") - len("than")].rstrip()
        work = re.sub(r"\bthan\s*$", "", work, flags=_F)
    for m in list(_REJECT_AFTER.finditer(work))[::-1]:
        tail = work[m.end():]
        end = re.search(r"[.;!?]", tail)
        neg = tail[: end.start()] if end else tail
        pre_rejected.append(neg)
        cues.append(m.group(0).lower())
        work = work[: m.start()] + (tail[end.start():] if end else "")

    # 2. clause-level negation
    clauses = [c for c in _SPLIT.split(work) if c and c.strip()]
    pos, rej = [], []
    prev_neg = False
    for c in clauses:
        neg, cue = _is_negated(c)
        if not neg and prev_neg and not _NEW_CLAUSE.match(c.strip()):
            neg, cue = True, "inherited"      # "I don't like math, physics or chemistry"
        if neg:
            content = _content(c)
            if content:
                rej.append(content)
            cues.append(cue)
        else:
            pos.append(c.strip())
        prev_neg = neg
    rej = [_content(r) or r.strip() for r in pre_rejected] + rej
    rej = [r for r in rej if r]
    if not rej:
        return NegationSplit(positive=text)
    positive = ". ".join(p for p in pos if p)
    return NegationSplit(positive=positive, rejected=rej, cues=cues)


def adjusted_scores(sim_positive, sim_rejected, alpha: float):
    """Occupation scores for one statement: sim(positive) - alpha * max over rejected clauses of sim(rejected).

    sim_positive: array (n_occ,) or None when nothing positive is left (then only the penalty ranks; callers should
    ask a follow-up question instead of showing those results). sim_rejected: list of arrays (n_occ,).
    """
    import numpy as np

    if not sim_rejected:
        return np.asarray(sim_positive, float)
    pen = np.max(np.vstack(sim_rejected), axis=0)
    base = np.zeros_like(pen) if sim_positive is None else np.asarray(sim_positive, float)
    return base - alpha * pen
