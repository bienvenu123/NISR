"""Plain-language captions, alerts, briefs and methodology text.

Every sentence is a template filled with numbers computed elsewhere. This module
does not invent estimates and does not call a network service.
"""

from __future__ import annotations

from typing import Any, Mapping

LEVERS: dict[str, str] = {
    "Uncovered and unbanked": (
        "Pair VUP outreach with account opening, through a mobile-money agent or a bank agent, in the same visit."
    ),
    "Uncovered but banked": (
        "Account access is the smaller gap. Prioritise identification and enrolment into the VUP component that matches the household."
    ),
    "Covered but unbanked": (
        "VUP already reaches many poor households who still have no account. Add an account-opening step at existing VUP contact points."
    ),
    "Lower exclusion": (
        "Keep routine coverage, and use the district as a comparison for neighbours where exclusion is higher."
    ),
}

WEIGHT_LABELS: dict[str, str] = {
    "de_rate": "Double-exclusion rate",
    "de_count": "Double-excluded households",
    "vup_gap": "VUP gap",
    "financial_gap": "Financial gap",
    "poverty_rate": "Poverty rate",
}

RULE_NOTES: dict[str, str] = {
    "R0": "R0 shares the budget in proportion to each district's estimated poor households.",
    "R1": "R1 fills districts with the highest double-exclusion rate first, up to each district's poor households.",
    "R2": "R2 fills districts with the largest estimated double-excluded count first.",
    "R3": "R3 fills districts in priority-index order, using the weights set in the sidebar.",
    "R4": (
        "R4 follows the double-exclusion rate, but reliable districts are filled before "
        "districts marked interpret with caution, and unreliable districts are filled last."
    ),
}


def lever_for(cluster_name: str) -> str:
    """Policy lever for a typology name, including disambiguated suffixes."""
    for key, text in LEVERS.items():
        if str(cluster_name).startswith(key):
            return text
    return LEVERS["Lower exclusion"]


def sankey_caption(share_neither: float, largest_name: str, largest_share: float) -> str:
    """One-line reading of the pathway split."""
    neither = (
        f"{share_neither:.1%} of poor households have neither VUP nor an account"
    )
    if largest_name == "neither VUP nor an account":
        return f"The biggest leak is neither VUP nor an account ({neither})."
    return (
        f"The largest pathway state is {largest_name} ({largest_share:.1%}). "
        f"The biggest leak is neither VUP nor an account ({neither})."
    )


def simulator_contrast(rule: str, reached: float, baseline: float) -> str:
    """Compare a rule with proportional allocation at the same budget."""
    if rule == "R0":
        return (
            "R0 reaches the same number of double-excluded households as this "
            "proportional baseline, which is the reference for a random draw of "
            "poor households within districts."
        )
    gap = reached - baseline
    if gap >= 0:
        return (
            f"{rule} reaches {gap:,.0f} more double-excluded households than "
            "random (R0, proportional) for the same budget."
        )
    return (
        f"{rule} reaches {abs(gap):,.0f} fewer double-excluded households than "
        "random (R0, proportional) for the same budget."
    )


def moran_reading(moran_i: float, p_value: float) -> str:
    """Plain-language reading of global Moran's I. Exploratory, 30 districts."""
    if p_value < 0.05 and moran_i > 0:
        pattern = (
            "Districts with similar double-exclusion rates sit nearer each other "
            "than a random arrangement of the same rates."
        )
    elif p_value < 0.05 and moran_i < 0:
        pattern = "Nearby districts tend to have dissimilar double-exclusion rates."
    else:
        pattern = (
            "The global pattern is not distinguishable from a random arrangement "
            "at the 5% permutation threshold."
        )
    return (
        f"Exploratory, 30 districts. Moran's I is {moran_i:.2f} "
        f"(pseudo p-value {p_value:.3f}). {pattern}"
    )


def alert_above_national(district: str, rate: float, low: float, high: float, national: float) -> str:
    return (
        f"{district}: the double-exclusion interval ({low:.1%} to {high:.1%}) "
        f"lies entirely above the national rate of {national:.1%}. "
        f"The direct estimate is {rate:.1%}."
    )


def alert_top5(district: str, probability: float, median_rank: float) -> str:
    return (
        f"{district}: the Monte Carlo rank draws put it in the five highest "
        f"double-exclusion rates with probability {probability:.0%}. "
        f"The median rank is {median_rank:.1f}."
    )


