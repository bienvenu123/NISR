"""Load EICV7 district aggregates and derive pathway, reliability and national figures.

Paths are resolved from this file: ``lab/`` is one level below the repository
root, and ``pages/`` lives at the same depth, so both use
``Path(__file__).resolve().parents[1]``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import streamlit as st
except ModuleNotFoundError:  # unit tests can import the pure loaders without the app runtime
    st = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "outputs" / "eicv7_district_double_exclusion.csv"
GEOJSON_PATH = ROOT / "data" / "rwanda_districts.geojson"

MIN_SAMPLE_N = 30
RELIABLE_MIN_N = 100
RELATIVE_SE_MAX = 0.30
PATHWAY_TOLERANCE = 0.005

LOAN_REASONS: list[tuple[str, str]] = [
    ("Insufficient income", "insufficient_income_among_poor_with_recorded_loan_denial"),
    ("Insufficient collateral", "insufficient_collateral_among_poor_with_recorded_loan_denial"),
    ("Debt-history problems", "debt_history_problems_among_poor_with_recorded_loan_denial"),
    ("Unclear loan purpose", "unclear_loan_purpose_among_poor_with_recorded_loan_denial"),
    ("Other stated reason", "other_loan_denial_reason_among_poor_with_recorded_loan_denial"),
]

VUP_REASONS: list[tuple[str, str]] = [
    (
        "Household had no workers",
        "vup_ds_reason_no_household_workers_among_poor_direct_support_households",
    ),
    (
        "Caring for a person with severe disability",
        "vup_ds_reason_care_for_severe_disability_among_poor_direct_support_households",
    ),
    (
        "Respondent did not know",
        "vup_ds_reason_dont_know_among_poor_direct_support_households",
    ),
]

REQUIRED_COLUMNS: tuple[str, ...] = (
    "district_code",
    "district",
    "sample_households",
    "sample_poor_households",
    "estimated_poor_households",
    "estimated_population",
    "estimated_poor_population",
    "poverty_rate",
    "extreme_poverty_rate",
    "vup_coverage_among_poor",
    "vup_coverage_among_poor_se",
    "vup_coverage_among_poor_ci_low",
    "vup_coverage_among_poor_ci_high",
    "vup_coverage_among_poor_sample_n",
    "financial_access_among_poor",
    "financial_access_among_poor_se",
    "financial_access_among_poor_ci_low",
    "financial_access_among_poor_ci_high",
    "financial_access_among_poor_sample_n",
    "broad_financial_or_tontine_access_among_poor",
    "tontine_participation_among_poor",
    "tontine_participation_among_poor_sample_n",
    "double_exclusion_among_poor",
    "double_exclusion_among_poor_se",
    "double_exclusion_among_poor_ci_low",
    "double_exclusion_among_poor_ci_high",
    "double_exclusion_among_poor_sample_n",
    "credit_denial_recorded_among_poor",
    "credit_denial_recorded_among_poor_se",
    "credit_denial_recorded_among_poor_ci_low",
    "credit_denial_recorded_among_poor_ci_high",
    "credit_denial_recorded_among_poor_sample_n",
    "estimated_double_excluded_poor_households",
    "reliability_flag",
    "published_poverty_rate_pct",
    "poverty_rate_difference_pp",
    "priority_rank_by_double_excluded_count",
    "priority_rank_by_double_exclusion_rate",
    "extreme_poverty_rate_sample_n",
    "poverty_rate_sample_n",
)


def _reason_columns() -> list[str]:
    columns: list[str] = []
    for _label, base in (*LOAN_REASONS, *VUP_REASONS):
        columns.extend(
            [base, f"{base}_se", f"{base}_ci_low", f"{base}_ci_high", f"{base}_sample_n"]
        )
    return columns


def _zscore(values: np.ndarray) -> np.ndarray:
    """Population z-score. A constant input returns zeros."""
    array = np.asarray(values, dtype=float)
    spread = float(array.std(ddof=0))
    if spread < 1e-12:
        return np.zeros_like(array)
    return (array - float(array.mean())) / spread


def pathway_shares(
    vup: np.ndarray,
    financial: np.ndarray,
    double_exclusion: np.ndarray,
    tolerance: float = PATHWAY_TOLERANCE,
) -> dict[str, np.ndarray]:
    """Split poor households into four pathway cells from the marginal rates.

    Among poor households, with ``v`` = VUP coverage, ``f`` = bank or
    mobile-money access, and ``d`` = double exclusion (neither):

    - ``share_no_vup_no_account = d``
    - ``share_vup_and_account = v + f + d - 1``
    - ``share_vup_only = v - share_vup_and_account``
    - ``share_account_only = f - share_vup_and_account``

    These identities use only the three marginals. They do not assume that VUP
    and account holding are independent. Values in ``(-tolerance, 0)`` are
    clipped to zero. A cell below ``-tolerance``, or four cells that miss 1 by
    more than ``tolerance``, sets ``pathway_consistency_warning``. Large
    negatives are kept so the warning stays visible.
    """
    v = np.asarray(vup, dtype=float)
    f = np.asarray(financial, dtype=float)
    d = np.asarray(double_exclusion, dtype=float)
    both = v + f + d - 1.0
    vup_only = v - both
    account_only = f - both
    neither = d.copy()
    cells = np.vstack([neither, both, vup_only, account_only])
    raw_sum = cells.sum(axis=0)
    warning = (cells < -tolerance).any(axis=0) | (np.abs(raw_sum - 1.0) > tolerance)
    small_negative = (cells < 0.0) & (cells > -tolerance)
    cells = cells.copy()
    cells[small_negative] = 0.0
    return {
        "share_no_vup_no_account": cells[0],
        "share_vup_and_account": cells[1],
        "share_vup_only": cells[2],
        "share_account_only": cells[3],
        "pathway_consistency_warning": warning,
    }


def reliability_labels(
    double_exclusion: np.ndarray,
    standard_error: np.ndarray,
    sample_n: np.ndarray,
) -> np.ndarray:
    """Label district double-exclusion estimates.

    Reliable: sample of poor households is at least 100 and the relative
    standard error (standard error / rate) is at most 0.30. Unreliable: sample
    below 30. Every other district is "Interpret with caution". A zero rate
    has an infinite relative standard error, so it is not labelled reliable.
    """
    rate = np.asarray(double_exclusion, dtype=float)
    error = np.asarray(standard_error, dtype=float)
    n = np.asarray(sample_n, dtype=float)
    relative = np.where(rate > 0, error / rate, np.inf)
    labels = np.full(rate.shape, "Interpret with caution", dtype=object)
    reliable = (n >= RELIABLE_MIN_N) & (relative <= RELATIVE_SE_MAX)
    labels[reliable] = "Reliable"
    labels[n < MIN_SAMPLE_N] = "Unreliable"
    return labels


def reach_difficulty(vup_gap: np.ndarray, financial_gap: np.ndarray) -> np.ndarray:
    """Descriptive reach-difficulty index.

    Mean of the z-scores of the VUP gap (1 - VUP coverage among poor
    households) and the financial gap (1 - bank or mobile-money access among
    poor households). A higher value means both gaps are larger than in the
    typical district in this file. It is not a prediction, a needs score, or
    an eligibility rule.
    """
    return (_zscore(vup_gap) + _zscore(financial_gap)) / 2.0


def plottable_rows(frame: pd.DataFrame, value_column: str) -> pd.DataFrame:
    """Return rows whose ``{value}_sample_n`` is at least 30.

    Districts below that threshold are omitted so a chart never draws them,
    including cases where the published interval collapses to [0, 0] or [1, 1].
    """
    n_column = f"{value_column}_sample_n"
    if n_column not in frame.columns:
        raise ValueError(f"The district CSV has no {n_column} column.")
    sample_n = pd.to_numeric(frame[n_column], errors="coerce")
    return frame.loc[sample_n >= MIN_SAMPLE_N].copy()


def require_plottable(sample_n: pd.Series, *, what: str = "indicator") -> None:
    """Raise if any row would plot an indicator with sample_n below 30."""
    numeric = pd.to_numeric(sample_n, errors="coerce").fillna(0)
    if (numeric < MIN_SAMPLE_N).any():
        raise ValueError(
            f"Refusing to plot {what}: at least one row has sample_n below {MIN_SAMPLE_N}."
        )


def usable_interval(
    low: np.ndarray,
    high: np.ndarray,
    sample_n: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Blank intervals that are degenerate or based on sample_n below 30.

    A degenerate interval is exactly [0, 0] or [1, 1]. Blanked bounds are NaN
    so a chart can omit the error bar.
    """
    lower = np.asarray(low, dtype=float).copy()
    upper = np.asarray(high, dtype=float).copy()
    n = np.asarray(sample_n, dtype=float)
    collapsed = ((lower <= 0.0) & (upper <= 0.0)) | ((lower >= 1.0) & (upper >= 1.0))
    bad = (n < MIN_SAMPLE_N) | collapsed | ~np.isfinite(lower) | ~np.isfinite(upper)
    lower[bad] = np.nan
    upper[bad] = np.nan
    return lower, upper


