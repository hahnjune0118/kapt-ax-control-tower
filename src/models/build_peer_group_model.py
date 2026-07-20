from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

COHORT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "pilot_cohort.csv"
)

ANNUAL_COST_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "fact_apartment_cost_annual.csv"
)

PEER_WEIGHT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "model_peer_weights.csv"
)

EXPECTED_RANGE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "model_expected_cost_range.csv"
)

MODEL_SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "model_peer_group_summary.csv"
)

MODEL_CARD_FILE = (
    PROJECT_ROOT
    / "docs"
    / "model_cards"
    / "peer_group_model.md"
)


MODEL_VERSION = "peer-group-v1.0"
MIN_SELECTED_PEERS = 15
MAX_SELECTED_PEERS = 30
MIN_RANGE_PEERS = 10
MIN_EFFECTIVE_SAMPLE_SIZE = 5


SIMILARITY_WEIGHTS = {
    "household_count": 0.25,
    "approval_year": 0.20,
    "management_area_per_household": 0.15,
    "building_count": 0.10,
    "city_district": 0.10,
    "heating_type": 0.08,
    "management_type": 0.07,
    "hall_type": 0.03,
    "sale_type": 0.02,
}


def is_present(value: Any) -> bool:
    if value is None:
        return False

    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass

    return str(value).strip() != ""


def relative_similarity(
    target_value: Any,
    peer_value: Any,
    tolerance_ratio: float,
) -> float | None:
    if (
        not is_present(target_value)
        or not is_present(peer_value)
    ):
        return None

    target_number = float(target_value)
    peer_number = float(peer_value)

    denominator = max(abs(target_number), 1.0)

    difference_ratio = (
        abs(peer_number - target_number)
        / denominator
    )

    similarity = (
        1
        - difference_ratio / tolerance_ratio
    )

    return float(
        min(max(similarity, 0), 1)
    )


def absolute_similarity(
    target_value: Any,
    peer_value: Any,
    tolerance: float,
) -> float | None:
    if (
        not is_present(target_value)
        or not is_present(peer_value)
    ):
        return None

    difference = abs(
        float(peer_value) - float(target_value)
    )

    similarity = 1 - difference / tolerance

    return float(
        min(max(similarity, 0), 1)
    )


def categorical_similarity(
    target_value: Any,
    peer_value: Any,
) -> float | None:
    if (
        not is_present(target_value)
        or not is_present(peer_value)
    ):
        return None

    return float(
        str(target_value).strip()
        == str(peer_value).strip()
    )