def alert_eb_shift(district: str, shift_pp: float, direct: float, stabilised: float) -> str:
    direction = "above" if shift_pp > 0 else "below"
    return (
        f"{district}: the stabilised rate ({stabilised:.1%}) is {abs(shift_pp):.1f} "
        f"percentage points {direction} the direct estimate ({direct:.1%}). "
        "A shift above 2 percentage points means the direct rate is sensitive to sampling error."
    )


def alert_vup_below(
    district: str, rate: float, high: float, national: float
) -> str:
    return (
        f"{district}: VUP coverage among poor households is {rate:.1%}, and the "
        f"interval ends at {high:.1%}, entirely below the national share of {national:.1%}."
    )


def alert_reliability(district: str, label: str, sample_n: int, relative_se: float) -> str:
    if label == "Unreliable":
        return (
            f"{district}: the poor-household sample is {sample_n}, below 30, so the "
            "double-exclusion rate is unreliable for targeting."
        )
    return (
        f"{district}: interpret the double-exclusion rate with caution "
        f"(sample of poor households {sample_n}; relative standard error {relative_se:.0%}). "
        "Reliable estimates need a sample of at least 100 and a relative standard error of at most 30%."
    )


def alert_lisa(district: str, p_value: float) -> str:
    return (
        f"{district}: exploratory local hotspot. The district and its nearest "
        f"neighbours both have high double-exclusion rates (local Moran quadrant HH, "
        f"pseudo p-value {p_value:.3f}). This is a spatial description of 30 districts, not a boundary test."
    )


def _words(text: str) -> list[str]:
    return text.split()


def fit_length(required: list[str], optional: list[str], low: int = 120, high: int = 180) -> str:
    """Join sentences into a brief of about 120 to 180 words."""
    chosen = [sentence.strip() for sentence in required if sentence.strip()]
    text = " ".join(chosen)
    for sentence in optional:
        if len(_words(text)) >= low:
            break
        extra = sentence.strip()
        if extra:
            chosen.append(extra)
            text = " ".join(chosen)
    while len(_words(text)) > high and len(chosen) > len(required):
        chosen.pop()
        text = " ".join(chosen)
    words = _words(text)
    if len(words) > high:
        shortened = " ".join(words[:high])
        dot = shortened.rfind(".")
        if dot > 0 and len(_words(shortened[: dot + 1])) >= low:
            return shortened[: dot + 1]
        return shortened
    return text


def _pp(delta: float) -> str:
    if abs(delta) < 0.0005:
        return "in line with"
    if delta > 0:
        return f"{delta * 100:.1f} percentage points above"
    return f"{abs(delta) * 100:.1f} percentage points below"


def _wider_gap(vup_gap_vs_national: float, financial_gap_vs_national: float) -> str:
    """Say which coverage gap is further from the national share."""
    if abs(vup_gap_vs_national - financial_gap_vs_national) < 0.005:
        return "VUP coverage and account access are similarly far from the national shares"
    if vup_gap_vs_national > financial_gap_vs_national:
        return "the wider gap, relative to national coverage, is VUP rather than account access"
    return "the wider gap, relative to national coverage, is account access rather than VUP"


