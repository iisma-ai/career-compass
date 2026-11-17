"""v1 questionnaire engine: fixed form -> GRM-EAP profile -> lost-user gate -> unordered career families.

Implements research/MODELS.md L1-L4 for one person at a time (plus a vectorised scorer for validation).

Gender-blind by construction (ADR 0015): no function here takes, infers or stores gender, age or any other
demographic input. Identical answers always give identical results. Nothing is written to disk or logged; answers live
only in memory for the call (ADR 0014).

**Research-only parameters.** The GRM item parameters, the item order and the latent correlations come from E4's
calibration on OpenPsychometrics data, which has no licence (ADR 0002). Every result carries ``research_only=True``
until release blocker 2 is cleared (permission, or our own calibration from study S1).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm

from .matching import SCALES, load_occupations, score_matrix

ROOT = Path(__file__).resolve().parents[2]
E4_JSON = ROOT / "research" / "findings" / "e4_cat_simulation.json"
FAMILIES_CSV = ROOT / "research" / "findings" / "e3_families.csv"

GRID = np.linspace(-5, 5, 81)
LOGPRIOR0 = norm.logpdf(GRID)
# E2: weak items (R1, A7, S4) and gender-DIF items (E4, R3, I8, R4, E1); excluded from the v1 form (MODELS L1).
EXCLUDED_ITEMS = ("R1", "A7", "S4", "E4", "R3", "I8", "R4", "E1")
# MODELS L3 gate thresholds (E1, E4, E5).
GATE_DIFFERENTIATION = 1.0
GATE_ELEVATION = 2.0
SOFT_DIFFERENTIATION = 1.5
MIN_ANSWERS_PER_SCALE = 2

NOTICES = (
    "careers_worth_exploring",  # framing, never "your perfect career"
    "not_ability_or_satisfaction",  # MODELS L6.3
    "us_occupational_data_onet",  # MODELS L6.4 + O*NET CC BY 4.0 attribution
    "human_help_links",  # MODELS L3, required on every result page
)


# ------------------------------------------------------------------------------------------------ item bank
@dataclass(frozen=True)
class ItemBank:
    items: tuple[str, ...]
    scale: np.ndarray  # (J,) scale index 0..5
    a: np.ndarray  # (J,) discrimination
    b: np.ndarray  # (J, 4) ordered thresholds
    phi: np.ndarray  # (6, 6) latent correlation
    source: str
    research_only: bool

    @classmethod
    def from_e4(cls, path: Path | str | None = None) -> ItemBank:
        """Load E4's EM-polished GRM calibration (research-only, ADR 0002)."""
        d = json.loads(Path(path or E4_JSON).read_text(encoding="utf-8"))["calibration"]
        items = tuple(d["items"])
        return cls(
            items=items,
            scale=np.array([SCALES.index(it[0]) for it in items]),
            a=np.array([d["items"][it]["a"] for it in items], float),
            b=np.array([d["items"][it]["b"] for it in items], float),
            phi=np.array(d["latent_corr"], float),
            source="E4 GRM calibration on OpenPsychometrics RIASEC (research-only, ADR 0002)",
            research_only=True,
        )

    def __post_init__(self):
        if not np.all(np.diff(self.b, axis=1) > 0):
            raise ValueError("GRM thresholds must be strictly increasing")
        if self.phi.shape != (6, 6):
            raise ValueError("phi must be 6x6")

    @cached_property
    def log_probs(self) -> np.ndarray:
        """(J, Q, 5) log category probabilities on GRID."""
        cum = expit(self.a[:, None, None] * (GRID[None, :, None] - self.b[:, None, :]))
        ones, zeros = np.ones_like(cum[:, :, :1]), np.zeros_like(cum[:, :, :1])
        p = np.concatenate([ones, cum], 2) - np.concatenate([cum, zeros], 2)
        return np.log(np.clip(p, 1e-12, 1))

    @cached_property
    def expected_score(self) -> np.ndarray:
        """(J, Q) expected answer on the 1-5 scale."""
        return (np.exp(self.log_probs) * np.arange(1, 6)).sum(2)

    def index(self, item: str) -> int:
        return self.items.index(item)


