"""Create weighted district indicators for the EICV7 double-exclusion project.

Raw Stata files are read in place and never copied into the output folder.
Only district-level aggregate tables are written.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DISTRICTS = {
    11: "Nyarugenge", 12: "Gasabo", 13: "Kicukiro",
    21: "Nyanza", 22: "Gisagara", 23: "Nyaruguru", 24: "Huye",
    25: "Nyamagabe", 26: "Ruhango", 27: "Muhanga", 28: "Kamonyi",
    31: "Karongi", 32: "Rutsiro", 33: "Rubavu", 34: "Nyabihu",
    35: "Ngororero", 36: "Rusizi", 37: "Nyamasheke",
    41: "Rulindo", 42: "Gakenke", 43: "Musanze", 44: "Burera",
    45: "Gicumbi", 51: "Rwamagana", 52: "Nyagatare", 53: "Gatsibo",
    54: "Kayonza", 55: "Kirehe", 56: "Ngoma", 57: "Bugesera",
}

# NISR EICV7 Main Indicators Report district headcount poverty rates, percent.
PUBLISHED_POVERTY_RATES = {
    "Nyamagabe": 51.4, "Gisagara": 45.6, "Rusizi": 44.2, "Nyanza": 43.3,
    "Nyamasheke": 42.8, "Rutsiro": 40.8, "Nyaruguru": 39.7, "Kamonyi": 39.7,
    "Rubavu": 38.8, "Karongi": 38.2, "Kayonza": 36.6, "Nyagatare": 36.4,
    "Ngoma": 30.9, "Ngororero": 30.2, "Gakenke": 24.5, "Huye": 24.2,
    "Rwamagana": 23.8, "Bugesera": 23.7, "Burera": 22.0, "Rulindo": 21.6,
    "Musanze": 21.0, "Nyabihu": 20.2, "Gatsibo": 18.4, "Ruhango": 15.0,
    "Muhanga": 15.0, "Kirehe": 14.2, "Gicumbi": 13.3, "Gasabo": 11.1,
    "Kicukiro": 6.9, "Nyarugenge": 6.8,
}

VUP_MODULES = {
    "CS_S9D1_Direct_Support.dta": ("s9d1q1", "s9d1q2"),
    "CS_S9D2_Classic_Public_Work.dta": ("s9d1q1", "s9d2q1"),
    "CS_S9D3_Expanded_Public_Work.dta": ("s9d1q1", "s9d3q1"),
    "CS_S9D4_NSDS.dta": ("s9d1q1", "s9d4q1"),
    "CS_S9D5_Financial_Services.dta": ("s9d1q1", "s9d5q1"),
}


def read_stata(path: Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Read numeric Stata values without converting value labels to strings."""
    return pd.read_stata(path, columns=columns, convert_categoricals=False)


def household_vup_flags(data_dir: Path) -> pd.Series:
    """Union household VUP participation flags across the five VUP modules."""
    participants: set[int] = set()
    for filename, fields in VUP_MODULES.items():
        df = read_stata(data_dir / filename, ["hhid", *fields])
        yes = pd.Series(False, index=df.index)
        for field in fields:
            yes |= df[field].eq(1)
        participants.update(df.loc[yes, "hhid"].dropna().astype("int64").tolist())
    return pd.Series(1, index=pd.Index(sorted(participants), name="hhid"), name="vup_any")


def household_financial_flags(data_dir: Path) -> pd.DataFrame:
    """Collapse member/account records to household access indicators.

    `s10cq4` is the primary bank/mobile-money measure. `s10cq1` is retained as
    a broader sensitivity measure that also includes tontine ownership.
    """
    df = read_stata(
        data_dir / "CS_S10C_Savings.dta",
        ["hhid", "s10cq1", "s10cq4", "s10cq8"],
    )
    df["broad_financial_or_tontine_access"] = df["s10cq1"].eq(1).astype("int8")
    df["bank_or_mobile_account"] = df["s10cq4"].eq(1).astype("int8")
    df["tontine_participation"] = df["s10cq8"].eq(1).astype("int8")
    collapsed = df.groupby("hhid", as_index=True)[
        ["broad_financial_or_tontine_access", "bank_or_mobile_account", "tontine_participation"]
    ].max()
    collapsed.index = collapsed.index.astype("int64")
    return collapsed