def district_brief(row: Mapping[str, Any], national: Mapping[str, Any]) -> str:
    """120–180 word district brief built only from computed figures."""
    district = str(row["district"])
    province = str(row.get("province") or "Rwanda")
    rate = float(row["double_exclusion_among_poor"])
    low = float(row["double_exclusion_among_poor_ci_low"])
    high = float(row["double_exclusion_among_poor_ci_high"])
    sample_n = int(row["double_exclusion_among_poor_sample_n"])
    national_rate = float(national["double_exclusion_rate"])
    count = float(row["estimated_double_excluded_poor_households"])
    vup = float(row["vup_coverage_among_poor"])
    financial = float(row["financial_access_among_poor"])
    national_vup = float(national["vup_coverage"])
    national_financial = float(national["financial_access"])
    poverty = float(row["poverty_rate"])
    national_poverty = float(national["poverty_rate"])
    cluster = str(row["cluster_name"])
    lever = lever_for(cluster)
    twin = str(row["better_twin"])
    twin_rate = float(row["better_twin_d"])
    reliability = str(row["reliability_label"])
    stabilised = float(row["d_eb"])
    shift = float(row["eb_shift_pp"])
    vup_shortfall = national_vup - vup
    finance_shortfall = national_financial - financial
    if twin_rate < rate:
        twin_sentence = (
            f"Among its three nearest districts, {twin} has the lower double-exclusion "
            f"rate, at {twin_rate:.1%}, so it is a similar district that does better on this measure."
        )
    else:
        twin_sentence = (
            f"Among its three nearest districts, {twin} has the lowest double-exclusion "
            f"rate, at {twin_rate:.1%}. That neighbour does not undercut {district}; "
            "the comparison still shows which similar district is closest to a lower rate."
        )
    required = [
        (
            f"{district} district in {province} has a double-exclusion rate of {rate:.1%} "
            f"among poor households. The approximate 95% interval runs from {low:.1%} to "
            f"{high:.1%}, based on {sample_n} sampled poor households."
        ),
        (
            f"That rate is {_pp(rate - national_rate)} the national rate of {national_rate:.1%}, "
            f"which is weighted by estimated poor households. About {count:,.0f} poor households "
            "are estimated to have neither a VUP participation flag nor a bank or mobile-money account."
        ),
        (
            f"VUP coverage among poor households is {vup:.1%}, against {national_vup:.1%} nationally. "
            f"Bank or mobile-money access is {financial:.1%}, against {national_financial:.1%} nationally. "
            f"On those two comparisons, {_wider_gap(vup_shortfall, finance_shortfall)}."
        ),
        (
            f"The typology label is {cluster}. The suggested lever is: {lever}"
        ),
        twin_sentence,
        (
            f"The reliability label is {reliability}. The stabilised double-exclusion rate is "
            f"{stabilised:.1%}, which differs from the direct estimate by {shift:+.1f} percentage points."
        ),
        (
            "These are district estimates from EICV7, with fieldwork from October 2023 to October 2024. "
            "They support local follow-up. They do not identify individual households and they are not eligibility decisions."
        ),
    ]
    optional = [
        (
            f"Poverty is {poverty:.1%} of the population, {_pp(poverty - national_poverty)} "
            f"the national poverty rate of {national_poverty:.1%}."
        ),
        (
            "A high rate can sit in a smaller district, and a moderate rate can still mean many households, so the count and the rate answer different questions."
        ),
        (
            "The nearest-district comparison is descriptive. It does not show that a programme caused the difference."
        ),
    ]
    return fit_length(required, optional)


def district_insight(row: Mapping[str, Any], national: Mapping[str, Any]) -> str:
    """Short profile paragraph for the district explorer."""
    district = str(row["district"])
    rate = float(row["double_exclusion_among_poor"])
    national_rate = float(national["double_exclusion_rate"])
    vup = float(row["vup_coverage_among_poor"])
    financial = float(row["financial_access_among_poor"])
    count = float(row["estimated_double_excluded_poor_households"])
    cluster = str(row["cluster_name"])
    twin = str(row["better_twin"])
    twin_rate = float(row["better_twin_d"])
    comparison = "above" if rate >= national_rate else "below"
    gap = _wider_gap(float(national["vup_coverage"]) - vup, float(national["financial_access"]) - financial)
    if twin_rate < rate:
        twin_clause = f"{twin} is a similar district with a lower rate ({twin_rate:.1%})."
    else:
        twin_clause = (
            f"None of its three nearest districts has a lower rate; "
            f"{twin} is the lowest among them, at {twin_rate:.1%}."
        )
    return (
        f"{district}’s double-exclusion rate is {rate:.1%}, {comparison} the national "
        f"{national_rate:.1%}, or about {count:,.0f} poor households. {gap[0].upper() + gap[1:]}. "
        f"The district sits in “{cluster}”. {twin_clause} "
        f"Read the {row['reliability_label'].lower()} label before using the rate for follow-up."
    )


