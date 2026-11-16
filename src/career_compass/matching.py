"""Person <-> occupation RIASEC matching (shared by E3, E4, E5 and later the product).

Profiles are 6-vectors in R-I-A-S-E-C order. People are on the 1-5 Likert scale (mean of
8 items per scale); O*NET occupations are on the OI 1-7 scale. Because the scales differ,
every method below either removes the level/scale (shape methods) or z-scores each side
within its *own* population before comparing.

Methods (higher score = better match for all of them):

``pearson``
    Pearson correlation of the two 6-vectors (each centred on its own mean, i.e. ipsative).
    This is the O*NET-style baseline (My Next Move / Interest Profiler use a correlation of
    profiles; see the riasec-scoring skill, "verify"). Range -1..1. Note that cosine
    similarity of *self*-centred vectors is mathematically identical to Pearson, so it is not
    offered as a separate method.
``cosine_centered``
    "Normed shape". Each side is first centred on its own population mean profile (people on
    the mean person profile, occupations on the mean catalogue profile), then on its own mean
    (ipsatised), then compared by cosine. A person is matched on what is *distinctive about
    them relative to other people* to what is distinctive about an occupation relative to
    other occupations. This removes the population-level mismatch found in E1 (people lean
    S/I/A, the catalogue leans R/C). Range -1..1.
``euclid_z``
    Both sides z-scored per scale within their own population (people: person norms;
    occupations: catalogue mean/SD); score = minus the Euclidean distance between the two
    z-vectors. Keeps elevation (overall level), so a person who likes everything is pulled
    towards occupations rated high on everything. Range -inf..0.
``hexagon``
    Circular-distance-aware correlation. With a, b the self-centred profiles and K the 6x6
    circulant kernel K_ij = w(d_ij), where d_ij is the hexagon distance between types i and j
    (0 same, 1 adjacent, 2 alternate, 3 opposite) and w = HEX_WEIGHTS = (1, 0.4, 0, 0):

        score = a'Kb / sqrt(a'Ka * b'Kb)

    A mismatch between neighbouring types (e.g. the person peaks on I, the occupation on R)
    is penalised less than a mismatch between opposite types. In Fourier terms K weights the
    first circular harmonic (the Prediger Data/Ideas x People/Things plane) 1.4, the second
    0.6 and the third (alternating R/A/E vs I/S/C) 0.2, versus 1:1:1 for Pearson. Computed as
    the cosine of K^(1/2)-smoothed centred profiles. Range -1..1.

Degenerate input: a completely flat profile (all six scores equal) carries no shape
information. Shape methods then return 0 for every occupation; ranking falls back to
catalogue order and should not be shown to a user (use the "lost user" flow instead).

Ties: rankings are deterministic; exact ties are broken by catalogue row order.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

SCALES = list("RIASEC")
METHODS = ("pearson", "cosine_centered", "euclid_z", "hexagon")
HEX_WEIGHTS = (1.0, 0.4, 0.0, 0.0)  # weight by hexagon distance 0, 1, 2, 3

ROOT = Path(__file__).resolve().parents[2]
OCC_PATH = ROOT / "data" / "processed" / "onet_occupations.parquet"
PEOPLE_PATH = ROOT / "data" / "processed" / "riasec_people.parquet"


# ----------------------------------------------------------------------------- loading
def load_occupations(path: Path | str | None = None, extra: bool = False) -> pd.DataFrame:
    """Load the 923 rated O*NET 31.0 occupations.

    Returns a DataFrame with columns ``code, title, R, I, A, S, E, C, job_zone`` (OI 1-7), sorted
    by code with a 0..n-1 index. ``extra=True`` also keeps ``holland_code`` and
    ``oi_domain_source``.
    """
    df = pd.read_parquet(path or OCC_PATH).rename(columns={"onet_soc_code": "code"})
    cols = ["code", "title", *SCALES, "job_zone"]
    if extra:
        cols += ["holland_code", "oi_domain_source"]
    return df[cols].sort_values("code").reset_index(drop=True)


@lru_cache(maxsize=4)
def _person_norms_cached(path: str) -> tuple[tuple[float, ...], tuple[float, ...]]:
    p = pd.read_parquet(path, columns=SCALES)
    return tuple(p.mean().to_numpy()), tuple(p.std(ddof=1).to_numpy())


def person_norms(path: Path | str | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Mean and SD of the six raw (1-5) scale scores in the cleaned people table (cached).

    These are the population norms used by ``cosine_centered`` and ``euclid_z``. In the product
    they would be frozen constants.
    """
    m, s = _person_norms_cached(str(path or PEOPLE_PATH))
    return np.asarray(m), np.asarray(s)


