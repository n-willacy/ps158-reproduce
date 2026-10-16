"""Download the Survey of Consumer Finances summary extracts and compute median
net worth by education of the family's reference person, 1989-2025.

Source: Federal Reserve Board, SCF summary extract public data
(https://www.federalreserve.gov/econres/scfindex.htm). As of the 2025 release,
every year's extract is inflation-adjusted to 2025 dollars.

Groups (EDCL, harmonized across the 2016 change to the education question):
    college         EDCL == 4   bachelor's degree or higher
    hs_or_less      EDCL <= 2   no diploma, or high school diploma / GED
"Some college" (EDCL == 3) is excluded.

Each household appears five times (multiple imputation); WGT already divides
the weight across implicates, so statistics pool all rows. This reproduces the
medians in the Fed's historical Table 4.

Writes data/networth_by_education.csv.
"""

import io
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

YEARS = [1989, 1992, 1995, 1998, 2001, 2004, 2007, 2010, 2013, 2016, 2019, 2022, 2025]
URL = "https://www.federalreserve.gov/econres/files/scfp{year}s.zip"
RAW_DIR = Path("data/raw")
OUT = Path("data/networth_by_education.csv")

GROUPS = {
    "college": lambda edcl: edcl == 4,
    "hs_or_less": lambda edcl: edcl <= 2,
}


def download(year):
    path = RAW_DIR / f"scfp{year}s.zip"
    if not path.exists():
        print(f"downloading {path.name}")
        req = urllib.request.Request(URL.format(year=year), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as resp:
            path.write_bytes(resp.read())
    return path


def read_extract(path):
    with zipfile.ZipFile(path) as zf:
        (name,) = [n for n in zf.namelist() if n.lower().endswith(".dta")]
        df = pd.read_stata(io.BytesIO(zf.read(name)), convert_categoricals=False)
    df.columns = df.columns.str.lower()
    return df[["wgt", "edcl", "networth"]]


def weighted_median(x, w):
    order = np.argsort(x)
    x, w = x[order], w[order]
    cum = np.cumsum(w)
    return x[np.searchsorted(cum, cum[-1] / 2)]


def summarize(df, year):
    rows = []
    for group, select in GROUPS.items():
        g = df[select(df.edcl)]
        rows.append({
            "year": year,
            "group": group,
            "median_networth": weighted_median(g.networth.to_numpy(), g.wgt.to_numpy()),
            "mean_networth": np.average(g.networth, weights=g.wgt),
            "share_of_families": g.wgt.sum() / df.wgt.sum(),
        })
    return rows


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for year in YEARS:
        rows += summarize(read_extract(download(year)), year)
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False, float_format="%.4f")
    print(f"wrote {OUT}")
    print(out.pivot(index="year", columns="group", values="median_networth").round(-2))


if __name__ == "__main__":
    main()
