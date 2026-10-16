"""Download the Survey of Consumer Finances summary extracts and replicate
weights, and compute median net worth by education of the family's reference
person, with standard errors, 1989-2025.

Source: Federal Reserve Board, SCF summary extract public data and replicate
weight files (https://www.federalreserve.gov/econres/scfindex.htm). As of the
2025 release, every year's extract is inflation-adjusted to 2025 dollars.

Groups (EDCL, harmonized across the 2016 change to the education question):
    college         EDCL == 4   bachelor's degree or higher
    hs_or_less      EDCL <= 2   no diploma, or high school diploma / GED
"Some college" (EDCL == 3) is excluded.

Each household appears five times (multiple imputation); point estimates pool
all rows with WGT, which reproduces the medians in the Fed's historical Table 4.
Standard errors combine imputation and sampling variance (see scf_se.py).

Downloads ~450 MB into data/raw/ on first run. Writes:
    data/networth_by_education.csv   median/mean (+ SE) and share, by year and group
    data/networth_ratio.csv          college / hs_or_less median ratio (+ SE), by year
"""

import io
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

from scf_se import estimate_with_se, replicate_weights, weighted_mean, weighted_median

YEARS = [1989, 1992, 1995, 1998, 2001, 2004, 2007, 2010, 2013, 2016, 2019, 2022, 2025]
BASE_URL = "https://www.federalreserve.gov/econres/files/"
RAW_DIR = Path("data/raw")
OUT_GROUPS = Path("data/networth_by_education.csv")
OUT_RATIO = Path("data/networth_ratio.csv")

GROUPS = {
    "college": lambda edcl: edcl == 4,
    "hs_or_less": lambda edcl: edcl <= 2,
}


def extract_name(year):
    return f"scfp{year}s.zip"


def replicate_name(year):
    # Surveys before 2001 use two-digit years in the replicate file name.
    return f"scf{year if year >= 2001 else str(year)[2:]}rw1s.zip"


def download(name):
    path = RAW_DIR / name
    if not path.exists():
        print(f"downloading {name}")
        req = urllib.request.Request(BASE_URL + name, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            path.write_bytes(resp.read())
    return path


def read_dta(path):
    with zipfile.ZipFile(path) as zf:
        (name,) = [n for n in zf.namelist() if n.lower().endswith(".dta")]
        df = pd.read_stata(io.BytesIO(zf.read(name)), convert_categoricals=False)
    df.columns = df.columns.str.lower()
    return df


def read_extract(path):
    df = read_dta(path)
    # Case ids are X1/XX1 in 1989 and Y1/YY1 afterwards. Cast before
    # multiplying: YY1 is stored as int16 and 10 * YY1 overflows.
    case, household = ("y1", "yy1") if "y1" in df.columns else ("x1", "xx1")
    df["case_id"] = df[case].astype("int64")
    df["implicate"] = df.case_id - 10 * df[household].astype("int64")
    return df[["case_id", "implicate", "wgt", "edcl", "networth"]]


def stat(df, w):
    """Median and mean net worth by group, and the ratio of medians."""
    out = {}
    for group, select in GROUPS.items():
        mask = select(df.edcl).to_numpy()
        x = df.networth.to_numpy()[mask]
        out[f"{group}_median"] = weighted_median(x, w[mask])
        out[f"{group}_mean"] = weighted_mean(x, w[mask])
    out["ratio"] = out["college_median"] / out["hs_or_less_median"]
    return out


def summarize(df, rep_weights, year):
    est = estimate_with_se(df, stat, rep_weights)
    groups = []
    for group, select in GROUPS.items():
        groups.append({
            "year": year,
            "group": group,
            "median_networth": est[f"{group}_median"][0],
            "median_se": est[f"{group}_median"][1],
            "mean_networth": est[f"{group}_mean"][0],
            "mean_se": est[f"{group}_mean"][1],
            "share_of_families": df.wgt[select(df.edcl)].sum() / df.wgt.sum(),
        })
    ratio = {"year": year, "ratio": est["ratio"][0], "ratio_se": est["ratio"][1]}
    return groups, ratio


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    groups, ratios = [], []
    for year in YEARS:
        df = read_extract(download(extract_name(year)))
        rep = replicate_weights(read_dta(download(replicate_name(year))))
        g, r = summarize(df, rep, year)
        groups += g
        ratios.append(r)
        print(f"{year}: ratio {r['ratio']:.2f} (SE {r['ratio_se']:.2f})")
    pd.DataFrame(groups).to_csv(OUT_GROUPS, index=False, float_format="%.4f")
    pd.DataFrame(ratios).to_csv(OUT_RATIO, index=False, float_format="%.4f")
    print(f"wrote {OUT_GROUPS} and {OUT_RATIO}")


if __name__ == "__main__":
    main()
