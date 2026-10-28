"""Pure statistics for the Innovation Lab.

Every routine is deterministic given its seed. Nothing here reads a file or
calls Streamlit. Inputs are district aggregates already loaded by ``lab.data``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from . import texts

SEED = 42
N_DRAWS = 5000
N_PERMUTATIONS = 999
SE_FLOOR = 1e-8
TAU_FLOOR = 1e-6
LOCAL_ALPHA = 0.05

DEFAULT_WEIGHTS: dict[str, float] = {
    "de_rate": 0.35,
    "de_count": 0.35,
    "vup_gap": 0.10,
    "financial_gap": 0.10,
    "poverty_rate": 0.10,
}

WEIGHT_ORDER: tuple[str, ...] = (
    "de_rate",
    "de_count",
    "vup_gap",
    "financial_gap",
    "poverty_rate",
)

CLUSTER_FEATURES: tuple[str, ...] = (
    "poverty_rate",
    "vup_gap",
    "financial_gap",
    "double_exclusion_among_poor",
    "log_poor_households",
)

TWIN_FEATURES: tuple[str, ...] = CLUSTER_FEATURES + (
    "extreme_poverty_rate",
    "tontine_participation_among_poor",
)

RULES: tuple[str, ...] = ("R0", "R1", "R2", "R3", "R4")

RULE_LABELS: dict[str, str] = {
    "R0": "R0 · Proportional to poor households",
    "R1": "R1 · Highest double-exclusion rate first",
    "R2": "R2 · Highest double-exclusion count first",
    "R3": "R3 · Hybrid priority index",
    "R4": "R4 · Reliability-aware rate",
}


def zscore(values: np.ndarray) -> np.ndarray:
    """Population z-score (divisor n). A constant series returns zeros."""
    array = np.asarray(values, dtype=float)
    spread = float(array.std(ddof=0))
    if not np.isfinite(spread) or spread < 1e-12:
        return np.zeros_like(array)
    return (array - float(array.mean())) / spread


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Rescale non-negative weights so they sum to 1. All-zero weights become equal."""
    cleaned = {key: max(0.0, float(weights.get(key, 0.0))) for key in WEIGHT_ORDER}
    total = float(sum(cleaned.values()))
    if total <= 0:
        share = 1.0 / len(WEIGHT_ORDER)
        return {key: share for key in WEIGHT_ORDER}
    return {key: cleaned[key] / total for key in WEIGHT_ORDER}


@dataclass
class EBResult:
    """Empirical-Bayes shrinkage of the district double-exclusion rate."""

    d_eb: np.ndarray
    shrink: np.ndarray
    eb_shift_pp: np.ndarray
    eb_low: np.ndarray
    eb_high: np.ndarray
    mu: float
    tau2: float
    shift_flag: np.ndarray


def empirical_bayes(
    double_exclusion: np.ndarray,
    standard_error: np.ndarray,
    *,
    se_floor: float = SE_FLOOR,
    tau_floor: float = TAU_FLOOR,
) -> EBResult:
    """Shrink district rates toward the inverse-variance weighted mean.

    ``mu`` is that weighted mean. ``tau²`` is ``max(var(d, ddof=1) - mean(s²), tau_floor)``
    after flooring standard errors at ``se_floor``. The shrink factor is
    ``tau² / (tau² + s²)``. The stabilised rate is ``shrink * d + (1 - shrink) * mu``.
    The approximate interval uses posterior sd ``s * sqrt(shrink)`` and a 1.96
    normal multiplier, clipped to [0, 1]. ``eb_shift_pp`` is ``(d_eb - d) * 100``,
    flagged when the absolute shift exceeds 2 percentage points.
    """
    rate = np.asarray(double_exclusion, dtype=float)
    error = np.maximum(np.asarray(standard_error, dtype=float), se_floor)
    if rate.shape != error.shape:
        raise ValueError("Double-exclusion rates and standard errors must have the same shape.")
    precision = 1.0 / error**2
    mu = float(np.sum(precision * rate) / np.sum(precision))
    tau2 = max(float(np.var(rate, ddof=1) - np.mean(error**2)), tau_floor)
    shrink = tau2 / (tau2 + error**2)
    stabilised = shrink * rate + (1.0 - shrink) * mu
    posterior_sd = error * np.sqrt(shrink)
    low = np.clip(stabilised - 1.96 * posterior_sd, 0.0, 1.0)
    high = np.clip(stabilised + 1.96 * posterior_sd, 0.0, 1.0)
    shift_pp = (stabilised - rate) * 100.0
    return EBResult(
        d_eb=stabilised,
        shrink=shrink,
        eb_shift_pp=shift_pp,
        eb_low=low,
        eb_high=high,
        mu=mu,
        tau2=tau2,
        shift_flag=np.abs(shift_pp) > 2.0,
    )