def _validate_columns(frame: pd.DataFrame) -> None:
    required = list(REQUIRED_COLUMNS) + _reason_columns()
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(
            "The district CSV is missing required fields: " + ", ".join(missing)
        )


def _read_geojson(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"The GeoJSON file could not be parsed: {exc}") from exc
    features = payload.get("features") if isinstance(payload, dict) else None
    if not isinstance(features, list) or not features:
        raise ValueError("The GeoJSON file has no features.")
    if any("dist_code" not in feature.get("properties", {}) for feature in features):
        raise ValueError("The GeoJSON features are missing the dist_code property.")
    return payload


def _assert_code_join(frame: pd.DataFrame, geojson: dict[str, Any]) -> None:
    polygon_codes = [str(feature["properties"]["dist_code"]) for feature in geojson["features"]]
    if len(polygon_codes) != len(set(polygon_codes)):
        raise ValueError("GeoJSON district codes are not unique.")
    district_codes = set(frame["district_code_str"])
    if district_codes != set(polygon_codes) or len(polygon_codes) != len(frame):
        missing = sorted(district_codes - set(polygon_codes))
        extra = sorted(set(polygon_codes) - district_codes)
        raise ValueError(
            "The district codes in the CSV do not match dist_code in the GeoJSON "
            f"exactly once. Missing polygons for {missing or 'none'}; "
            f"extra polygons {extra or 'none'}."
        )