def national_brief(
    frame_records: list[Mapping[str, Any]],
    national: Mapping[str, Any],
    model: Mapping[str, Any],
) -> str:
    """120–180 word national brief built only from computed figures."""
    highest_rate = max(frame_records, key=lambda row: float(row["double_exclusion_among_poor"]))
    highest_count = max(
        frame_records,
        key=lambda row: float(row["estimated_double_excluded_poor_households"]),
    )
    names = [str(row["cluster_name"]) for row in frame_records]
    largest_cluster = max(set(names), key=names.count)
    cluster_n = names.count(largest_cluster)
    required = [
        (
            f"Across 30 districts, {national['double_exclusion_rate']:.1%} of poor households "
            f"are estimated to have neither VUP participation nor a bank or mobile-money account. "
            f"That is about {national['double_excluded_households']:,.0f} poor households, "
            f"out of {national['poor_households']:,.0f} poor households."
        ),
        (
            f"The population poverty rate is {national['poverty_rate']:.1%}. "
            f"Among poor households, VUP coverage is {national['vup_coverage']:.1%} and "
            f"bank or mobile-money access is {national['financial_access']:.1%}. "
            f"The neither-pathway share is {national['share_no_vup_no_account']:.1%}."
        ),
        (
            f"The highest double-exclusion rate is in {highest_rate['district']} "
            f"({float(highest_rate['double_exclusion_among_poor']):.1%}). "
            f"The largest estimated count is in {highest_count['district']} "
            f"({float(highest_count['estimated_double_excluded_poor_households']):,.0f} households)."
        ),
        (
            f"{national['n_reliable']} districts are labelled reliable and "
            f"{national['n_caution']} are marked interpret with caution, because the sample "
            "of poor households is under 100 or the relative standard error is above 30%. "
            f"{national['n_unreliable']} districts fall below the unreliable threshold of 30."
        ),
        (
            f"The largest typology group is {largest_cluster}, with {cluster_n} districts. "
            f"The suggested lever for that type is: {lever_for(largest_cluster)}"
        ),
        (
            "This briefing uses district aggregates from EICV7 only. Fieldwork ran from "
            "October 2023 to October 2024. It is an illustrative decision-support summary, "
            "not a list of eligible households."
        ),
    ]
    optional = [
        moran_reading(float(model["moran_i"]), float(model["moran_p"])),
        (
            "Rank intervals elsewhere in the lab show where a district's position would move if each rate were redrawn from its standard error."
        ),
    ]
    return fit_length(required, optional)