def _rank_high_to_low(draws: np.ndarray) -> np.ndarray:
    """Rank 1 is the largest value. Ties keep the earlier column first."""
    order = np.argsort(-draws, axis=1, kind="mergesort")
    ranks = np.empty_like(order)
    ranks[np.arange(draws.shape[0])[:, None], order] = np.arange(1, draws.shape[1] + 1)
    return ranks


def monte_carlo_ranks(
    double_exclusion: np.ndarray,
    standard_error: np.ndarray,
    poor_households: np.ndarray,
    *,
    n_draws: int = N_DRAWS,
    seed: int = SEED,
) -> pd.DataFrame:
    """Median rank, 90% interval and top-5 / top-10 probabilities.

    Draws are normal, clipped to [0, 1], and seeded. Count draws are the rate
    draw times estimated poor households. The same seed always returns the
    same frame.
    """
    rate = np.asarray(double_exclusion, dtype=float)
    error = np.maximum(np.asarray(standard_error, dtype=float), SE_FLOOR)
    poor = np.asarray(poor_households, dtype=float)
    n_districts = rate.shape[0]
    generator = np.random.default_rng(seed)
    draws = generator.normal(loc=rate, scale=error, size=(n_draws, n_districts))
    np.clip(draws, 0.0, 1.0, out=draws)
    rate_ranks = _rank_high_to_low(draws)
    count_ranks = _rank_high_to_low(draws * poor)
    frame = pd.DataFrame(
        {
            "median_rank_rate": np.median(rate_ranks, axis=0),
            "rank_rate_p05": np.quantile(rate_ranks, 0.05, axis=0),
            "rank_rate_p95": np.quantile(rate_ranks, 0.95, axis=0),
            "p_top5_rate": np.mean(rate_ranks <= 5, axis=0),
            "p_top10_rate": np.mean(rate_ranks <= 10, axis=0),
            "median_rank_count": np.median(count_ranks, axis=0),
            "rank_count_p05": np.quantile(count_ranks, 0.05, axis=0),
            "rank_count_p95": np.quantile(count_ranks, 0.95, axis=0),
            "p_top5_count": np.mean(count_ranks <= 5, axis=0),
            "p_top10_count": np.mean(count_ranks <= 10, axis=0),
        }
    )
    return frame


@dataclass
class PriorityResult:
    """Weighted z-score index. Rank 1 is the highest index."""

    index: np.ndarray
    rank: np.ndarray
    weights: dict[str, float]
    contributions: dict[str, np.ndarray]
    zscores: dict[str, np.ndarray]


def priority_from_z(zscores: dict[str, np.ndarray], weights: dict[str, float]) -> PriorityResult:
    """Combine precomputed z-scores with normalised weights."""
    normalised = normalize_weights(weights)
    contributions = {key: normalised[key] * np.asarray(zscores[key], dtype=float) for key in WEIGHT_ORDER}
    index = np.sum([contributions[key] for key in WEIGHT_ORDER], axis=0)
    order = np.argsort(-index, kind="mergesort")
    rank = np.empty(index.shape[0], dtype=float)
    rank[order] = np.arange(1, index.shape[0] + 1)
    return PriorityResult(
        index=index,
        rank=rank,
        weights=normalised,
        contributions=contributions,
        zscores={key: np.asarray(zscores[key], dtype=float) for key in WEIGHT_ORDER},
    )


def priority_index(
    double_exclusion: np.ndarray,
    double_excluded_count: np.ndarray,
    vup_gap: np.ndarray,
    financial_gap: np.ndarray,
    poverty_rate: np.ndarray,
    weights: dict[str, float] | None = None,
) -> PriorityResult:
    """Transparent priority index. Default weights are 0.35 / 0.35 / 0.10 / 0.10 / 0.10."""
    zscores = {
        "de_rate": zscore(double_exclusion),
        "de_count": zscore(double_excluded_count),
        "vup_gap": zscore(vup_gap),
        "financial_gap": zscore(financial_gap),
        "poverty_rate": zscore(poverty_rate),
    }
    return priority_from_z(zscores, weights or DEFAULT_WEIGHTS)