def add_derived_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with pathway cells, reliability and the reach index."""
    out = frame.copy()
    poor = pd.to_numeric(out["estimated_poor_households"], errors="coerce")
    if poor.isna().any() or (poor <= 0).any():
        raise ValueError("estimated_poor_households must be positive for every district.")
    shares = pathway_shares(
        out["vup_coverage_among_poor"],
        out["financial_access_among_poor"],
        out["double_exclusion_among_poor"],
    )
    for name, values in shares.items():
        out[name] = values
    households = poor.to_numpy(dtype=float)
    out["n_no_vup_no_account"] = out["share_no_vup_no_account"] * households
    out["n_vup_and_account"] = out["share_vup_and_account"] * households
    out["n_vup_only"] = out["share_vup_only"] * households
    out["n_account_only"] = out["share_account_only"] * households
    out["vup_gap"] = 1.0 - out["vup_coverage_among_poor"].astype(float)
    out["financial_gap"] = 1.0 - out["financial_access_among_poor"].astype(float)
    out["log_poor_households"] = np.log(households)
    rate = out["double_exclusion_among_poor"].to_numpy(dtype=float)
    error = out["double_exclusion_among_poor_se"].to_numpy(dtype=float)
    out["de_relative_se"] = np.where(rate > 0, error / rate, np.inf)
    out["reliability_label"] = reliability_labels(
        rate,
        error,
        out["double_exclusion_among_poor_sample_n"].to_numpy(dtype=float),
    )
    out["reach_difficulty"] = reach_difficulty(
        out["vup_gap"].to_numpy(dtype=float),
        out["financial_gap"].to_numpy(dtype=float),
    )
    out["pathway_consistency_warning"] = out["pathway_consistency_warning"].astype(bool)
    return out


def _pooled_share(frame: pd.DataFrame, column: str) -> tuple[float | None, int]:
    """Weight a reason share by recorded cases. Hide it when the pool is under 30."""
    sample_n = pd.to_numeric(frame[f"{column}_sample_n"], errors="coerce").fillna(0).to_numpy()
    values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
    mask = (sample_n > 0) & np.isfinite(values)
    total = float(sample_n[mask].sum()) if mask.any() else 0.0
    if total < MIN_SAMPLE_N:
        return None, int(round(total))
    share = float(np.average(values[mask], weights=sample_n[mask]))
    return share, int(round(total))


def _weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    weight = weights.to_numpy(dtype=float)
    value = values.to_numpy(dtype=float)
    total = float(weight.sum())
    if total <= 0:
        raise ValueError("Cannot weight a national share because the weights sum to zero.")
    return float(np.average(value, weights=weight))


def national_summary(frame: pd.DataFrame) -> dict[str, Any]:
    """National figures using the same weights as the main dashboard.

    Poverty is the sum of estimated poor population divided by the sum of
    estimated population. Shares among poor households are weighted by
    estimated poor households. The double-exclusion rate is the sum of
    estimated double-excluded poor households divided by the sum of estimated
    poor households.
    """
    poor_households = float(frame["estimated_poor_households"].sum())
    population = float(frame["estimated_population"].sum())
    poor_population = float(frame["estimated_poor_population"].sum())
    if poor_households <= 0 or population <= 0:
        raise ValueError("The district file has no population to summarise.")
    weights = frame["estimated_poor_households"]
    double_excluded = float(frame["estimated_double_excluded_poor_households"].sum())
    summary: dict[str, Any] = {
        "poor_households": poor_households,
        "population": population,
        "poor_population": poor_population,
        "poverty_rate": poor_population / population,
        "extreme_poverty_rate": _weighted_mean(
            frame["extreme_poverty_rate"], frame["estimated_population"]
        ),
        "vup_coverage": _weighted_mean(frame["vup_coverage_among_poor"], weights),
        "financial_access": _weighted_mean(frame["financial_access_among_poor"], weights),
        "tontine": _weighted_mean(frame["tontine_participation_among_poor"], weights),
        "broad_financial": _weighted_mean(
            frame["broad_financial_or_tontine_access_among_poor"], weights
        ),
        "double_excluded_households": double_excluded,
        "double_exclusion_rate": double_excluded / poor_households,
        "credit_denial_rate": _weighted_mean(
            frame["credit_denial_recorded_among_poor"], weights
        ),
        "credit_denial_sample_n": int(frame["credit_denial_recorded_among_poor_sample_n"].sum()),
        "n_districts": int(len(frame)),
        "n_reliable": int((frame["reliability_label"] == "Reliable").sum()),
        "n_caution": int((frame["reliability_label"] == "Interpret with caution").sum()),
        "n_unreliable": int((frame["reliability_label"] == "Unreliable").sum()),
        "pathway_warning_districts": frame.loc[
            frame["pathway_consistency_warning"], "district"
        ].astype(str).tolist(),
    }
    summary["vup_gap"] = 1.0 - summary["vup_coverage"]
    summary["financial_gap"] = 1.0 - summary["financial_access"]
    for share_name, count_name in (
        ("share_no_vup_no_account", "n_no_vup_no_account"),
        ("share_vup_and_account", "n_vup_and_account"),
        ("share_vup_only", "n_vup_only"),
        ("share_account_only", "n_account_only"),
    ):
        summary[share_name] = _weighted_mean(frame[share_name], weights)
        summary[count_name] = float(frame[count_name].sum())

    def _pack(pairs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        packed = []
        for label, column in pairs:
            share, sample_n = _pooled_share(frame, column)
            plottable = int((frame[f"{column}_sample_n"] >= MIN_SAMPLE_N).sum())
            packed.append(
                {
                    "label": label,
                    "column": column,
                    "share": share,
                    "sample_n": sample_n,
                    "districts_plottable": plottable,
                }
            )
        return packed

    summary["loan_reasons"] = _pack(LOAN_REASONS)
    summary["vup_reasons"] = _pack(VUP_REASONS)
    return summary


def load_inputs(csv_path: Path, geo_path: Path) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    """Read the CSV and GeoJSON, derive columns, and build the national summary."""
    try:
        frame = pd.read_csv(csv_path, encoding="utf-8")
    except pd.errors.ParserError as exc:
        raise ValueError(f"The district CSV could not be parsed: {exc}") from exc
    except OSError as exc:
        raise ValueError(f"The district CSV could not be read: {exc}") from exc
    _validate_columns(frame)
    text_columns = {"district", "reliability_flag"}
    for column in frame.columns:
        if column not in text_columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["district"] = frame["district"].astype(str)
    frame["district_code_str"] = frame["district_code"].astype(int).astype(str)
    frame["reliability_flag"] = frame["reliability_flag"].fillna("").astype(str)
    geojson = _read_geojson(geo_path)
    _assert_code_join(frame, geojson)
    provinces = {
        str(feature["properties"]["dist_code"]): str(
            feature["properties"].get("province_eng", "")
        )
        for feature in geojson["features"]
    }
    frame["province"] = frame["district_code_str"].map(provinces).fillna("")
    derived = add_derived_columns(frame)
    summary = national_summary(derived)
    return derived, geojson, summary


def build_analysis(
    csv_path: Path | None = None,
    geo_path: Path | None = None,
    *,
    seed: int = 42,
    n_draws: int = 5000,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load inputs and attach ranks, shrinkage, clusters, twins and spatial labels."""
    from .stats import attach_model

    frame, geojson, summary = load_inputs(csv_path or CSV_PATH, geo_path or GEOJSON_PATH)
    enriched, model = attach_model(frame, geojson, summary, seed=seed, n_draws=n_draws)
    return enriched, geojson, summary, model