def weighted_estimate(
    frame: pd.DataFrame,
    outcome: str,
    domain: pd.Series,
    weight_col: str = "weight",
) -> dict[str, float | int]:
    """Estimate a weighted domain mean and stratified-PSU linearized SE.

    `clust` is the PSU and `strata_id` is the survey stratum. The variance is
    calculated from PSU totals of the ratio linearized residual. A normal
    1.96 multiplier is used for the 95% interval.
    """
    d = frame.copy()
    d["_domain"] = domain.reindex(d.index).fillna(False).astype(bool)
    d = d.loc[d[outcome].notna() & d[weight_col].notna() & (d[weight_col] > 0)]
    n = int(d["_domain"].sum())
    d["_domain_weight"] = d[weight_col] * d["_domain"].astype(float)
    denominator = float(d["_domain_weight"].sum())
    if denominator <= 0 or n == 0:
        return {"estimate": np.nan, "se": np.nan, "ci_low": np.nan, "ci_high": np.nan, "n": n, "weighted_n": 0.0}

    estimate = float((d["_domain_weight"] * d[outcome]).sum() / denominator)
    # Keep all sampled households so PSUs with no domain members remain in
    # the design variance calculation as zero domain contributions.
    d["_linearized"] = d["_domain_weight"] * (d[outcome] - estimate)
    psu = d.groupby(["strata_id", "clust"], dropna=False)["_linearized"].sum().reset_index()
    variance_numerator = 0.0
    strata_count = 0
    for _, stratum in psu.groupby("strata_id", dropna=False):
        m = len(stratum)
        if m < 2:
            continue
        centered = stratum["_linearized"] - stratum["_linearized"].mean()
        variance_numerator += (m / (m - 1)) * float((centered**2).sum())
        strata_count += 1
    se = float(np.sqrt(variance_numerator) / denominator)
    return {
        "estimate": estimate,
        "se": se,
        "ci_low": max(0.0, estimate - 1.96 * se),
        "ci_high": min(1.0, estimate + 1.96 * se),
        "n": n,
        "weighted_n": denominator,
    }