def methodology_sections(warning_districts: list[str]) -> list[tuple[str, str]]:
    """Expander title and markdown for the methodology tab."""
    if warning_districts:
        warning_text = (
            "Pathway consistency warning for: "
            + ", ".join(warning_districts)
            + ". A warning means a pathway cell is below -0.005 or the four cells miss 1 by more than 0.005. Values only slightly below zero are clipped to zero; larger negatives are left in place."
        )
    else:
        warning_text = (
            "No district breached the pathway check. For all 30 districts the four cells sum to 1 within 0.005, and no cell is below -0.005. Tiny negatives above -0.005 would be clipped to zero; none of those clips was required to hide a breach."
        )
    return [
        (
            "Definitions",
            """
**Poor.** An EICV7 household classified as poor. District poverty rates use population weights. The national poverty rate on this page is the sum of estimated poor population divided by the sum of estimated population, the same construction as the main dashboard.

**Social protection.** VUP coverage among poor households: a positive participation flag in the VUP modules that were available when the district file was built. It is not an eligibility decision and it does not include every social-protection instrument outside those modules.

**Financial access.** At least one household member reports a bank account or a mobile-money account. Tontine participation is kept as a separate column. The broader “financial or tontine” share is also in the file and is not used as the double-exclusion definition.

**Double exclusion.** Among poor households, neither the VUP flag nor a bank or mobile-money account. The national rate is the sum of estimated double-excluded poor households divided by the sum of estimated poor households.
            """.strip(),
        ),
        (
            "Pathway formulas",
            """
Let `v` be VUP coverage among poor households, `f` bank or mobile-money access among poor households, and `d` the double-exclusion rate. `P` is estimated poor households. The four cells use only these marginals. They do not assume independence:

- Neither VUP nor account = `d`
- VUP and account = `v + f + d - 1`
- VUP only = `v - (v + f + d - 1)`
- Account only = `f - (v + f + d - 1)`

Household counts are the share times `P`. A cell in the open interval (-0.005, 0) is clipped to 0. A cell below -0.005, or a set of four cells that misses 1 by more than 0.005, raises `pathway_consistency_warning`. That warning is reported below and is not dropped from the chart data.
            """.strip()
            + "\n\n"
            + warning_text,
        ),
        (
            "Empirical Bayes shrinkage",
            """
The direct district rate is `d_i` with standard error `s_i`. Standard errors of 0 are floored at a small epsilon before weighting. The prior mean `mu` is the inverse-variance weighted mean of the district rates. The prior variance is `tau² = max(variance of d with ddof 1 − mean of s², 1e-6)`. The shrinkage factor is `tau² / (tau² + s_i²)`, which lies in [0, 1]. The stabilised rate is `shrink_i * d_i + (1 - shrink_i) * mu`. An approximate interval uses the posterior standard deviation `s_i * sqrt(shrink_i)` and a normal 1.96 multiplier, then clips to [0, 1]. `eb_shift_pp` is the stabilised rate minus the direct rate, in percentage points, and is flagged when the absolute shift exceeds 2.
            """.strip(),
        ),
        (
            "Monte Carlo ranks",
            """
Each district rate is redrawn 5,000 times from a normal distribution with its published mean and standard error, clipped to [0, 1], with NumPy’s Generator seeded at 42. Counts are the draw times estimated poor households. Rank 1 is the highest rate, or the highest count. The chart shows the median rank and the 5th to 95th percentiles. P(top 5) and P(top 10) are the share of draws in which the district’s rank is 5 or better, or 10 or better. A rank of 1 is firm only when that interval is narrow.
            """.strip(),
        ),
        (
            "Priority index and the simulator",
            """
The priority index is a weighted sum of population z-scores (standard deviation with divisor n) of the double-exclusion rate, the double-excluded count, the VUP gap `1 - v`, the financial gap `1 - f`, and the poverty rate. Default weights are 0.35, 0.35, 0.10, 0.10 and 0.10. Sidebar weights are rescaled so they sum to 1. The sensitivity table rebuilds the top 10 after moving one weight by +50% or -50% and rescaling again. “Top 10 replaced” counts districts that leave the original top 10.

The simulator allocates a budget `B` of poor households. Inside a district the selected households are treated as a random draw, so expected double-excluded households in district `i` equal `allocation_i * d_i`, and `allocation_i` never exceeds `P_i`. R0 is proportional to `P_i`. R1 fills the highest rate first. R2 fills the highest count first. R3 follows the priority index. R4 follows the rate, but reliable districts are filled before “interpret with caution”, and unreliable districts (sample below 30) are filled last. Recall is expected double-excluded households divided by all double-excluded households. Precision is expected double-excluded households divided by `B`. The 90% interval redraws `d` from its standard error and holds the allocation fixed. The frontier repeats the point-estimate rules for budgets from 5% to 100% of poor households. Optional unit cost is RWF per poor household reached; cost per double-excluded household is that unit cost times `B`, divided by expected double-excluded households.
            """.strip(),
        ),
        (
            "Typology, twins and Moran's I",
            """
KMeans uses a fixed seed of 42 and 10 initialisations. Features, after standardisation, are the poverty rate, the VUP gap, the financial gap, the double-exclusion rate, and the log of estimated poor households. K is chosen in {3, 4, 5} by the highest silhouette score; ties keep the smaller k. Cluster names come from the signs of the standardised VUP-gap and financial-gap centroids: uncovered and unbanked, uncovered but banked, covered but unbanked, or lower exclusion. Duplicate names are split by the centroid double-exclusion rate.

Twins use those features plus extreme poverty and tontine participation, standardised on their own, and Euclidean distance. Each district is matched to its three nearest neighbours. The better-performing twin is the neighbour with the lowest double-exclusion rate.

Spatial results are exploratory for 30 districts. Centroids are the average of exterior-ring vertices. Neighbours are the five nearest centroids under an equirectangular scaling of longitude. Weights are row-standardised. Global Moran’s I uses centred rates and 999 permutations (seed 42); the pseudo p-value is `(1 + count of |I_perm| at least |I|) / 1000`. Local Moran uses `z_i` times the lagged `z`, with conditional permutations that hold `z_i` fixed. Quadrants are HH, LL, HL and LH. A map class of “Not significant” means the local pseudo p-value is 0.05 or higher.
            """.strip(),
        ),
        (
            "Masking, reliability and the published poverty check",
            """
Any indicator whose own `_sample_n` is below 30 is shown as “n too small” and is not plotted. Intervals that collapse to [0, 0] or [1, 1] are not drawn as error bars. Loan-denial reasons and VUP direct-support reasons are recorded on small district samples; district bars are omitted. A national bar is shown only when the sum of recorded cases is at least 30, and it is weighted by those recorded cases. That pool is not a substitute for a district estimate.

Reliability is recomputed and does not use the often-empty `reliability_flag` column. Reliable means a double-exclusion sample of at least 100 and a relative standard error of at most 0.30. Sample size below 30 is unreliable. Other districts are “interpret with caution”.

The validation table compares each district poverty rate with `published_poverty_rate_pct` and shows `poverty_rate_difference_pp` from the file (estimated percent minus the published percent).
            """.strip(),
        ),
        (
            "Limitations, sources and AI use",
            """
The protection measure in this file is VUP participation, not the full social-protection system. Samples for some districts, and for almost all denial and direct-support reasons, are small. Intervals are the file’s approximate 95% intervals. Correlations and clusters describe districts, not people: ecological patterns are not individual behaviour. The survey is cross-sectional. Fieldwork ran from October 2023 to October 2024. Nothing here establishes programme impact, eligibility, or why a household has no account.

Sources: district aggregates in `outputs/eicv7_district_double_exclusion.csv`; boundaries in `data/rwanda_districts.geojson` (`dist_code` joined to `district_code`). NISR publishes the survey metadata at the [EICV7 microdata catalog](https://microdata.statistics.gov.rw/index.php/catalog/119) and the [EICV7 poverty profile](https://statistics.gov.rw/sites/default/files/documents/2025-07/EICV7_Poverty%20Profile.pdf). The institutional site is [NISR](https://www.statistics.gov.rw/).

**AI-use disclosure.** AI tools were used to help write code and documentation. Every number on these pages is computed from the EICV7 district aggregates. An optional language-model rewrite of the template brief is off unless a `LAB_LLM_API_KEY` secret is present and the checkbox is turned on. That rewrite, if used, is labelled “AI-generated, verify before use” and is sent only the aggregated numbers in the brief.
            """.strip(),
        ),
    ]


