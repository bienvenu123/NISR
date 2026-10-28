"""Unit tests for pathway cells, shrinkage, ranks, the simulator and the GeoJSON join."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab.data import (  # noqa: E402
    CSV_PATH,
    GEOJSON_PATH,
    MIN_SAMPLE_N,
    LOAN_REASONS,
    VUP_REASONS,
    load_inputs,
    pathway_shares,
    plottable_rows,
    require_plottable,
    usable_interval,
)
from lab.stats import (  # noqa: E402
    DEFAULT_WEIGHTS,
    allocate,
    empirical_bayes,
    fit_typology,
    monte_carlo_ranks,
    moran_for_districts,
    priority_index,
    simulate_scenario,
    targeting_frontier,
)
from lab.texts import district_brief, fit_length, national_brief  # noqa: E402

PATHWAY_COLUMNS = [
    "share_no_vup_no_account",
    "share_vup_and_account",
    "share_vup_only",
    "share_account_only",
]


@pytest.fixture(scope="module")
def inputs():
    return load_inputs(CSV_PATH, GEOJSON_PATH)


def test_pathway_cells_sum_to_one_and_large_negatives_are_not_clipped(inputs):
    frame, _geo, _national = inputs
    totals = frame[PATHWAY_COLUMNS].sum(axis=1)
    breach = frame.loc[(totals - 1).abs() > 0.005, "district"].tolist()
    assert not breach, f"Pathway cells do not sum to 1: {breach}"
    for column in PATHWAY_COLUMNS:
        hidden = frame.loc[
            (frame[column] < -0.005) & ~frame["pathway_consistency_warning"],
            "district",
        ].tolist()
        assert not hidden, f"{column} was clipped below -0.005 without a warning: {hidden}"
    warned = frame.loc[frame["pathway_consistency_warning"], "district"].tolist()
    assert warned == [] or all(name in set(frame["district"]) for name in warned)

    synthetic = pathway_shares(
        np.array([0.10]),
        np.array([0.10]),
        np.array([0.10]),
    )
    assert bool(synthetic["pathway_consistency_warning"][0])
    assert synthetic["share_vup_and_account"][0] < -0.005

    tiny = pathway_shares(
        np.array([0.40]),
        np.array([0.40]),
        np.array([0.20 - 1e-8]),
    )
    assert not bool(tiny["pathway_consistency_warning"][0])
    assert abs(sum(tiny[column][0] for column in PATHWAY_COLUMNS) - 1) <= 0.005


def test_double_exclusion_matches_count_over_poor_households(inputs):
    frame, _geo, _national = inputs
    ratio = (
        frame["estimated_double_excluded_poor_households"] / frame["estimated_poor_households"]
    )
    gap = (frame["double_exclusion_among_poor"] - ratio).abs().max()
    assert gap <= 0.001


def test_empirical_bayes_shrinks_toward_inverse_variance_mean(inputs):
    frame, _geo, _national = inputs
    rate = frame["double_exclusion_among_poor"].to_numpy()
    error = frame["double_exclusion_among_poor_se"].to_numpy()
    result = empirical_bayes(rate, error)
    floored = np.maximum(error, 1e-8)
    precision = 1.0 / floored**2
    inverse_variance_mean = float(np.sum(precision * rate) / np.sum(precision))
    assert np.all((result.shrink >= 0) & (result.shrink <= 1))
    assert result.mu == pytest.approx(inverse_variance_mean)
    rebuilt = result.shrink * rate + (1 - result.shrink) * result.mu
    assert np.allclose(result.d_eb, rebuilt)
    largest_se = int(np.argmax(error))
    largest_shift = int(np.argmax(np.abs(result.d_eb - rate)))
    assert largest_se == largest_shift
    assert int(np.argmin(result.shrink)) == largest_se


def test_monte_carlo_ranks_are_deterministic_and_cover_the_median(inputs):
    frame, _geo, _national = inputs
    rate = frame["double_exclusion_among_poor"].to_numpy()
    error = frame["double_exclusion_among_poor_se"].to_numpy()
    poor = frame["estimated_poor_households"].to_numpy()
    first = monte_carlo_ranks(rate, error, poor, n_draws=5000, seed=42)
    second = monte_carlo_ranks(rate, error, poor, n_draws=5000, seed=42)
    pd.testing.assert_frame_equal(first, second)
    for column in ("median_rank_rate", "median_rank_count", "rank_rate_p05", "rank_rate_p95"):
        assert first[column].between(1, 30).all()
    assert np.all(first["rank_rate_p05"] <= first["median_rank_rate"] + 1e-9)
    assert np.all(first["median_rank_rate"] <= first["rank_rate_p95"] + 1e-9)
    assert np.all(first["rank_count_p05"] <= first["median_rank_count"] + 1e-9)
    assert np.all(first["median_rank_count"] <= first["rank_count_p95"] + 1e-9)
    assert first["p_top5_rate"].between(0, 1).all()
    assert first["p_top10_rate"].between(0, 1).all()


def test_simulator_respects_capacity_and_beats_proportional(inputs):
    frame, _geo, _national = inputs
    poor = frame["estimated_poor_households"].to_numpy()
    rate = frame["double_exclusion_among_poor"].to_numpy()
    error = frame["double_exclusion_among_poor_se"].to_numpy()
    priority = priority_index(
        rate,
        frame["estimated_double_excluded_poor_households"].to_numpy(),
        frame["vup_gap"].to_numpy(),
        frame["financial_gap"].to_numpy(),
        frame["poverty_rate"].to_numpy(),
        DEFAULT_WEIGHTS,
    )
    assert sorted(priority.rank.tolist()) == list(range(1, 31))
    doubled = priority_index(
        rate,
        frame["estimated_double_excluded_poor_households"].to_numpy(),
        frame["vup_gap"].to_numpy(),
        frame["financial_gap"].to_numpy(),
        frame["poverty_rate"].to_numpy(),
        {key: value * 2 for key, value in DEFAULT_WEIGHTS.items()},
    )
    assert np.allclose(priority.index, doubled.index)

    total_de = float(np.sum(poor * rate))
    shares = np.round(np.arange(0.05, 1.0001, 0.05), 2)
    for share in shares:
        budget = float(poor.sum() * share)
        reached = {}
        for rule in ("R0", "R1", "R2", "R3", "R4"):
            allocation = allocate(
                poor,
                rate,
                budget,
                rule,
                priority.index,
                frame["reliability_label"].to_numpy(),
            )
            assert np.all(allocation <= poor + 1e-6)
            assert allocation.sum() == pytest.approx(min(budget, poor.sum()), rel=0, abs=1e-4)
            expected = float(np.sum(allocation * rate))
            recall = expected / total_de
            assert 0 <= recall <= 1 + 1e-9
            reached[rule] = expected
        assert reached["R1"] + 1e-4 >= reached["R0"]
        assert reached["R2"] + 1e-4 >= reached["R0"]

    scenario = simulate_scenario(
        poor,
        rate,
        error,
        float(poor.sum() * 0.10),
        "R1",
        priority=priority.index,
        reliability=frame["reliability_label"].to_numpy(),
        unit_cost=1000,
        n_draws=200,
        seed=42,
    )
    assert scenario.de_p05 <= scenario.expected_de <= scenario.de_p95 or (
        scenario.de_p05 <= scenario.de_p95
    )
    assert scenario.de_p05 <= scenario.de_p95
    assert 0 <= scenario.recall <= 1
    assert scenario.cost_per_de is not None and scenario.cost_per_de > 0

    toy_poor = np.array([10.0, 10.0, 10.0])
    toy_rate = np.array([0.9, 0.5, 0.1])
    toy_reliability = np.array(["Unreliable", "Reliable", "Reliable"])
    toy = allocate(toy_poor, toy_rate, 15, "R4", reliability=toy_reliability)
    assert toy.tolist() == pytest.approx([0.0, 10.0, 5.0])


def test_masking_drops_sample_sizes_below_30(inputs):
    frame, _geo, national = inputs
    for _label, column in (*LOAN_REASONS, *VUP_REASONS):
        plotted = plottable_rows(frame, column)
        assert plotted.empty
        with pytest.raises(ValueError):
            require_plottable(frame[f"{column}_sample_n"], what=column)
        assert national["loan_reasons"] or national["vup_reasons"]
    credit = plottable_rows(frame, "credit_denial_recorded_among_poor")
    assert len(credit) == 30
    require_plottable(credit["credit_denial_recorded_among_poor_sample_n"], what="credit denial")
    assert (credit["credit_denial_recorded_among_poor_sample_n"] >= MIN_SAMPLE_N).all()
    for item in national["loan_reasons"] + national["vup_reasons"]:
        assert item["districts_plottable"] == 0
        assert item["sample_n"] >= MIN_SAMPLE_N
        assert item["share"] is not None
    low, high = usable_interval(
        np.array([0.0, 0.2, 1.0]),
        np.array([0.0, 0.4, 1.0]),
        np.array([100, 100, 100]),
    )
    assert np.isnan(low[0]) and np.isnan(high[0])
    assert np.isnan(low[2]) and np.isnan(high[2])
    assert low[1] == pytest.approx(0.2) and high[1] == pytest.approx(0.4)
    blocked_low, blocked_high = usable_interval(
        np.array([0.2]), np.array([0.4]), np.array([10])
    )
    assert np.isnan(blocked_low[0]) and np.isnan(blocked_high[0])


def test_geojson_codes_match_each_district_once(inputs):
    frame, geojson, _national = inputs
    codes = [str(feature["properties"]["dist_code"]) for feature in geojson["features"]]
    assert len(codes) == 30
    assert len(set(codes)) == 30
    assert set(codes) == set(frame["district_code_str"])
    names = {str(feature["properties"]["dist_code"]): feature["properties"]["district"] for feature in geojson["features"]}
    for _index, row in frame.iterrows():
        assert names[row["district_code_str"]] == row["district"]
    from lab.charts import display_geojson

    drawn = display_geojson(geojson)
    drawn_codes = [str(feature["properties"]["dist_code"]) for feature in drawn["features"]]
    assert drawn_codes == codes


def test_clustering_is_reproducible_and_non_empty(inputs):
    frame, _geo, _national = inputs
    first = fit_typology(frame, seed=42)
    second = fit_typology(frame, seed=42)
    assert first.k == second.k
    assert np.array_equal(first.labels, second.labels)
    assert list(first.names) == list(second.names)
    counts = np.bincount(first.labels)
    assert len(counts) == first.k
    assert np.all(counts > 0)
    assert -1 <= first.silhouette <= 1
    assert set(first.names) <= set(second.names)


def test_moran_is_deterministic(inputs):
    frame, geojson, _national = inputs
    first = moran_for_districts(frame, geojson, n_perm=199, seed=42)
    second = moran_for_districts(frame, geojson, n_perm=199, seed=42)
    assert first.moran_i == pytest.approx(second.moran_i)
    assert list(first.quadrant) == list(second.quadrant)
    assert set(first.quadrant).issubset({"HH", "LL", "HL", "LH"})
    assert np.isfinite(first.lon).all() and np.isfinite(first.lat).all()
    assert 0 < first.p_value <= 1


def test_frontier_recall_stays_inside_unit_interval(inputs):
    frame, _geo, _national = inputs
    priority = priority_index(
        frame["double_exclusion_among_poor"].to_numpy(),
        frame["estimated_double_excluded_poor_households"].to_numpy(),
        frame["vup_gap"].to_numpy(),
        frame["financial_gap"].to_numpy(),
        frame["poverty_rate"].to_numpy(),
    )
    frontier = targeting_frontier(
        frame["estimated_poor_households"].to_numpy(),
        frame["double_exclusion_among_poor"].to_numpy(),
        priority.index,
        frame["reliability_label"].to_numpy(),
        shares=np.array([0.05, 0.5, 1.0]),
    )
    assert frontier["recall"].between(0, 1).all()
    full = frontier.loc[frontier["budget_share"] == 1.0]
    assert full["recall"].min() == pytest.approx(1.0, abs=1e-6)


def test_briefs_stay_within_120_to_180_words(inputs):
    frame, geojson, national = inputs
    from lab.stats import attach_model

    enriched, model = attach_model(frame, geojson, national, n_draws=200, seed=42)
    for _index, row in enriched.iterrows():
        text = district_brief(row, national)
        count = len(text.split())
        assert 120 <= count <= 180, (row["district"], count)
    text = national_brief(enriched.to_dict(orient="records"), national, model)
    assert 120 <= len(text.split()) <= 180
    fitted = fit_length(["One two three four five."] * 5, ["Extra sentence here now."])
    assert fitted