def analyze(data_dir: Path) -> pd.DataFrame:
    poverty = read_stata(
        data_dir / "CS_EICV7_poverty_file.dta",
        ["hhid", "province", "district", "ur", "weight", "pop_wt", "clust", "pov_jan", "epov_jan"],
    )
    if poverty["hhid"].duplicated().any():
        raise ValueError("Poverty file must contain one row per household.")

    # The poverty file codes poor/extreme-poor as 100 and not-poor as 0.
    poverty["poor"] = poverty["pov_jan"].eq(100).astype("int8")
    poverty["extreme_poor"] = poverty["epov_jan"].eq(100).astype("int8")
    poverty["district"] = poverty["district"].astype("int64")
    design = read_stata(data_dir / "CS_S01_S5_S7_Household.dta", ["hhid", "strata_id"])
    poverty = poverty.merge(design, on="hhid", how="left", validate="one_to_one")
    if poverty["strata_id"].isna().any():
        raise ValueError("Survey strata could not be matched for every poverty-file household.")

    vup = household_vup_flags(data_dir)
    poverty = poverty.merge(vup.rename("vup_any"), how="left", left_on="hhid", right_index=True, validate="one_to_one")
    poverty["vup_any"] = poverty["vup_any"].fillna(0).astype("int8")

    finance = household_financial_flags(data_dir)
    poverty = poverty.merge(finance, how="left", left_on="hhid", right_index=True, validate="one_to_one")
    if poverty["broad_financial_or_tontine_access"].isna().any():
        raise ValueError("Savings module is missing households; inspect before treating missing access as zero.")

    poverty["double_excluded"] = (
        poverty["vup_any"].eq(0) & poverty["bank_or_mobile_account"].eq(0)
    ).astype("int8")

    rows: list[dict[str, object]] = []
    for district, group in poverty.groupby("district", sort=True):
        poor_domain = group["poor"].eq(1)
        all_domain = pd.Series(True, index=group.index)
        measures = {
            "poverty_rate": weighted_estimate(group, "poor", all_domain, weight_col="pop_wt"),
            "extreme_poverty_rate": weighted_estimate(group, "extreme_poor", all_domain),
            "vup_coverage_among_poor": weighted_estimate(group, "vup_any", poor_domain),
            "financial_access_among_poor": weighted_estimate(group, "bank_or_mobile_account", poor_domain),
            "broad_financial_or_tontine_access_among_poor": weighted_estimate(group, "broad_financial_or_tontine_access", poor_domain),
            "tontine_participation_among_poor": weighted_estimate(group, "tontine_participation", poor_domain),
            "double_exclusion_among_poor": weighted_estimate(group, "double_excluded", poor_domain),
        }
        row: dict[str, object] = {
            "district_code": int(district),
            "district": DISTRICTS.get(int(district), "Unknown"),
            "sample_households": int(len(group)),
            "sample_poor_households": int(poor_domain.sum()),
            "estimated_poor_households": float((group["weight"] * group["poor"]).sum()),
            "estimated_population": float(group["pop_wt"].sum()),
            "estimated_poor_population": float((group["pop_wt"] * group["poor"]).sum()),
        }
        for name, estimate in measures.items():
            row[name] = estimate["estimate"]
            row[f"{name}_se"] = estimate["se"]
            row[f"{name}_ci_low"] = estimate["ci_low"]
            row[f"{name}_ci_high"] = estimate["ci_high"]
        row["estimated_double_excluded_poor_households"] = float(
            (group["weight"] * group["poor"] * group["double_excluded"]).sum()
        )
        row["reliability_flag"] = "small poor-household sample" if int(poor_domain.sum()) < 50 else ""
        rows.append(row)

    result = pd.DataFrame(rows)
    result["published_poverty_rate_pct"] = result["district"].map(PUBLISHED_POVERTY_RATES)
    result["poverty_rate_difference_pp"] = (
        result["poverty_rate"] * 100 - result["published_poverty_rate_pct"]
    )
    rounded_rates = (result["poverty_rate"] * 100).round(1)
    if result["published_poverty_rate_pct"].isna().any() or not rounded_rates.eq(
        result["published_poverty_rate_pct"]
    ).all():
        raise ValueError("Population-weighted district poverty rates do not match NISR benchmarks to 0.1 pp.")
    result["priority_rank_by_double_excluded_count"] = result[
        "estimated_double_excluded_poor_households"
    ].rank(method="min", ascending=False).astype("int64")
    result["priority_rank_by_double_exclusion_rate"] = result[
        "double_exclusion_among_poor"
    ].rank(method="min", ascending=False).astype("int64")
    return result.sort_values("priority_rank_by_double_excluded_count")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("Microdata/Cross_Section"),
        help="Folder containing the EICV7 cross-section .dta files.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()

    output = analyze(args.data_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = args.output_dir / "eicv7_district_double_exclusion.csv"
    output.to_csv(destination, index=False)
    print(f"Wrote district aggregates: {destination}")
    print(f"Districts: {len(output)} | Columns: {len(output.columns)}")
    print(output[[
        "district", "sample_households", "sample_poor_households",
        "poverty_rate", "vup_coverage_among_poor",
        "financial_access_among_poor",
        "broad_financial_or_tontine_access_among_poor",
        "tontine_participation_among_poor", "double_exclusion_among_poor",
        "estimated_double_excluded_poor_households",
    ]].to_string(index=False, formatters={
        "poverty_rate": "{:.1%}".format,
        "vup_coverage_among_poor": "{:.1%}".format,
        "financial_access_among_poor": "{:.1%}".format,
        "broad_financial_or_tontine_access_among_poor": "{:.1%}".format,
        "tontine_participation_among_poor": "{:.1%}".format,
        "double_exclusion_among_poor": "{:.1%}".format,
        "estimated_double_excluded_poor_households": "{:,.0f}".format,
    }))


if __name__ == "__main__":
    main()