def build_fixed_form(bank: ItemBank, per_scale: int = 4, exclude: Sequence[str] = EXCLUDED_ITEMS) -> list[str]:
    """Content-balanced fixed form (ADR 0005): per scale, the `per_scale` most discriminating retained items,
    administered round-robin R-I-A-S-E-C in descending discrimination."""
    ranked = []
    for s in range(6):
        cand = [j for j, it in enumerate(bank.items) if bank.scale[j] == s and it not in exclude]
        if len(cand) < per_scale:
            raise ValueError(f"scale {SCALES[s]} has only {len(cand)} retained items")
        ranked.append(sorted(cand, key=lambda j: -bank.a[j])[:per_scale])
    return [bank.items[ranked[s][r]] for r in range(per_scale) for s in range(6)]


# ------------------------------------------------------------------------------------------------ scoring
@dataclass(frozen=True)
class Profile:
    theta: np.ndarray  # (6,) EAP under the correlated prior (internal; never shown)
    se: np.ndarray  # (6,) posterior SD (internal)
    raw: np.ndarray  # (6,) predicted full-scale mean, 1-5 (used for matching)
    n_answered: int

    @property
    def elevation(self) -> float:
        return float(self.raw.mean())

    @property
    def differentiation(self) -> float:
        return float(self.raw.max() - self.raw.min())

    def top_types(self, k: int = 2) -> list[str]:
        order = np.argsort(-self.raw, kind="stable")
        return [SCALES[i] for i in order[:k]]


def _eap_indep(loglik):
    lp = loglik + LOGPRIOR0
    lp = lp - lp.max(-1, keepdims=True)
    post = np.exp(lp)
    post /= post.sum(-1, keepdims=True)
    mu = post @ GRID
    return mu, np.clip(post @ GRID**2 - mu**2, 1e-8, None)


def _eap_corr(loglik, mu0, v0, phi_inv):
    """Correlated-prior EAP with Gaussian sites and exact 1-D cavity posteriors (same maths as E4 eap_corr)."""
    tau = np.clip(1.0 / v0 - 1.0, 0, None)
    h = np.where(tau > 0, mu0 / v0, 0.0)
    C = np.linalg.inv(phi_inv[None] + tau[:, :, None] * np.eye(6)[None])
    m = np.einsum("nij,nj->ni", C, h)
    css = np.einsum("nii->ni", C)
    w = css / (1 - tau * css)
    c = w * (m / css - h)
    lp = loglik - 0.5 * (GRID[None, None, :] - c[:, :, None]) ** 2 / w[:, :, None]
    lp = lp - lp.max(-1, keepdims=True)
    post = np.exp(lp)
    post /= post.sum(-1, keepdims=True)
    mu = post @ GRID
    return post, mu, np.clip(post @ GRID**2 - mu**2, 1e-8, None)


def score_matrix_responses(resp: np.ndarray, bank: ItemBank) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Vectorised scoring. resp: (n, J) answers 1..5 in bank order, 0 = not administered.
    Returns theta (n,6), se (n,6), raw predicted full-scale means (n,6)."""
    resp = np.asarray(resp, int)
    n = resp.shape[0]
    loglik = np.zeros((n, 6, GRID.size))
    for j in range(len(bank.items)):
        m = resp[:, j] > 0
        if m.any():
            loglik[m, bank.scale[j], :] += bank.log_probs[j][:, resp[m, j] - 1].T
    mu0, v0 = _eap_indep(loglik)
    post, mu, var = _eap_corr(loglik, mu0, v0, np.linalg.inv(bank.phi))
    exp_item = np.einsum("nsq,jq->nsj", post, bank.expected_score)  # (n, 6, J)
    raw = np.zeros((n, 6))
    for s in range(6):
        cols = np.flatnonzero(bank.scale == s)
        e = exp_item[:, s, cols]
        obs = resp[:, cols]
        raw[:, s] = np.where(obs > 0, obs, e).mean(1)
    return mu, np.sqrt(var), raw


def score(responses: Mapping[str, int], bank: ItemBank) -> Profile:
    """Score one person's answers {item_id: 1..5}."""
    row = np.zeros((1, len(bank.items)), int)
    for it, x in responses.items():
        if it not in bank.items:
            raise KeyError(f"unknown item {it!r}")
        if isinstance(x, bool) or not isinstance(x, (int, np.integer)) or not 1 <= x <= 5:
            raise ValueError(f"answer to {it} must be an integer 1-5, got {x!r}")
        row[0, bank.index(it)] = int(x)
    theta, se, raw = score_matrix_responses(row, bank)
    return Profile(theta=theta[0], se=se[0], raw=raw[0], n_answered=len(responses))