def weighted_quantile(
    values: pd.Series,
    weights: pd.Series,
    quantile: float,
) -> float | None:
    valid_mask = (
        values.notna()
        & weights.notna()
        & weights.gt(0)
    )

    valid_values = (
        values.loc[valid_mask]
        .astype(float)
        .to_numpy()
    )

    valid_weights = (
        weights.loc[valid_mask]
        .astype(float)
        .to_numpy()
    )

    if len(valid_values) == 0:
        return None

    order = np.argsort(valid_values)

    sorted_values = valid_values[order]
    sorted_weights = valid_weights[order]

    cumulative_weights = np.cumsum(
        sorted_weights
    )

    cutoff = quantile * sorted_weights.sum()

    position = int(
        np.searchsorted(
            cumulative_weights,
            cutoff,
            side="left",
        )
    )

    position = min(
        position,
        len(sorted_values) - 1,
    )

    return float(sorted_values[position])


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    if not COHORT_FILE.exists():
        raise FileNotFoundError(
            f"파일럿 비교군 파일이 없습니다: {COHORT_FILE}"
        )

    if not ANNUAL_COST_FILE.exists():
        raise FileNotFoundError(
            f"연간 관리비 피처가 없습니다: {ANNUAL_COST_FILE}"
        )

    cohort = pd.read_csv(
        COHORT_FILE,
        dtype={
            "apartment_id": "string",
            "cohort_role": "string",
        },
    )

    annual = pd.read_csv(
        ANNUAL_COST_FILE,
        dtype={
            "apartment_id": "string",
            "cohort_role": "string",
            "cost_category": "string",
        },
    )

    required_cohort_columns = {
        "apartment_id",
        "apartment_name",
        "cohort_role",
        "household_count",
        "approval_year",
        "management_area_m2",
    }

    missing_cohort_columns = (
        required_cohort_columns
        - set(cohort.columns)
    )

    if missing_cohort_columns:
        raise ValueError(
            f"비교군 필수 칼럼이 없습니다: "
            f"{sorted(missing_cohort_columns)}"
        )

    required_annual_columns = {
        "apartment_id",
        "cohort_role",
        "cost_category",
        "cost_category_name_ko",
        "coverage_pct",
        "annualized_cost_per_household_krw",
    }

    missing_annual_columns = (
        required_annual_columns
        - set(annual.columns)
    )

    if missing_annual_columns:
        raise ValueError(
            f"연간 피처 필수 칼럼이 없습니다: "
            f"{sorted(missing_annual_columns)}"
        )

    optional_columns = [
        "building_count",
        "city_district",
        "heating_type",
        "management_type",
        "hall_type",
        "sale_type",
    ]

    for column in optional_columns:
        if column not in cohort.columns:
            cohort[column] = pd.NA

    cohort["apartment_id"] = (
        cohort["apartment_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    annual["apartment_id"] = (
        annual["apartment_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    cohort["cohort_role"] = (
        cohort["cohort_role"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    annual["cohort_role"] = (
        annual["cohort_role"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    numeric_profile_columns = [
        "household_count",
        "approval_year",
        "management_area_m2",
        "building_count",
    ]

    for column in numeric_profile_columns:
        cohort[column] = pd.to_numeric(
            cohort[column],
            errors="coerce",
        )

    annual["coverage_pct"] = pd.to_numeric(
        annual["coverage_pct"],
        errors="coerce",
    )

    annual[
        "annualized_cost_per_household_krw"
    ] = pd.to_numeric(
        annual[
            "annualized_cost_per_household_krw"
        ],
        errors="coerce",
    )

    cohort[
        "management_area_per_household_m2"
    ] = (
        cohort["management_area_m2"]
        .div(cohort["household_count"])
        .where(cohort["household_count"].gt(0))
    )

    target_count = int(
        cohort["cohort_role"].eq("TARGET").sum()
    )

    peer_count = int(
        cohort["cohort_role"].eq("PEER").sum()
    )

    if target_count != 1:
        raise ValueError(
            f"TARGET이 정확히 1개가 아닙니다: {target_count}"
        )

    if peer_count != 49:
        raise ValueError(
            f"PEER가 49개가 아닙니다: {peer_count}"
        )

    return cohort, annual


def build_cost_coverage(
    annual: pd.DataFrame,
) -> pd.DataFrame:
    coverage = (
        annual.groupby(
            "apartment_id",
            as_index=False,
        )
        .agg(
            cost_data_coverage_pct=(
                "coverage_pct",
                "mean",
            ),
            valid_cost_category_count=(
                "annualized_cost_per_household_krw",
                "count",
            ),
        )
    )

    coverage["cost_data_coverage_pct"] = (
        coverage["cost_data_coverage_pct"]
        .fillna(0)
        .clip(lower=0, upper=100)
    )

    return coverage


def build_peer_scores(
    cohort: pd.DataFrame,
    annual: pd.DataFrame,
) -> pd.DataFrame:
    target = cohort.loc[
        cohort["cohort_role"].eq("TARGET")
    ].iloc[0]

    peers = cohort.loc[
        cohort["cohort_role"].eq("PEER")
    ].copy()

    cost_coverage = build_cost_coverage(annual)

    peers = peers.merge(
        cost_coverage,
        on="apartment_id",
        how="left",
        validate="one_to_one",
    )

    peers["cost_data_coverage_pct"] = (
        peers["cost_data_coverage_pct"]
        .fillna(0)
    )

    peers["valid_cost_category_count"] = (
        peers["valid_cost_category_count"]
        .fillna(0)
        .astype(int)
    )

    score_rows: list[dict[str, Any]] = []

    for _, peer in peers.iterrows():
        component_scores = {
            "household_count": relative_similarity(
                target["household_count"],
                peer["household_count"],
                tolerance_ratio=1.0,
            ),
            "approval_year": absolute_similarity(
                target["approval_year"],
                peer["approval_year"],
                tolerance=20,
            ),
            "management_area_per_household": (
                relative_similarity(
                    target[
                        "management_area_per_household_m2"
                    ],
                    peer[
                        "management_area_per_household_m2"
                    ],
                    tolerance_ratio=1.0,
                )
            ),
            "building_count": relative_similarity(
                target["building_count"],
                peer["building_count"],
                tolerance_ratio=1.5,
            ),
            "city_district": categorical_similarity(
                target["city_district"],
                peer["city_district"],
            ),
            "heating_type": categorical_similarity(
                target["heating_type"],
                peer["heating_type"],
            ),
            "management_type": categorical_similarity(
                target["management_type"],
                peer["management_type"],
            ),
            "hall_type": categorical_similarity(
                target["hall_type"],
                peer["hall_type"],
            ),
            "sale_type": categorical_similarity(
                target["sale_type"],
                peer["sale_type"],
            ),
        }

        available_weight = 0.0
        weighted_similarity = 0.0

        output_components: dict[str, Any] = {}

        for component, component_score in (
            component_scores.items()
        ):
            weight = SIMILARITY_WEIGHTS[component]

            if component_score is not None:
                available_weight += weight
                weighted_similarity += (
                    component_score * weight
                )

                output_components[
                    f"{component}_similarity_pct"
                ] = round(
                    component_score * 100,
                    2,
                )
            else:
                output_components[
                    f"{component}_similarity_pct"
                ] = None

        if available_weight > 0:
            structural_similarity = (
                weighted_similarity
                / available_weight
                * 100
            )
        else:
            structural_similarity = 0.0

        evidence_coverage_pct = (
            available_weight * 100
        )

        evidence_factor = min(
            evidence_coverage_pct / 80,
            1,
        )

        peer_suitability_score = (
            structural_similarity * 0.8
            + float(
                peer["cost_data_coverage_pct"]
            ) * 0.2
        ) * evidence_factor

        score_rows.append(
            {
                "model_version": MODEL_VERSION,
                "target_apartment_id": target[
                    "apartment_id"
                ],
                "target_apartment_name": target[
                    "apartment_name"
                ],
                "apartment_id": peer[
                    "apartment_id"
                ],
                "apartment_name": peer[
                    "apartment_name"
                ],
                "city_district": peer[
                    "city_district"
                ],
                "household_count": peer[
                    "household_count"
                ],
                "approval_year": peer[
                    "approval_year"
                ],
                "heating_type": peer[
                    "heating_type"
                ],
                "management_type": peer[
                    "management_type"
                ],
                "structural_similarity_score": round(
                    structural_similarity,
                    2,
                ),
                "similarity_evidence_coverage_pct": round(
                    evidence_coverage_pct,
                    2,
                ),
                "cost_data_coverage_pct": round(
                    float(
                        peer[
                            "cost_data_coverage_pct"
                        ]
                    ),
                    2,
                ),
                "valid_cost_category_count": int(
                    peer[
                        "valid_cost_category_count"
                    ]
                ),
                "peer_suitability_score": round(
                    peer_suitability_score,
                    2,
                ),
                **output_components,
            }
        )

    scores = pd.DataFrame(score_rows).sort_values(
        by=[
            "peer_suitability_score",
            "structural_similarity_score",
            "apartment_id",
        ],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    scores.insert(
        0,
        "peer_rank",
        range(1, len(scores) + 1),
    )

    scores["peer_group_class"] = "EXCLUDED"

    core_mask = (
        scores["peer_suitability_score"].ge(75)
        & scores[
            "similarity_evidence_coverage_pct"
        ].ge(80)
        & scores["cost_data_coverage_pct"].ge(75)
    )

    supporting_mask = (
        scores["peer_suitability_score"].ge(60)
        & scores["cost_data_coverage_pct"].ge(75)
        & ~core_mask
    )

    scores.loc[
        core_mask,
        "peer_group_class",
    ] = "CORE"

    scores.loc[
        supporting_mask,
        "peer_group_class",
    ] = "SUPPORTING"

    eligible_indices = scores.index[
        scores["peer_group_class"].isin(
            ["CORE", "SUPPORTING"]
        )
    ].tolist()[:MAX_SELECTED_PEERS]

    selection_policy = "THRESHOLD"

    if len(eligible_indices) < MIN_SELECTED_PEERS:
        eligible_indices = scores.index[
            :MIN_SELECTED_PEERS
        ].tolist()
        selection_policy = "FALLBACK_TOP15"

    scores["model_selected"] = False
    scores.loc[
        eligible_indices,
        "model_selected",
    ] = True

    scores["selection_policy"] = (
        "NOT_SELECTED"
    )

    scores.loc[
        scores["model_selected"],
        "selection_policy",
    ] = selection_policy

    scores["raw_model_weight"] = 0.0

    selected_mask = scores["model_selected"]

    scores.loc[
        selected_mask,
        "raw_model_weight",
    ] = (
        scores.loc[
            selected_mask,
            "peer_suitability_score",
        ]
        .div(100)
        .pow(2)
        .mul(
            scores.loc[
                selected_mask,
                "cost_data_coverage_pct",
            ].div(100)
        )
    )

    total_raw_weight = scores.loc[
        selected_mask,
        "raw_model_weight",
    ].sum()

    if total_raw_weight <= 0:
        raise RuntimeError(
            "비교단지 모델 가중치를 계산할 수 없습니다."
        )

    scores["model_weight"] = 0.0

    scores.loc[
        selected_mask,
        "model_weight",
    ] = (
        scores.loc[
            selected_mask,
            "raw_model_weight",
        ]
        / total_raw_weight
    )

    scores["model_weight"] = (
        scores["model_weight"].round(8)
    )

    return scores


def build_expected_ranges(
    cohort: pd.DataFrame,
    annual: pd.DataFrame,
    peer_scores: pd.DataFrame,
) -> pd.DataFrame:
    target_profile = cohort.loc[
        cohort["cohort_role"].eq("TARGET")
    ].iloc[0]

    target_annual = annual.loc[
        annual["cohort_role"].eq("TARGET")
    ].copy()

    peer_annual = annual.loc[
        annual["cohort_role"].eq("PEER")
    ].copy()

    peer_annual = peer_annual.merge(
        peer_scores[
            [
                "apartment_id",
                "model_selected",
                "model_weight",
                "peer_suitability_score",
            ]
        ],
        on="apartment_id",
        how="left",
        validate="many_to_one",
    )

    output_rows: list[dict[str, Any]] = []

    for _, target in target_annual.iterrows():
        category = target["cost_category"]

        pool = peer_annual.loc[
            peer_annual["cost_category"].eq(category)
            & peer_annual["model_selected"].eq(True)
            & peer_annual[
                "annualized_cost_per_household_krw"
            ].notna()
            & peer_annual["model_weight"].gt(0)
        ].copy()

        peer_count = len(pool)

        available_weight = float(
            pool["model_weight"].sum()
        )

        if available_weight > 0:
            pool["category_model_weight"] = (
                pool["model_weight"]
                / available_weight
            )
        else:
            pool["category_model_weight"] = 0.0

        values = pool[
            "annualized_cost_per_household_krw"
        ]

        weights = pool["category_model_weight"]

        expected_low = weighted_quantile(
            values,
            weights,
            0.25,
        )

        expected_median = weighted_quantile(
            values,
            weights,
            0.50,
        )

        expected_high = weighted_quantile(
            values,
            weights,
            0.75,
        )

        if peer_count > 0:
            expected_mean = float(
                np.average(
                    values.astype(float),
                    weights=weights.astype(float),
                )
            )

            effective_sample_size = float(
                1
                / np.square(
                    weights.astype(float)
                ).sum()
            )
        else:
            expected_mean = None
            effective_sample_size = 0.0

        if (
            peer_count >= MIN_RANGE_PEERS
            and effective_sample_size
            >= MIN_EFFECTIVE_SAMPLE_SIZE
        ):
            model_status = "MODEL_READY"
        else:
            model_status = "INSUFFICIENT_PEERS"

        target_value = target[
            "annualized_cost_per_household_krw"
        ]

        if (
            model_status == "MODEL_READY"
            and pd.notna(target_value)
            and expected_median is not None
            and expected_median != 0
        ):
            gap_per_household = float(
                target_value - expected_median
            )

            gap_pct = float(
                gap_per_household
                / expected_median
                * 100
            )

            indicative_excess_cost = (
                max(gap_per_household, 0)
                * float(
                    target_profile[
                        "household_count"
                    ]
                )
            )

            if (
                expected_high is not None
                and target_value > expected_high
            ):
                range_position = (
                    "ABOVE_EXPECTED_RANGE"
                )
            elif (
                expected_low is not None
                and target_value < expected_low
            ):
                range_position = (
                    "BELOW_EXPECTED_RANGE"
                )
            else:
                range_position = (
                    "WITHIN_EXPECTED_RANGE"
                )
        else:
            gap_per_household = None
            gap_pct = None
            indicative_excess_cost = None
            range_position = "NOT_ASSESSED"

        target_household_count = float(
            target_profile["household_count"]
        )

        if expected_low is not None:
            expected_low_total = (
                expected_low
                * target_household_count
            )
        else:
            expected_low_total = None

        if expected_median is not None:
            expected_median_total = (
                expected_median
                * target_household_count
            )
        else:
            expected_median_total = None

        if expected_high is not None:
            expected_high_total = (
                expected_high
                * target_household_count
            )
        else:
            expected_high_total = None

        if (
            model_status == "MODEL_READY"
            and peer_count >= 20
            and effective_sample_size >= 10
            and available_weight >= 0.8
        ):
            confidence_level = "HIGH"
        elif model_status == "MODEL_READY":
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"

        output_rows.append(
            {
                "model_version": MODEL_VERSION,
                "apartment_id": target[
                    "apartment_id"
                ],
                "apartment_name": target[
                    "apartment_name"
                ],
                "cost_category": category,
                "cost_category_name_ko": target[
                    "cost_category_name_ko"
                ],
                "model_peer_count": peer_count,
                "effective_sample_size": round(
                    effective_sample_size,
                    2,
                ),
                "available_model_weight_pct": round(
                    available_weight * 100,
                    2,
                ),
                "target_annualized_cost_per_household_krw": (
                    target_value
                ),
                "expected_low_cost_per_household_krw": (
                    expected_low
                ),
                "expected_median_cost_per_household_krw": (
                    expected_median
                ),
                "expected_high_cost_per_household_krw": (
                    expected_high
                ),
                "expected_mean_cost_per_household_krw": (
                    expected_mean
                ),
                "target_gap_per_household_krw": (
                    gap_per_household
                ),
                "target_gap_pct": gap_pct,
                "target_range_position": range_position,
                "expected_low_total_cost_krw": (
                    expected_low_total
                ),
                "expected_median_total_cost_krw": (
                    expected_median_total
                ),
                "expected_high_total_cost_krw": (
                    expected_high_total
                ),
                "indicative_annual_excess_cost_krw": (
                    indicative_excess_cost
                ),
                "confidence_level": confidence_level,
                "model_status": model_status,
            }
        )

    return pd.DataFrame(output_rows).sort_values(
        by="cost_category"
    ).reset_index(drop=True)


def create_model_summary(
    cohort: pd.DataFrame,
    peer_scores: pd.DataFrame,
    expected_ranges: pd.DataFrame,
) -> pd.DataFrame:
    target = cohort.loc[
        cohort["cohort_role"].eq("TARGET")
    ].iloc[0]

    selected = peer_scores.loc[
        peer_scores["model_selected"]
    ]

    effective_sample_size = float(
        1
        / np.square(
            selected["model_weight"].astype(float)
        ).sum()
    )

    weighted_similarity = float(
        np.average(
            selected[
                "structural_similarity_score"
            ],
            weights=selected["model_weight"],
        )
    )

    return pd.DataFrame(
        [
            {
                "model_version": MODEL_VERSION,
                "target_apartment_id": target[
                    "apartment_id"
                ],
                "target_apartment_name": target[
                    "apartment_name"
                ],
                "candidate_peer_count": len(
                    peer_scores
                ),
                "selected_peer_count": len(
                    selected
                ),
                "core_peer_count": int(
                    selected[
                        "peer_group_class"
                    ].eq("CORE").sum()
                ),
                "supporting_peer_count": int(
                    selected[
                        "peer_group_class"
                    ].eq("SUPPORTING").sum()
                ),
                "weighted_structural_similarity_score": round(
                    weighted_similarity,
                    2,
                ),
                "effective_sample_size": round(
                    effective_sample_size,
                    2,
                ),
                "model_ready_category_count": int(
                    expected_ranges[
                        "model_status"
                    ].eq("MODEL_READY").sum()
                ),
            }
        ]
    )


def write_model_card(
    summary: pd.DataFrame,
) -> None:
    row = summary.iloc[0]

    model_card = f"""# K-APT Peer Group Model Card

## 1. Model Overview

- Model version: `{MODEL_VERSION}`
- Target apartment: {row["target_apartment_name"]} (`{row["target_apartment_id"]}`)
- Candidate peers: {int(row["candidate_peer_count"])}
- Selected peers: {int(row["selected_peer_count"])}
- Effective sample size: {row["effective_sample_size"]}
- Weighted structural similarity: {row["weighted_structural_similarity_score"]}%
- Model-ready cost categories: {int(row["model_ready_category_count"])}/6

## 2. Purpose

This model selects structurally comparable apartment complexes and calculates a weighted expected management-cost range.

The result is intended for advisory screening and prioritization. It is not proof of inefficient management or a guaranteed saving amount.

## 3. Similarity Weights

| Feature | Weight |
|---|---:|
| Household count | 25% |
| Approval year | 20% |
| Management area per household | 15% |
| Building count | 10% |
| City district | 10% |
| Heating type | 8% |
| Management type | 7% |
| Hall type | 3% |
| Sale type | 2% |

## 4. Peer Selection

- Core peer: suitability score of at least 75 with sufficient profile and cost data
- Supporting peer: suitability score of at least 60 with sufficient cost data
- Selected peers: maximum 30
- Fallback: top 15 peers when threshold-based selection is insufficient

## 5. Expected Cost Range

The expected range is calculated using weighted peer quantiles:

- Low: weighted 25th percentile
- Expected: weighted median
- High: weighted 75th percentile

## 6. Limitations

- Public K-APT data may contain missing or delayed disclosures.
- High cost does not by itself demonstrate inefficiency.
- Facility quality, security scope, outsourcing contracts, and service levels require additional review.
- Indicative excess cost is not a guaranteed saving amount.
- Missing values are not automatically treated as zero.

## 7. Human Review Requirement

Every high-cost signal must be reviewed with contract documents, service scope, budget data, and management-office explanations before an advisory conclusion is issued.
"""

    MODEL_CARD_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    MODEL_CARD_FILE.write_text(
        model_card,
        encoding="utf-8",
    )


def validate_and_save(
    peer_scores: pd.DataFrame,
    expected_ranges: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    PEER_WEIGHT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    peer_scores.to_csv(
        PEER_WEIGHT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    expected_ranges.to_csv(
        EXPECTED_RANGE_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    summary.to_csv(
        MODEL_SUMMARY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    write_model_card(summary)

    selected = peer_scores.loc[
        peer_scores["model_selected"]
    ]

    selected_peer_count = len(selected)
    weight_sum = float(
        selected["model_weight"].sum()
    )

    peer_duplicate_count = int(
        peer_scores.duplicated(
            subset=["apartment_id"]
        ).sum()
    )

    range_duplicate_count = int(
        expected_ranges.duplicated(
            subset=["cost_category"]
        ).sum()
    )

    model_ready_count = int(
        expected_ranges[
            "model_status"
        ].eq("MODEL_READY").sum()
    )

    print(
        f"[OK] 비교단지 평가 수: "
        f"{len(peer_scores):,}"
    )
    print(
        f"[OK] 모델 선정 비교단지 수: "
        f"{selected_peer_count:,}"
    )
    print(
        f"[QA] 선정 가중치 합계: "
        f"{weight_sum:.8f}"
    )
    print(
        f"[QA] 비교단지 중복 수: "
        f"{peer_duplicate_count:,}"
    )
    print(
        f"[OK] 기대비용 범위 수: "
        f"{len(expected_ranges):,}"
    )
    print(
        f"[QA] 기대비용 중복 수: "
        f"{range_duplicate_count:,}"
    )
    print(
        f"[QA] 모델 사용 가능 항목 수: "
        f"{model_ready_count:,}/6"
    )
    print(f"[OK] 비교단지 가중치: {PEER_WEIGHT_FILE}")
    print(f"[OK] 기대비용 범위: {EXPECTED_RANGE_FILE}")
    print(f"[OK] 모델 요약: {MODEL_SUMMARY_FILE}")
    print(f"[OK] 모델 카드: {MODEL_CARD_FILE}")

    if len(peer_scores) != 49:
        raise RuntimeError(
            "비교단지 평가 결과가 49개가 아닙니다."
        )

    if not (
        MIN_SELECTED_PEERS
        <= selected_peer_count
        <= MAX_SELECTED_PEERS
    ):
        raise RuntimeError(
            "모델 선정 비교단지 수가 기준을 벗어났습니다."
        )

    if not np.isclose(
        weight_sum,
        1.0,
        atol=0.000001,
    ):
        raise RuntimeError(
            f"비교단지 가중치 합계가 1이 아닙니다: "
            f"{weight_sum}"
        )

    if len(expected_ranges) != 6:
        raise RuntimeError(
            "기대비용 범위가 6개가 아닙니다."
        )

    if (
        peer_duplicate_count > 0
        or range_duplicate_count > 0
    ):
        raise RuntimeError(
            "모델 결과에 중복 키가 있습니다."
        )

    if model_ready_count < 6:
        print(
            "[WARNING] 일부 비용항목은 모델 기준을 "
            "충족하지 못했습니다."
        )

    print(
        "[SUCCESS] Peer Group Model v1을 생성했습니다."
    )


def main() -> None:
    cohort, annual = load_inputs()

    peer_scores = build_peer_scores(
        cohort=cohort,
        annual=annual,
    )

    expected_ranges = build_expected_ranges(
        cohort=cohort,
        annual=annual,
        peer_scores=peer_scores,
    )

    summary = create_model_summary(
        cohort=cohort,
        peer_scores=peer_scores,
        expected_ranges=expected_ranges,
    )

    validate_and_save(
        peer_scores=peer_scores,
        expected_ranges=expected_ranges,
        summary=summary,
    )


if __name__ == "__main__":
    main()