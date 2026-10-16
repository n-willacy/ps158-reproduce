"""Standard errors for SCF statistics, following the MEANIT macro in the SCF
codebook (https://www.federalreserve.gov/econres/files/codebk2025.txt).

    SE = sqrt((6/5) * imputation variance + sampling variance)

- Point estimate: computed on all five implicates pooled with WGT, which is
  how the Fed's published tables are computed.
- Imputation variance: variance (n-1) of the estimate across the five
  implicates, each computed separately with WGT.
- Sampling variance: variance (n-1) of the estimate across the 999 bootstrap
  replicate weights, computed on the first implicate only. Replicate weights
  are WT1Bi * MMi (weight times multiplicity), with missing values set to 0.

A statistic is any function `stat(df, w) -> dict[str, array]` where `w` is an
(n, k) weight matrix and each returned array has length k. Writing statistics
this way lets one call evaluate all 999 replicates at once.
"""

import numpy as np
import pandas as pd

N_REPLICATES = 999


def weighted_median(x, w):
    """Weighted median of x for each column of w (n,) or (n, k).

    Takes the first value where the cumulative weight share reaches 1/2,
    as MEANIT does.
    """
    x = np.asarray(x)
    w = np.asarray(w, dtype=float)
    squeeze = w.ndim == 1
    if squeeze:
        w = w[:, None]
    order = np.argsort(x, kind="stable")
    cum = np.cumsum(w[order], axis=0)
    med = x[order][np.argmax(cum >= cum[-1] / 2, axis=0)]
    return med[0] if squeeze else med


def weighted_mean(x, w):
    """Weighted mean of x for each column of w (n, k)."""
    w = np.asarray(w, dtype=float)
    return (np.asarray(x)[:, None] * w).sum(0) / w.sum(0)


def replicate_weights(rw):
    """Replicate-weight matrix indexed by case id (the implicate-1 Y1/X1).

    `rw` is the replicate weight file with lower-case column names.
    """
    id_col = "y1" if "y1" in rw.columns else "x1"
    wt = rw[[f"wt1b{i}" for i in range(1, N_REPLICATES + 1)]].fillna(0).clip(lower=0).to_numpy()
    mm = rw[[f"mm{i}" for i in range(1, N_REPLICATES + 1)]].fillna(0).clip(lower=0).to_numpy()
    return pd.DataFrame(wt * mm, index=rw[id_col].astype("int64").to_numpy())


def estimate_with_se(df, stat, rep_weights):
    """Point estimates and standard errors for every output of `stat`.

    `df` holds all implicates with columns `wgt`, `implicate` (1-5) and
    `case_id` (Y1/X1), plus whatever `stat` uses.
    Returns {name: (estimate, se)}.
    """
    def run(d, w):
        return {k: np.atleast_1d(v) for k, v in stat(d, w).items()}

    pooled = run(df, df.wgt.to_numpy()[:, None])

    by_implicate = [run(g, g.wgt.to_numpy()[:, None]) for _, g in df.groupby("implicate")]
    if len(by_implicate) != 5:
        raise ValueError(f"expected 5 implicates, found {len(by_implicate)}")

    first = df[df.implicate == 1]
    replicates = run(first, rep_weights.loc[first.case_id].to_numpy())

    out = {}
    for name, value in pooled.items():
        imp_var = np.var([r[name][0] for r in by_implicate], ddof=1)
        samp_var = np.var(replicates[name], ddof=1)
        out[name] = (value[0], np.sqrt(6 / 5 * imp_var + samp_var))
    return out