def _cached(spinner: str):
    """Apply ``st.cache_data`` when Streamlit is installed; otherwise return the function."""

    def decorate(func):
        if st is None:
            return func
        return st.cache_data(show_spinner=spinner, max_entries=2)(func)

    return decorate


@_cached("Loading EICV7 district estimates…")
def load_lab_data() -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    """Cached loader used by the lab pages: district frame, GeoJSON, national dict."""
    if not CSV_PATH.is_file() or not GEOJSON_PATH.is_file():
        missing = [str(path) for path in (CSV_PATH, GEOJSON_PATH) if not path.is_file()]
        raise FileNotFoundError("Missing file(s): " + "; ".join(missing))
    return load_inputs(CSV_PATH, GEOJSON_PATH)


@_cached("Preparing ranks, clusters and the spatial summary…")
def _cached_analysis(csv_mtime_ns: int, geo_mtime_ns: int, seed: int, n_draws: int):
    """Cache key includes file timestamps, the Monte Carlo seed and the draw count."""
    del csv_mtime_ns, geo_mtime_ns
    return build_analysis(seed=seed, n_draws=n_draws)


def _copy_model(model: dict[str, Any]) -> dict[str, Any]:
    copied = dict(model)
    for key in ("profile_z", "profile_raw", "twins"):
        if key in copied and isinstance(copied[key], pd.DataFrame):
            copied[key] = copied[key].copy()
    if "alerts" in copied:
        copied["alerts"] = [dict(item) for item in copied["alerts"]]
    return copied


def open_lab() -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Load the cached analysis for a page, or stop with a readable error."""
    try:
        if not CSV_PATH.is_file() or not GEOJSON_PATH.is_file():
            missing = [str(path) for path in (CSV_PATH, GEOJSON_PATH) if not path.is_file()]
            raise FileNotFoundError("Missing file(s): " + "; ".join(missing))
        frame, geojson, summary, model = _cached_analysis(
            CSV_PATH.stat().st_mtime_ns,
            GEOJSON_PATH.stat().st_mtime_ns,
            42,
            5000,
        )
    except FileNotFoundError as exc:
        st.error(
            "A required data file is missing "
            f"({exc}). Expected outputs/eicv7_district_double_exclusion.csv and "
            "data/rwanda_districts.geojson next to dashboard.py."
        )
        st.stop()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()
    except OSError as exc:
        st.error(f"Could not read the lab inputs: {exc}")
        st.stop()
    return frame.copy(), geojson, dict(summary), _copy_model(model)