# ----------------------------------------------------------------------------- helpers
def _as_2d(profiles) -> np.ndarray:
    a = np.asarray(profiles, dtype=float)
    if a.ndim == 1:
        a = a[None, :]
    if a.shape[1] != 6:
        raise ValueError("profiles must have 6 columns in R-I-A-S-E-C order")
    return a


def _occ_matrix(occ) -> np.ndarray:
    if isinstance(occ, pd.DataFrame):
        return occ[SCALES].to_numpy(dtype=float)
    return _as_2d(occ)


def _unit_rows(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return np.divide(x, n, out=np.zeros_like(x), where=n > 1e-12)


def _centre_rows(x: np.ndarray) -> np.ndarray:
    return x - x.mean(axis=1, keepdims=True)


def hexagon_kernel(weights=HEX_WEIGHTS) -> np.ndarray:
    """6x6 circulant kernel K_ij = weights[hexagon distance(i, j)]."""
    idx = np.arange(6)
    d = np.abs(idx[:, None] - idx[None, :])
    d = np.minimum(d, 6 - d)
    return np.asarray(weights, dtype=float)[d]


def _kernel_sqrt(weights=HEX_WEIGHTS) -> np.ndarray:
    vals, vecs = np.linalg.eigh(hexagon_kernel(weights))
    if vals.min() < -1e-10:
        raise ValueError("hexagon kernel must be positive semi-definite")
    return (vecs * np.sqrt(np.clip(vals, 0, None))) @ vecs.T


def _transform(p: np.ndarray, o: np.ndarray, method: str, pnorm, onorm):
    """Return (person_vectors, occupation_vectors, kind) with kind 'cos' or 'dist'."""
    if method == "pearson":
        return _unit_rows(_centre_rows(p)), _unit_rows(_centre_rows(o)), "cos"
    if method == "hexagon":
        L = _kernel_sqrt()
        return _unit_rows(_centre_rows(p) @ L), _unit_rows(_centre_rows(o) @ L), "cos"
    pm, ps = pnorm if pnorm is not None else person_norms()
    om, osd = onorm if onorm is not None else (o.mean(axis=0), o.std(axis=0, ddof=1))
    if method == "cosine_centered":
        return _unit_rows(_centre_rows(p - pm)), _unit_rows(_centre_rows(o - om)), "cos"
    if method == "euclid_z":
        return (p - pm) / ps, (o - om) / osd, "dist"
    raise ValueError(f"unknown method {method!r}; choose from {METHODS}")


# ----------------------------------------------------------------------------- scoring
def score_matrix(profiles, occ, method: str = "pearson", person_norm=None, occ_norm=None) -> np.ndarray:
    """Vectorised scores, shape (n_people, n_occupations), float64. Higher = better.

    ``profiles``: (n, 6) or (6,) raw person scale scores (1-5). ``occ``: occupation DataFrame
    (R..C columns) or (m, 6) array. ``person_norm`` / ``occ_norm``: optional (mean, sd) tuples
    overriding the population norms (defaults: cleaned people table / the passed catalogue).
    """
    p, o = _as_2d(profiles), _occ_matrix(occ)
    pv, ov, kind = _transform(p, o, method, person_norm, occ_norm)
    if kind == "cos":
        return pv @ ov.T
    d2 = (pv**2).sum(1)[:, None] + (ov**2).sum(1)[None, :] - 2 * pv @ ov.T
    return -np.sqrt(np.clip(d2, 0, None))


def top_k_indices(profiles, occ, k: int = 10, method: str = "pearson", chunk: int = 10000,
                  return_scores: bool = False, **norms):
    """Row indices (into ``occ``) of the k best occupations per person, best first.

    Works in chunks so 80k people x 923 occupations fits in memory. Exact ties are broken by
    catalogue row order (lower index first). Returns (n, k) int array, plus (n, k) scores if
    ``return_scores``.
    """
    p = _as_2d(profiles)
    m = len(occ)
    tieb = np.arange(m) * 1e-12
    out_i = np.empty((len(p), k), dtype=np.int32)
    out_s = np.empty((len(p), k)) if return_scores else None
    for a in range(0, len(p), chunk):
        s = score_matrix(p[a:a + chunk], occ, method, **norms)
        s_t = s - tieb
        part = np.argpartition(-s_t, k - 1, axis=1)[:, :k]
        order = np.argsort(-np.take_along_axis(s_t, part, 1), axis=1, kind="stable")
        idx = np.take_along_axis(part, order, 1)
        out_i[a:a + chunk] = idx
        if return_scores:
            out_s[a:a + chunk] = np.take_along_axis(s, idx, 1)
    return (out_i, out_s) if return_scores else out_i


def score_occupations(profile6, occ: pd.DataFrame, method: str = "pearson", **norms) -> pd.DataFrame:
    """Score one person against every occupation; returns ``occ`` plus a ``score`` column, best first."""
    s = score_matrix(profile6, occ, method, **norms)[0]
    out = occ.assign(score=s)
    order = np.lexsort((np.arange(len(out)), -s))  # score desc, ties by row order
    return out.iloc[order]


def top_k(profile6, occ: pd.DataFrame, k: int = 10, method: str = "pearson", **norms) -> pd.DataFrame:
    """The k best occupations for one person (see ``score_occupations``)."""
    return score_occupations(profile6, occ, method, **norms).head(k)


def top_k_overlap(a, b) -> float:
    """Share of list ``a`` that also appears in list ``b`` (|a & b| / |a|), order ignored.

    Accepts lists of codes/indices, or DataFrames with a ``code`` column.
    """
    if isinstance(a, pd.DataFrame):
        a = a["code"].tolist()
    if isinstance(b, pd.DataFrame):
        b = b["code"].tolist()
    a = list(a)
    return len(set(a) & set(b)) / len(a) if a else float("nan")


def top_k_overlap_rows(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Row-wise ``top_k_overlap`` for two (n, k) integer index arrays (vectorised)."""
    A, B = np.asarray(A), np.asarray(B)
    hits = (A[:, :, None] == B[:, None, :]).any(axis=2)
    return hits.mean(axis=1)


# ----------------------------------------------------------------------------- families
def occupation_families(occ, r_min: float = 0.90) -> np.ndarray:
    """Group occupations into profile families (integer label per row, 0..F-1).

    Complete-linkage hierarchical clustering on the distance 1 - Pearson r between occupation
    profiles, cut at 1 - r_min. Complete linkage guarantees that *every* pair inside a family
    has profile r >= r_min. The partition is deterministic. It is an upper bound on the minimum
    number of such groups, because exact minimum clique cover is NP-hard. Labels are numbered
    by first appearance in catalogue order.
    """
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    o = _unit_rows(_centre_rows(_occ_matrix(occ)))
    d = np.clip(1.0 - o @ o.T, 0, 2)
    np.fill_diagonal(d, 0)
    lab = fcluster(linkage(squareform(d, checks=False), "complete"), 1.0 - r_min, "distance")
    _, first = np.unique(lab, return_index=True)
    remap = {lab[i]: j for j, i in enumerate(np.sort(first))}
    return np.array([remap[x] for x in lab], dtype=np.int32)


# ----------------------------------------------------------------------------- self-check
if __name__ == "__main__":
    import time

    occ = load_occupations()
    print(f"{len(occ)} occupations loaded")
    pure = {s: np.where(np.array(SCALES) == s, 5.0, 1.0) for s in SCALES}
    for method in METHODS:
        top = top_k(pure["A"], occ, k=5, method=method)
        print(f"\n[{method}] pure-A top 5:")
        for _, r in top.iterrows():
            print(f"  {r.code}  {r.title[:55]:55s} score={r.score:.3f}  A={r.A:.1f}")
        # A pure-A profile should mostly return SOC major group 27 (Arts, Design, Media).
        # euclid_z is exempt on purpose: it keeps elevation, and an extreme 5/1 profile is far outside
        # both populations, so it lands on mixed R/A craft jobs (documented weakness, see E3).
        n_arts = int(top.code.str.startswith("27-").sum())
        if method != "euclid_z":
            assert n_arts >= 4, f"{method}: pure-A top-5 not mostly arts"
        if method in ("pearson", "hexagon"):  # shape methods: top letter must match exactly
            for s in SCALES:
                t = top_k_indices(pure[s], occ, 3, method)[0]
                assert (occ.loc[t, SCALES].to_numpy().argmax(1) == SCALES.index(s)).all(), (method, s)
    # Pearson equals its definition
    x = np.array([2.0, 3.5, 4.0, 3.0, 1.5, 2.5])
    r = np.array([np.corrcoef(x, row)[0, 1] for row in occ[SCALES].to_numpy()])
    assert np.allclose(score_matrix(x, occ, "pearson")[0], r)
    # flat profile -> all zeros for shape methods
    assert np.allclose(score_matrix(np.full(6, 3.0), occ, "pearson"), 0)
    assert top_k_overlap([1, 2, 3], [3, 2, 9]) == 2 / 3
    # speed: 80k x 923
    rng = np.random.default_rng(0)
    P = rng.uniform(1, 5, size=(80_000, 6))
    for method in METHODS:
        t0 = time.time()
        top_k_indices(P, occ, 10, method)
        print(f"top-10 for 80k random people, {method}: {time.time() - t0:.1f}s")
    print("\nself-check OK")