def add_priority(frame: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Copy ``frame`` and add the index, rank, z-scores and contributions."""
    result = priority_index(
        frame["double_exclusion_among_poor"].to_numpy(),
        frame["estimated_double_excluded_poor_households"].to_numpy(),
        frame["vup_gap"].to_numpy(),
        frame["financial_gap"].to_numpy(),
        frame["poverty_rate"].to_numpy(),
        weights,
    )
    out = frame.copy()
    out["priority_index"] = result.index
    out["priority_rank"] = result.rank
    for key, values in result.zscores.items():
        out[f"z_{key}"] = values
    for key, values in result.contributions.items():
        out[f"contrib_{key}"] = values
    return out


def weight_sensitivity(
    double_exclusion: np.ndarray,
    double_excluded_count: np.ndarray,
    vup_gap: np.ndarray,
    financial_gap: np.ndarray,
    poverty_rate: np.ndarray,
    districts: np.ndarray,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """How many of the original top 10 leave when each weight moves by ±50%."""
    base = priority_index(
        double_exclusion,
        double_excluded_count,
        vup_gap,
        financial_gap,
        poverty_rate,
        weights,
    )
    names = np.asarray(districts)
    base_top = set(names[base.rank <= 10])
    rows: list[dict[str, object]] = []
    for key in WEIGHT_ORDER:
        for factor, label in ((1.5, "+50%"), (0.5, "-50%")):
            moved = dict(base.weights)
            moved[key] = moved[key] * factor
            alt = priority_from_z(base.zscores, moved)
            dropped = sorted(base_top - set(names[alt.rank <= 10]))
            rows.append(
                {
                    "Weight": texts.WEIGHT_LABELS[key],
                    "Change": label,
                    "Top 10 replaced": len(dropped),
                    "Districts leaving the top 10": ", ".join(dropped) if dropped else "None",
                }
            )
    return pd.DataFrame(rows)


def allocate(
    poor_households: np.ndarray,
    double_exclusion: np.ndarray,
    budget: float,
    rule: str,
    priority: np.ndarray | None = None,
    reliability: np.ndarray | None = None,
) -> np.ndarray:
    """Allocate a household budget without exceeding each district's poor households.

    R0 is proportional to estimated poor households. R1, R2 and R3 are greedy
    fills by rate, count and priority index. R4 is R1 with reliable districts
    first, then "Interpret with caution", then "Unreliable", so less reliable
    districts are down-weighted rather than dropped. When the budget exceeds
    total poor households it is capped at that total.
    """
    poor = np.asarray(poor_households, dtype=float)
    rate = np.asarray(double_exclusion, dtype=float)
    if rule not in RULES:
        raise ValueError(f"Unknown allocation rule: {rule}")
    if budget < 0:
        raise ValueError("Budget must be non-negative.")
    capacity = float(poor.sum())
    remaining = min(float(budget), capacity)
    allocation = np.zeros(poor.shape[0], dtype=float)
    if remaining <= 0 or capacity <= 0:
        return allocation
    if rule == "R0":
        return remaining * poor / capacity
    if rule == "R1":
        order = np.argsort(-rate, kind="mergesort")
    elif rule == "R2":
        order = np.argsort(-(rate * poor), kind="mergesort")
    elif rule == "R3":
        if priority is None:
            raise ValueError("R3 requires a priority index.")
        order = np.argsort(-np.asarray(priority, dtype=float), kind="mergesort")
    else:
        if reliability is None:
            raise ValueError("R4 requires reliability labels.")
        tier_map = {"Reliable": 0, "Interpret with caution": 1, "Unreliable": 2}
        tier = np.array([tier_map.get(str(label), 2) for label in reliability], dtype=int)
        order = np.lexsort((-rate, tier))
    for index in order:
        if remaining <= 1e-8:
            break
        take = min(poor[index], remaining)
        allocation[index] = take
        remaining -= take
    return allocation


def _expected(allocation: np.ndarray, rate: np.ndarray, total_de: float, budget: float) -> tuple[float, float, float]:
    expected = float(np.sum(allocation * rate))
    recall = expected / total_de if total_de > 0 else 0.0
    precision = expected / budget if budget > 0 else 0.0
    return expected, recall, precision


@dataclass
class ScenarioResult:
    """One budget and one rule, with a Monte Carlo interval on the reached count."""

    rule: str
    budget: float
    allocation: np.ndarray
    expected_de: float
    recall: float
    precision: float
    cost_per_de: float | None
    de_p05: float
    de_p95: float
    total_de: float
    district_p05: np.ndarray
    district_p95: np.ndarray


def simulate_scenario(
    poor_households: np.ndarray,
    double_exclusion: np.ndarray,
    standard_error: np.ndarray,
    budget: float,
    rule: str,
    *,
    priority: np.ndarray | None = None,
    reliability: np.ndarray | None = None,
    unit_cost: float | None = None,
    n_draws: int = N_DRAWS,
    seed: int = SEED,
) -> ScenarioResult:
    """Expected reach for a fixed allocation, plus a 90% interval from redrawn rates.

    The allocation is computed from the direct estimates and then held fixed.
    Draws clip the rate to [0, 1]. Cost is unit cost times the budget, divided
    by expected double-excluded households. A missing or non-positive unit cost
    leaves cost empty.
    """
    poor = np.asarray(poor_households, dtype=float)
    rate = np.asarray(double_exclusion, dtype=float)
    error = np.maximum(np.asarray(standard_error, dtype=float), SE_FLOOR)
    allocation = allocate(poor, rate, budget, rule, priority, reliability)
    spent = float(allocation.sum())
    total_de = float(np.sum(poor * rate))
    expected, recall, precision = _expected(allocation, rate, total_de, spent if spent > 0 else budget)
    generator = np.random.default_rng(seed)
    draws = generator.normal(loc=rate, scale=error, size=(n_draws, rate.shape[0]))
    np.clip(draws, 0.0, 1.0, out=draws)
    reached = draws * allocation
    district_total = reached.sum(axis=1)
    cost = None
    if unit_cost is not None and unit_cost > 0 and expected > 0:
        cost = float(unit_cost) * spent / expected
    return ScenarioResult(
        rule=rule,
        budget=spent,
        allocation=allocation,
        expected_de=expected,
        recall=recall,
        precision=precision,
        cost_per_de=cost,
        de_p05=float(np.quantile(district_total, 0.05)),
        de_p95=float(np.quantile(district_total, 0.95)),
        total_de=total_de,
        district_p05=np.quantile(reached, 0.05, axis=0),
        district_p95=np.quantile(reached, 0.95, axis=0),
    )


def targeting_frontier(
    poor_households: np.ndarray,
    double_exclusion: np.ndarray,
    priority: np.ndarray,
    reliability: np.ndarray,
    *,
    shares: np.ndarray | None = None,
) -> pd.DataFrame:
    """Recall and precision for every rule from 5% to 100% of poor households."""
    poor = np.asarray(poor_households, dtype=float)
    rate = np.asarray(double_exclusion, dtype=float)
    if shares is None:
        shares = np.round(np.arange(0.05, 1.0001, 0.05), 2)
    total_poor = float(poor.sum())
    total_de = float(np.sum(poor * rate))
    rows: list[dict[str, float | str]] = []
    for share in shares:
        budget = total_poor * float(share)
        for rule in RULES:
            allocation = allocate(poor, rate, budget, rule, priority, reliability)
            expected, recall, precision = _expected(allocation, rate, total_de, float(allocation.sum()))
            rows.append(
                {
                    "budget_share": float(share),
                    "budget": float(allocation.sum()),
                    "rule": rule,
                    "expected_de": expected,
                    "recall": recall,
                    "precision": precision,
                }
            )
    return pd.DataFrame(rows)


def _cluster_base_name(vup_gap_z: float, financial_gap_z: float) -> str:
    if vup_gap_z > 0 and financial_gap_z > 0:
        return "Uncovered and unbanked"
    if vup_gap_z > 0:
        return "Uncovered but banked"
    if financial_gap_z > 0:
        return "Covered but unbanked"
    return "Lower exclusion"


def _disambiguate_names(centers: np.ndarray) -> list[str]:
    bases = [_cluster_base_name(float(row[1]), float(row[2])) for row in centers]
    names = [""] * len(bases)
    for base in set(bases):
        members = [index for index, label in enumerate(bases) if label == base]
        if len(members) == 1:
            names[members[0]] = base
            continue
        ordered = sorted(members, key=lambda index: (-float(centers[index, 3]), index))
        if len(ordered) == 2:
            suffixes = (" — higher double exclusion", " — lower double exclusion")
        else:
            suffixes = tuple(f" — group {number}" for number in range(1, len(ordered) + 1))
        for index, suffix in zip(ordered, suffixes):
            names[index] = base + suffix
    return names


@dataclass
class TypologyResult:
    """KMeans typology, silhouette, PCA plane and cluster profiles."""

    k: int
    silhouette: float
    labels: np.ndarray
    names: np.ndarray
    pca_x: np.ndarray
    pca_y: np.ndarray
    pca_variance: tuple[float, float]
    profile_z: pd.DataFrame
    profile_raw: pd.DataFrame


def fit_typology(frame: pd.DataFrame, *, seed: int = SEED) -> TypologyResult:
    """Cluster districts for k in 3–5 and keep the highest silhouette.

    Features are standardised: poverty rate, VUP gap, financial gap,
    double-exclusion rate and log poor households. Seed 42 and ``n_init=10``
    make the labels reproducible. Every returned cluster is non-empty.
    """
    matrix = frame.loc[:, list(CLUSTER_FEATURES)].to_numpy(dtype=float)
    scaled = StandardScaler().fit_transform(matrix)
    best: tuple[float, int, np.ndarray, np.ndarray] | None = None
    for k in range(3, 6):
        model = KMeans(n_clusters=k, random_state=seed, n_init=10, algorithm="lloyd")
        labels = model.fit_predict(scaled)
        if len(np.unique(labels)) < k:
            continue
        score = float(silhouette_score(scaled, labels))
        if best is None or score > best[0]:
            best = (score, k, labels, model.cluster_centers_)
    if best is None:
        raise ValueError("KMeans did not return a complete set of clusters.")
    score, k, labels, centers = best
    cluster_names = _disambiguate_names(centers)
    names = np.array([cluster_names[int(label)] for label in labels], dtype=object)
    if min(np.bincount(labels)) < 1:
        raise ValueError("A cluster was empty.")
    pca = PCA(n_components=2, random_state=seed)
    plane = pca.fit_transform(scaled)
    profile_frame = pd.DataFrame(scaled, columns=list(CLUSTER_FEATURES))
    profile_frame["cluster"] = names
    raw = frame.loc[:, list(CLUSTER_FEATURES)].copy()
    raw["cluster"] = names
    order = (
        raw.groupby("cluster", sort=False)["double_exclusion_among_poor"].mean().sort_values(ascending=False).index
    )
    profile_z = profile_frame.groupby("cluster", sort=False).mean().loc[order]
    profile_raw = raw.groupby("cluster", sort=False).mean().loc[order]
    variance = (float(pca.explained_variance_ratio_[0]), float(pca.explained_variance_ratio_[1]))
    return TypologyResult(
        k=k,
        silhouette=score,
        labels=labels.astype(int),
        names=names,
        pca_x=plane[:, 0],
        pca_y=plane[:, 1],
        pca_variance=variance,
        profile_z=profile_z,
        profile_raw=profile_raw,
    )


def nearest_twins(frame: pd.DataFrame, *, k: int = 3) -> pd.DataFrame:
    """Three Euclidean neighbours on the standardised twin-feature vector.

    The better-performing twin is chosen later as the neighbour with the lowest
    double-exclusion rate. Distance is in standardised units, not kilometres.
    """
    matrix = frame.loc[:, list(TWIN_FEATURES)].to_numpy(dtype=float)
    scaled = StandardScaler().fit_transform(matrix)
    distance = cdist(scaled, scaled, metric="euclidean")
    np.fill_diagonal(distance, np.inf)
    order = np.argsort(distance, axis=1, kind="mergesort")[:, :k]
    districts = frame["district"].astype(str).to_numpy()
    rates = frame["double_exclusion_among_poor"].to_numpy(dtype=float)
    rows: list[dict[str, object]] = []
    for index, neighbours in enumerate(order):
        for rank, neighbour in enumerate(neighbours, start=1):
            rows.append(
                {
                    "district": districts[index],
                    "twin_rank": rank,
                    "twin": districts[int(neighbour)],
                    "distance": float(distance[index, int(neighbour)]),
                    "twin_double_exclusion": float(rates[int(neighbour)]),
                }
            )
    return pd.DataFrame(rows)


def indicator_gap(frame: pd.DataFrame, district: str, twin: str) -> pd.DataFrame:
    """Per-indicator gap, this district minus the twin."""
    columns = [
        ("Poverty rate", "poverty_rate", True),
        ("Extreme poverty rate", "extreme_poverty_rate", True),
        ("VUP coverage among poor households", "vup_coverage_among_poor", True),
        ("Financial access among poor households", "financial_access_among_poor", True),
        ("Tontine participation among poor households", "tontine_participation_among_poor", True),
        ("Double-exclusion rate", "double_exclusion_among_poor", True),
        ("Estimated poor households", "estimated_poor_households", False),
        ("Estimated double-excluded households", "estimated_double_excluded_poor_households", False),
    ]
    left = frame.loc[frame["district"] == district].iloc[0]
    right = frame.loc[frame["district"] == twin].iloc[0]
    rows = []
    for label, column, is_share in columns:
        this_value = float(left[column])
        twin_value = float(right[column])
        rows.append(
            {
                "Indicator": label,
                "This district": this_value,
                "Twin": twin_value,
                "Gap (this − twin)": this_value - twin_value,
                "Share": is_share,
            }
        )
    return pd.DataFrame(rows)


def _exterior_points(geometry: dict) -> np.ndarray:
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError(f"Unsupported geometry type: {geometry['type']}")
    points: list[list[float]] = []
    for polygon in polygons:
        if polygon:
            points.extend(polygon[0])
    if not points:
        raise ValueError("A district polygon has no vertices.")
    return np.asarray(points, dtype=float)


def district_centroids(geojson: dict) -> pd.DataFrame:
    """Average exterior-ring vertices. Acceptable for an exploratory neighbour graph."""
    rows = []
    for feature in geojson["features"]:
        points = _exterior_points(feature["geometry"])
        rows.append(
            {
                "district_code_str": str(feature["properties"]["dist_code"]),
                "lon": float(points[:, 0].mean()),
                "lat": float(points[:, 1].mean()),
            }
        )
    return pd.DataFrame(rows)


def _knn_weights(xy: np.ndarray, k: int = 5) -> np.ndarray:
    """Row-standardised k-nearest-neighbour weights. Self is excluded."""
    delta = xy[:, None, :] - xy[None, :, :]
    distance = np.sqrt(np.sum(delta * delta, axis=2))
    np.fill_diagonal(distance, np.inf)
    neighbours = np.argsort(distance, axis=1, kind="mergesort")[:, :k]
    weights = np.zeros_like(distance)
    rows = np.arange(xy.shape[0])[:, None]
    weights[rows, neighbours] = 1.0
    weights /= weights.sum(axis=1, keepdims=True)
    return weights


@dataclass
class MoranResult:
    """Global Moran's I and local quadrant labels, aligned to the input frame."""

    moran_i: float
    p_value: float
    quadrant: np.ndarray
    local_i: np.ndarray
    local_p: np.ndarray
    significant: np.ndarray
    label: np.ndarray
    lon: np.ndarray
    lat: np.ndarray
    n_permutations: int


def moran_for_districts(
    frame: pd.DataFrame,
    geojson: dict,
    *,
    value_column: str = "double_exclusion_among_poor",
    k: int = 5,
    n_perm: int = N_PERMUTATIONS,
    seed: int = SEED,
) -> MoranResult:
    """Exploratory global and local Moran's I for 30 districts.

    Centroids are vertex averages. Neighbour distance is equirectangular
    (longitude scaled by cos of mean latitude), not a surveyed kilometre grid.
    Global pseudo p-value: ``(1 + count of |I_perm| >= |I|) / (n_perm + 1)``
    from permutations of the centred values. Local statistics hold the
    district's own centred value fixed and permute the others. Quadrants use
    the sign of the centred value and its spatial lag. Labels are the quadrant
    when the local pseudo p-value is below 0.05, otherwise "Not significant".
    """
    centroids = district_centroids(geojson).set_index("district_code_str")
    aligned = centroids.loc[frame["district_code_str"].tolist()]
    lon = aligned["lon"].to_numpy(dtype=float)
    lat = aligned["lat"].to_numpy(dtype=float)
    latitude = np.deg2rad(float(lat.mean()))
    xy = np.column_stack([lon * np.cos(latitude), lat])
    weights = _knn_weights(xy, k=k)
    values = frame[value_column].to_numpy(dtype=float)
    centred = values - float(values.mean())
    denominator = float(np.dot(centred, centred))
    if denominator <= 0:
        raise ValueError("Moran's I is undefined because the indicator does not vary.")
    lag = weights @ centred
    observed = float(np.dot(centred, lag) / denominator)
    generator = np.random.default_rng(seed)
    perm_index = np.argsort(generator.random((n_perm, centred.shape[0])), axis=1)
    permuted = centred[perm_index]
    perm_lag = permuted @ weights.T
    perm_i = np.sum(permuted * perm_lag, axis=1) / np.sum(permuted * permuted, axis=1)
    global_p = float((1 + np.sum(np.abs(perm_i) >= abs(observed) - 1e-15)) / (n_perm + 1))
    local_i = centred * lag
    local_p = np.empty(centred.shape[0], dtype=float)
    n = centred.shape[0]
    for index in range(n):
        pool_mask = np.ones(n, dtype=bool)
        pool_mask[index] = False
        pool = centred[pool_mask]
        picks = np.argsort(generator.random((n_perm, n - 1)), axis=1)
        shuffled = pool[picks]
        draw = np.empty((n_perm, n), dtype=float)
        draw[:, index] = centred[index]
        draw[:, pool_mask] = shuffled
        stat = centred[index] * (draw @ weights[index])
        local_p[index] = (1 + np.sum(np.abs(stat) >= abs(local_i[index]) - 1e-15)) / (n_perm + 1)
    quadrant = np.empty(n, dtype=object)
    for index in range(n):
        high_self = centred[index] >= 0
        high_lag = lag[index] >= 0
        if high_self and high_lag:
            quadrant[index] = "HH"
        elif (not high_self) and (not high_lag):
            quadrant[index] = "LL"
        elif high_self and (not high_lag):
            quadrant[index] = "HL"
        else:
            quadrant[index] = "LH"
    significant = local_p < LOCAL_ALPHA
    label = np.where(significant, quadrant, "Not significant")
    return MoranResult(
        moran_i=observed,
        p_value=global_p,
        quadrant=quadrant,
        local_i=local_i,
        local_p=local_p,
        significant=significant,
        label=label,
        lon=lon,
        lat=lat,
        n_permutations=n_perm,
    )


def build_alerts(frame: pd.DataFrame, national: dict) -> list[dict[str, str]]:
    """Structured alerts. Severity is high, medium or info."""
    alerts: list[dict[str, str]] = []
    national_rate = float(national["double_exclusion_rate"])
    national_vup = float(national["vup_coverage"])
    for row in frame.itertuples(index=False):
        district = str(row.district)
        if float(row.double_exclusion_among_poor_ci_low) > national_rate:
            alerts.append(
                {
                    "district": district,
                    "severity": "high",
                    "code": "above_national",
                    "text": texts.alert_above_national(
                        district,
                        float(row.double_exclusion_among_poor),
                        float(row.double_exclusion_among_poor_ci_low),
                        float(row.double_exclusion_among_poor_ci_high),
                        national_rate,
                    ),
                }
            )
        if float(row.p_top5_rate) > 0.6:
            alerts.append(
                {
                    "district": district,
                    "severity": "high",
                    "code": "top5_probability",
                    "text": texts.alert_top5(
                        district, float(row.p_top5_rate), float(row.median_rank_rate)
                    ),
                }
            )
        shift = float(row.eb_shift_pp)
        if abs(shift) > 2.0:
            alerts.append(
                {
                    "district": district,
                    "severity": "medium",
                    "code": "eb_shift",
                    "text": texts.alert_eb_shift(
                        district,
                        shift,
                        float(row.double_exclusion_among_poor),
                        float(row.d_eb),
                    ),
                }
            )
        if (
            float(row.vup_coverage_among_poor) < national_vup
            and float(row.vup_coverage_among_poor_ci_high) < national_vup
        ):
            alerts.append(
                {
                    "district": district,
                    "severity": "high",
                    "code": "vup_below",
                    "text": texts.alert_vup_below(
                        district,
                        float(row.vup_coverage_among_poor),
                        float(row.vup_coverage_among_poor_ci_high),
                        national_vup,
                    ),
                }
            )
        if row.reliability_label == "Unreliable":
            alerts.append(
                {
                    "district": district,
                    "severity": "medium",
                    "code": "unreliable",
                    "text": texts.alert_reliability(
                        district,
                        "Unreliable",
                        int(row.double_exclusion_among_poor_sample_n),
                        float(row.de_relative_se),
                    ),
                }
            )
        elif row.reliability_label == "Interpret with caution":
            alerts.append(
                {
                    "district": district,
                    "severity": "info",
                    "code": "caution",
                    "text": texts.alert_reliability(
                        district,
                        "Interpret with caution",
                        int(row.double_exclusion_among_poor_sample_n),
                        float(row.de_relative_se),
                    ),
                }
            )
        if row.lisa_quadrant == "HH" and bool(row.lisa_significant):
            alerts.append(
                {
                    "district": district,
                    "severity": "high",
                    "code": "lisa_hh",
                    "text": texts.alert_lisa(district, float(row.lisa_p)),
                }
            )
    order = {"high": 0, "medium": 1, "info": 2}
    alerts.sort(key=lambda item: (order[item["severity"]], item["district"], item["code"]))
    return alerts


def _attach_twins(frame: pd.DataFrame, twins: pd.DataFrame) -> None:
    grouped: dict[str, pd.DataFrame] = {
        str(district): part.sort_values("twin_rank")
        for district, part in twins.groupby("district", sort=False)
    }
    for rank in (1, 2, 3):
        names: list[str] = []
        distances: list[float] = []
        rates: list[float] = []
        for district in frame["district"].astype(str):
            part = grouped[district]
            match = part.loc[part["twin_rank"] == rank].iloc[0]
            names.append(str(match["twin"]))
            distances.append(float(match["distance"]))
            rates.append(float(match["twin_double_exclusion"]))
        frame[f"twin_{rank}"] = names
        frame[f"twin_{rank}_distance"] = distances
        frame[f"twin_{rank}_d"] = rates
    better_names: list[str] = []
    better_rates: list[float] = []
    for district in frame["district"].astype(str):
        part = grouped[district].sort_values(["twin_double_exclusion", "twin_rank"])
        better_names.append(str(part.iloc[0]["twin"]))
        better_rates.append(float(part.iloc[0]["twin_double_exclusion"]))
    frame["better_twin"] = better_names
    frame["better_twin_d"] = better_rates


def attach_model(
    frame: pd.DataFrame,
    geojson: dict,
    national: dict,
    *,
    seed: int = SEED,
    n_draws: int = N_DRAWS,
) -> tuple[pd.DataFrame, dict]:
    """Add shrinkage, ranks, typology, twins, spatial labels and alerts."""
    out = frame.copy()
    rate = out["double_exclusion_among_poor"].to_numpy(dtype=float)
    error = out["double_exclusion_among_poor_se"].to_numpy(dtype=float)
    poor = out["estimated_poor_households"].to_numpy(dtype=float)
    shrunk = empirical_bayes(rate, error)
    out["d_eb"] = shrunk.d_eb
    out["shrink"] = shrunk.shrink
    out["eb_shift_pp"] = shrunk.eb_shift_pp
    out["eb_low"] = shrunk.eb_low
    out["eb_high"] = shrunk.eb_high
    out["eb_shift_flag"] = shrunk.shift_flag
    ranks = monte_carlo_ranks(rate, error, poor, n_draws=n_draws, seed=seed)
    for column in ranks.columns:
        out[column] = ranks[column].to_numpy()
    typology = fit_typology(out, seed=seed)
    out["cluster_id"] = typology.labels
    out["cluster_name"] = typology.names
    out["pca_x"] = typology.pca_x
    out["pca_y"] = typology.pca_y
    spatial = moran_for_districts(out, geojson, seed=seed)
    out["lon"] = spatial.lon
    out["lat"] = spatial.lat
    out["lisa_quadrant"] = spatial.quadrant
    out["lisa_i"] = spatial.local_i
    out["lisa_p"] = spatial.local_p
    out["lisa_significant"] = spatial.significant
    out["lisa_label"] = spatial.label
    twins = nearest_twins(out)
    _attach_twins(out, twins)
    alerts = build_alerts(out, national)
    model = {
        "eb_mu": shrunk.mu,
        "eb_tau2": shrunk.tau2,
        "silhouette": typology.silhouette,
        "k": typology.k,
        "pca_variance": typology.pca_variance,
        "profile_z": typology.profile_z,
        "profile_raw": typology.profile_raw,
        "moran_i": spatial.moran_i,
        "moran_p": spatial.p_value,
        "moran_permutations": spatial.n_permutations,
        "twins": twins,
        "alerts": alerts,
    }
    return out, model
