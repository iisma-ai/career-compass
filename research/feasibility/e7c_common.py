"""Shared E7c pipeline: cue stripping (text_cues v2) -> negation split -> embedding -> adjusted scores.

Used by e7c_dev_tuning.py (development, E7 statements only) and e7c_names_negation.py (pre-registered run).
Configuration fixed from E7: all-MiniLM-L6-v2, index variant (d), cosine, top-10.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "feasibility"))  # python -I drops the script dir
sys.path.insert(0, str(ROOT / "src"))
import e7_free_text_matching as E

from career_compass.negation import adjusted_scores, split_negation
from career_compass.text_cues import strip_demographic_cues


def prepare(texts, strip=True, negation=True):
    """Per text: dict(stripped, positive, rejected, followup, cue_types, neg_cues)."""
    out = []
    for x in texts:
        s, cues = strip_demographic_cues(x) if strip else (x, [])
        if negation:
            ns = split_negation(s)
            pos, rej, neg_cues = ns.positive, ns.rejected, ns.cues
        else:
            pos, rej, neg_cues = s, [], []
        out.append({"stripped": s, "positive": pos, "rejected": rej, "followup": bool(rej) and not pos.strip(),
                    "cue_types": [t for t, _ in cues], "neg_cues": neg_cues})
    return out


class Scorer:
    """Embeds every distinct query text once, then builds adjusted score matrices for any alpha."""

    def __init__(self, prepared_blocks: dict, model="minilm", log=None):
        self.occ, tasks, text_a, text_d = E.load_catalogue()
        texts = sorted({t for blk in prepared_blocks.values() for p in blk
                        for t in [p["positive"], p["stripped"], *p["rejected"]] if t and t.strip()})
        self.idx = {t: i for i, t in enumerate(texts)}
        log = {} if log is None else log
        S, _, _ = E.embed_scores(model, E.MODELS[model], self.occ, tasks, text_a, text_d, texts, log)
        self.Sd = S["d"]
        self.log = log

    def sim(self, text):
        return self.Sd[self.idx[text]]

    def matrix(self, prepared, alpha):
        """Returns (scores (n, n_occ), top1 similarity of the positive part (for rejection), followup flags)."""
        rows, top1, fu = [], [], []
        for p in prepared:
            if p["rejected"]:
                pos = self.sim(p["positive"]) if p["positive"].strip() else None
                rows.append(adjusted_scores(pos, [self.sim(r) for r in p["rejected"]], alpha))
                top1.append(float(pos.max()) if pos is not None else np.nan)
            else:
                s = self.sim(p["stripped"])
                rows.append(s)
                top1.append(float(s.max()))
            fu.append(p["followup"])
        return np.vstack(rows), np.array(top1), np.array(fu)