CAPTIONS: dict[str, str] = {
    "sankey": "What this means: follow poor households into VUP or not, then into an account or not. The four end states are the pathway cells.",
    "funnel": "What this means: each bar is a smaller group than the one above it, from all poor households down to those with neither VUP nor an account.",
    "population": "What this means: this panel is people, not households. It shows how many people are in poverty before the household pathway begins.",
    "stacked": "What this means: every district’s poor households are split into the same four states, so the bars are comparable even when districts differ in size.",
    "quadrant": "What this means: the lower-left has less VUP coverage and less account access among poor households. Bubble size is estimated poor households; colour is the double-exclusion rate.",
    "caterpillar": "What this means: the dot is the direct rate and the bar is the approximate 95% interval. Districts whose bars cross the national line are not cleanly above or below it.",
    "ranks": "What this means: rank 1 is only firm when the interval is narrow. A wide bar means sampling error could reorder the district.",
    "priority": "What this means: each coloured piece is one weighted z-score. The total length is the priority index, and a piece left of zero pulls the index down.",
    "sensitivity": "What this means: a larger count means the top 10 changes when that one weight moves by half and the weights are rescaled.",
    "simulator": "What this means: these cards are expected results if poor households inside a chosen district are drawn at random, not a list of people.",
    "allocation": "What this means: darker districts receive more of the budget. A district cannot be allocated more poor households than it is estimated to have.",
    "frontier": "What this means: a rule that stays above the others reaches a larger share of double-excluded households at the same budget.",
    "rules": "What this means: recall is the share of all double-excluded households the rule expects to reach; precision is that number divided by the budget.",
    "map": "What this means: each district is shaded by the selected measure. The map is a description of survey estimates, not a targeting boundary.",
    "moran": "What this means: Moran’s I summarises whether similar rates sit next to each other. With 30 districts this is exploratory.",
    "dumbbell": "What this means: the line joins the direct rate to the stabilised rate. Amber marks a shift of more than 2 percentage points.",
    "typology": "What this means: districts close together on this plane have similar standardised profiles. Colour is the cluster name, not a rank.",
    "heatmap": "What this means: a positive cell is above the 30-district average on that standardised indicator.",
    "twins": "What this means: a positive gap means this district is higher than the twin. For double exclusion and poverty, higher is a larger burden.",
    "radar": "What this means: further from the centre is a higher rate. For VUP and account access that is broader reach; for poverty and double exclusion it is a larger share.",
    "correlation": "What this means: this is an ecological correlation across 30 districts, not a correlation across households or people.",
    "parallel": "What this means: each line is a district. Lines that stay together have similar profiles on the selected indicators.",
    "reasons": "What this means: these are reasons recorded among people who reported a denial or a direct-support enrolment, not causes of having no account.",
    "credit": "What this means: this is the share of poor households with a denied loan recorded, not the denial rate among applicants.",
    "alerts": "What this means: a card fires only when a pre-set rule is met. It is a prompt to look at the estimate, not a finding of programme failure.",
}