# ------------------------------------------------------------------------------------------------ gate
def gate(profile: Profile) -> str:
    """MODELS L3: 'lost' (hard gate), 'mixed' (soft gate: broad families + wording) or 'clear'.
    Never triggered on posterior SE (E5). 'lost' is an internal name only."""
    if profile.differentiation < GATE_DIFFERENTIATION or profile.elevation < GATE_ELEVATION:
        return "lost"
    if profile.differentiation < SOFT_DIFFERENTIATION:
        return "mixed"
    return "clear"


# ------------------------------------------------------------------------------------------------ catalogue
@dataclass(frozen=True)
class Catalogue:
    occ: pd.DataFrame  # code, title, R..C (OI 1-7), job_zone; index 0..n-1
    family: np.ndarray  # (n,) family id 0..F-1 (r >= .80 complete linkage, E3/E5)
    label: dict[int, str]  # placeholder labels until milestone 1.4 (hand-written, counsellor-reviewed)

    @classmethod
    def load(cls) -> Catalogue:
        occ = load_occupations()
        fams = pd.read_csv(FAMILIES_CSV, dtype={"code": str}).set_index("code").loc[occ.code, "family_r80"].to_numpy()
        prof = occ[SCALES].to_numpy()
        label = {}
        for f in np.unique(fams):
            idx = np.flatnonzero(fams == f)
            centre = prof[idx].mean(0)
            # placeholder = title of the member closest (Pearson) to the family centre
            r = [np.corrcoef(prof[i], centre)[0, 1] if prof[i].std() > 0 else -1 for i in idx]
            label[int(f)] = str(occ.title.iloc[idx[int(np.argmax(r))]])
        return cls(occ=occ, family=fams, label=label)

    def family_profile(self, f: int) -> np.ndarray:
        return self.occ.loc[self.family == f, SCALES].to_numpy().mean(0)


@dataclass(frozen=True)
class Family:
    family_id: int
    label: str
    label_is_placeholder: bool
    examples: list[dict]  # code, title, job_zone; ordered by preparation, then title (MODELS L4)
    family_types: list[str]  # family's two strongest RIASEC types
    shared_types: list[str]  # overlap with the person's two strongest types (for the explanation, L6)
    job_zones: tuple[int, int]


def recommend(profile: Profile, cat: Catalogue, n_families: int = 3, n_examples: int = 3,
              job_zones: Sequence[int] | None = None) -> list[Family]:
    """Top families by their best member's Pearson score (E5), returned UNORDERED (sorted by id, ADR 0006).
    `job_zones` is the user's optional preparation filter; default = all (MODELS L4)."""
    mask = np.ones(len(cat.occ), bool) if job_zones is None else cat.occ.job_zone.isin(list(job_zones)).to_numpy()
    if not mask.any():
        return []
    s = score_matrix(profile.raw[None, :], cat.occ)[0]
    s = np.where(mask, s, -np.inf)
    fam_best = {}
    for i in np.argsort(-(s - np.arange(len(s)) * 1e-12), kind="stable"):  # ties by catalogue order
        if not np.isfinite(s[i]):
            break
        fam_best.setdefault(int(cat.family[i]), []).append(int(i))
    chosen = list(fam_best)[:n_families]
    mine = profile.top_types(2)
    out = []
    for f in sorted(chosen):
        members = fam_best[f][:n_examples]
        ex = cat.occ.iloc[members][["code", "title", "job_zone"]]
        ex = ex.sort_values(["job_zone", "title"], kind="stable")
        fp = cat.family_profile(f)
        ftypes = [SCALES[i] for i in np.argsort(-fp, kind="stable")[:2]]
        jz = cat.occ.loc[cat.family == f, "job_zone"]
        out.append(Family(
            family_id=f, label=cat.label[f], label_is_placeholder=True,
            examples=[{"code": c, "title": t, "job_zone": int(z)} for c, t, z in ex.itertuples(index=False)],
            family_types=ftypes, shared_types=[t for t in mine if t in ftypes],
            job_zones=(int(jz.min()), int(jz.max())),
        ))
    return out


# ------------------------------------------------------------------------------------------------ pipeline
def refine_form(bank: ItemBank) -> list[str]:
    """Optional refine step (MODELS L1): the v1 form plus each scale's 5th item (30 items). Its first 24 items are
    the v1 form, so the refine page only asks the 6 new items."""
    return build_fixed_form(bank, per_scale=5)


ANGLES = np.deg2rad(np.arange(6) * 60.0)  # R=0, I=60, A=120, S=180, E=240, C=300 (E2)


def prediger(profile: Profile) -> tuple[float, float]:
    """Angle projection of the shape onto the hexagon plane (MODELS L6, E2): (things_minus_people, ideas_minus_data).
    For explanation wording only; never shown as a number."""
    c = profile.raw - profile.raw.mean()
    return float(c @ np.cos(ANGLES)), float(c @ np.sin(ANGLES))


@dataclass(frozen=True)
class Result:
    status: str  # "clear" | "mixed" | "lost"
    families: list[Family]
    top_types: list[str]
    notices: tuple[str, ...]
    research_only: bool
    profile: Profile | None = field(default=None, repr=False)  # internal; never rendered as scores (ADR 0006)
    prediger_xy: tuple[float, float] | None = None  # internal, for explanation wording (L6)


def assess(responses: Mapping[str, int], bank: ItemBank, cat: Catalogue,
           job_zones: Sequence[int] | None = None, form: Sequence[str] | None = None) -> Result:
    """Full v1 flow for one person. Requires every item of the form to be answered, with at least
    MIN_ANSWERS_PER_SCALE answers per scale. 'lost' returns no families: the lost-user flow (design only, MODELS L3)
    takes over."""
    form = list(form) if form is not None else build_fixed_form(bank)
    missing = [it for it in form if it not in responses]
    if missing:
        raise ValueError(f"unanswered form items: {missing}")
    for s, letter in enumerate(SCALES):
        if sum(1 for it in responses if bank.scale[bank.index(it)] == s) < MIN_ANSWERS_PER_SCALE:
            raise ValueError(f"need at least {MIN_ANSWERS_PER_SCALE} answers on scale {letter}")
    prof = score(responses, bank)
    status = gate(prof)
    fams = [] if status == "lost" else recommend(prof, cat, job_zones=job_zones)
    notices = list(NOTICES)
    if status == "mixed":
        notices.append("mixed_profile")  # L3 soft gate: "your answers point in several directions"
    if prof.elevation < GATE_ELEVATION:
        notices.append("low_interest_talk_to_someone")  # L3 non-diagnostic line; counsellor review pending
    if fams and not any(prof.top_types(1)[0] in f.family_types for f in fams):
        notices.append("top_type_thin_pool")  # L4: few occupations peak on this type; explain why
    return Result(status=status, families=fams, top_types=prof.top_types(2), notices=tuple(notices),
                  research_only=bank.research_only, profile=prof, prediger_xy=prediger(prof))
