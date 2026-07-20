from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MONTHLY_FEATURE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "fact_cost_features_monthly.csv"
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

ANOMALY_MONTHLY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "model_anomaly_scores_monthly.csv"
)

ANOMALY_SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "model_anomaly_summary.csv"
)

ANOMALY_ALERT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "model_anomaly_alerts.csv"
)

MODEL_CARD_FILE = (
    PROJECT_ROOT
    / "docs"
    / "model_cards"
    / "anomaly_detection_model.md"
)


MODEL_VERSION = "hybrid-anomaly-v1.0"

MIN_PEER_COUNT = 10
MIN_EFFECTIVE_SAMPLE_SIZE = 5

SIGNAL_WEIGHTS = {
    "cross_sectional": 0.50,
    "expected_range": 0.25,
    "temporal_change": 0.15,
    "persistence": 0.10,
}

REVIEW_FOCUS = {
    "labor": (
        "관리인원, 급여수준, 근무형태 및 "
        "직영·위탁 운영방식 검토"
    ),
    "cleaning": (
        "청소용역 계약단가, 인원, 작업범위 및 "
        "계약 갱신조건 검토"
    ),
    "guard": (
        "경비인원, 교대방식, 근무시간 및 "
        "경비용역 계약조건 검토"
    ),
    "elevator": (
        "승강기 대수, 설비연식, 유지보수 계약단가 및 "
        "고장 이력 검토"
    ),
    "repairs": (
        "수선공사 발생시점, 비용분류, 업체선정 및 "
        "일회성 지출 여부 검토"
    ),
    "facility": (
        "시설 유지보수 범위, 설비연식, 계약단가 및 "
        "예방정비 체계 검토"
    ),
}


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

    cutoff = (
        quantile * sorted_weights.sum()
    )

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


def parse_bool(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .eq("true")
    )


def severity_from_score(
    score: float | None,
) -> str:
    if score is None or pd.isna(score):
        return "NOT_ASSESSED"

    if score >= 80:
        return "CRITICAL"

    if score >= 60:
        return "HIGH"

    if score >= 40:
        return "MEDIUM"

    return "LOW"


def load_inputs() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    for file_path in [
        MONTHLY_FEATURE_FILE,
        PEER_WEIGHT_FILE,
        EXPECTED_RANGE_FILE,
    ]:
        if not file_path.exists():
            raise FileNotFoundError(
                f"필수 입력 파일이 없습니다: {file_path}"
            )

    features = pd.read_csv(
        MONTHLY_FEATURE_FILE,
        dtype={
            "apartment_id": "string",
            "cohort_role": "string",
            "search_month": "string",
            "cost_category": "string",
        },
    )

    peer_weights = pd.read_csv(
        PEER_WEIGHT_FILE,
        dtype={
            "apartment_id": "string",
        },
    )

    expected_ranges = pd.read_csv(
        EXPECTED_RANGE_FILE,
        dtype={
            "cost_category": "string",
        },
    )

    required_feature_columns = {
        "apartment_id",
        "apartment_name",
        "cohort_role",
        "search_month",
        "month_start_date",
        "cost_category",
        "cost_category_name_ko",
        "cost_per_household_krw",
        "feature_usable",
        "data_quality_status",
        "source_quality_weight",
    }

    missing_feature_columns = (
        required_feature_columns
        - set(features.columns)
    )

    if missing_feature_columns:
        raise ValueError(
            f"월별 피처 필수 칼럼이 없습니다: "
            f"{sorted(missing_feature_columns)}"
        )

    required_weight_columns = {
        "apartment_id",
        "model_selected",
        "model_weight",
    }

    missing_weight_columns = (
        required_weight_columns
        - set(peer_weights.columns)
    )

    if missing_weight_columns:
        raise ValueError(
            f"비교단지 가중치 필수 칼럼이 없습니다: "
            f"{sorted(missing_weight_columns)}"
        )

    features["apartment_id"] = (
        features["apartment_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    peer_weights["apartment_id"] = (
        peer_weights["apartment_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    features["cohort_role"] = (
        features["cohort_role"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    features["feature_usable"] = parse_bool(
        features["feature_usable"]
    )

    peer_weights["model_selected"] = parse_bool(
        peer_weights["model_selected"]
    )

    numeric_feature_columns = [
        "cost_per_household_krw",
        "source_quality_weight",
    ]

    for column in numeric_feature_columns:
        features[column] = pd.to_numeric(
            features[column],
            errors="coerce",
        )

    peer_weights["model_weight"] = pd.to_numeric(
        peer_weights["model_weight"],
        errors="coerce",
    )

    expected_numeric_columns = [
        "indicative_annual_excess_cost_krw",
        "target_gap_pct",
        "effective_sample_size",
    ]

    for column in expected_numeric_columns:
        if column in expected_ranges.columns:
            expected_ranges[column] = pd.to_numeric(
                expected_ranges[column],
                errors="coerce",
            )

    target_rows = features.loc[
        features["cohort_role"].eq("TARGET")
    ]

    if target_rows["apartment_id"].nunique() != 1:
        raise ValueError(
            "월별 피처에 TARGET 단지가 정확히 "
            "1개가 아닙니다."
        )

    if len(target_rows) != 72:
        raise ValueError(
            f"TARGET 월별 행 수가 72가 아닙니다: "
            f"{len(target_rows)}"
        )

    selected_peers = peer_weights.loc[
        peer_weights["model_selected"]
    ]

    if not 15 <= len(selected_peers) <= 30:
        raise ValueError(
            f"선정 비교단지 수가 기준을 벗어났습니다: "
            f"{len(selected_peers)}"
        )

    return features, peer_weights, expected_ranges


def build_monthly_peer_benchmarks(
    features: pd.DataFrame,
    peer_weights: pd.DataFrame,
) -> pd.DataFrame:
    target_rows = (
        features.loc[
            features["cohort_role"].eq("TARGET")
        ]
        .sort_values(
            by=[
                "cost_category",
                "search_month",
            ]
        )
        .reset_index(drop=True)
    )

    peer_rows = features.loc[
        features["cohort_role"].eq("PEER")
    ].copy()

    peer_rows = peer_rows.merge(
        peer_weights[
            [
                "apartment_id",
                "model_selected",
                "model_weight",
            ]
        ],
        on="apartment_id",
        how="left",
        validate="many_to_one",
    )

    output_rows: list[dict[str, Any]] = []

    for _, target in target_rows.iterrows():
        peer_pool = peer_rows.loc[
            peer_rows["search_month"].eq(
                target["search_month"]
            )
            & peer_rows["cost_category"].eq(
                target["cost_category"]
            )
            & peer_rows["model_selected"].eq(True)
            & peer_rows["feature_usable"]
            & peer_rows[
                "cost_per_household_krw"
            ].notna()
            & peer_rows["model_weight"].gt(0)
        ].copy()

        peer_count = len(peer_pool)
        available_weight = float(
            peer_pool["model_weight"].sum()
        )

        if available_weight > 0:
            peer_pool["monthly_weight"] = (
                peer_pool["model_weight"]
                / available_weight
            )
        else:
            peer_pool["monthly_weight"] = 0.0

        values = peer_pool[
            "cost_per_household_krw"
        ]

        weights = peer_pool["monthly_weight"]

        if peer_count > 0:
            peer_mean = float(
                np.average(
                    values.astype(float),
                    weights=weights.astype(float),
                )
            )

            peer_q1 = weighted_quantile(
                values,
                weights,
                0.25,
            )

            peer_median = weighted_quantile(
                values,
                weights,
                0.50,
            )

            peer_q3 = weighted_quantile(
                values,
                weights,
                0.75,
            )

            effective_sample_size = float(
                1
                / np.square(
                    weights.astype(float)
                ).sum()
            )
        else:
            peer_mean = None
            peer_q1 = None
            peer_median = None
            peer_q3 = None
            effective_sample_size = 0.0

        if (
            peer_median is not None
            and peer_count > 0
        ):
            absolute_deviations = (
                values.astype(float)
                - peer_median
            ).abs()

            weighted_mad = weighted_quantile(
                absolute_deviations,
                weights,
                0.50,
            )
        else:
            weighted_mad = None

        target_value = target[
            "cost_per_household_krw"
        ]

        if not bool(target["feature_usable"]):
            benchmark_status = "TARGET_UNUSABLE"

        elif (
            peer_count < MIN_PEER_COUNT
            or effective_sample_size
            < MIN_EFFECTIVE_SAMPLE_SIZE
        ):
            benchmark_status = "INSUFFICIENT_PEERS"

        else:
            benchmark_status = "BENCHMARK_READY"

        peer_iqr = (
            peer_q3 - peer_q1
            if (
                peer_q1 is not None
                and peer_q3 is not None
            )
            else None
        )

        if (
            benchmark_status == "BENCHMARK_READY"
            and pd.notna(target_value)
            and peer_median is not None
        ):
            gap_per_household = float(
                target_value - peer_median
            )

            if peer_median != 0:
                gap_pct = float(
                    gap_per_household
                    / peer_median
                    * 100
                )
            else:
                gap_pct = None

            if (
                weighted_mad is not None
                and weighted_mad > 0
            ):
                robust_z_score = float(
                    0.6745
                    * gap_per_household
                    / weighted_mad
                )
            else:
                fallback_scale = max(
                    (
                        peer_iqr / 1.349
                        if (
                            peer_iqr is not None
                            and peer_iqr > 0
                        )
                        else 0
                    ),
                    abs(peer_median) * 0.05,
                    1,
                )

                robust_z_score = float(
                    gap_per_household
                    / fallback_scale
                )

            range_scale = max(
                peer_iqr or 0,
                abs(peer_median) * 0.05,
                1,
            )

            range_exceedance_ratio = float(
                max(
                    target_value
                    - (peer_q3 or peer_median),
                    0,
                )
                / range_scale
            )
        else:
            gap_per_household = None
            gap_pct = None
            robust_z_score = None
            range_exceedance_ratio = None

        if (
            benchmark_status == "BENCHMARK_READY"
            and pd.notna(target_value)
            and peer_q3 is not None
        ):
            above_expected_high = bool(
                target_value > peer_q3
            )
        else:
            above_expected_high = False

        target_quality_weight = target[
            "source_quality_weight"
        ]

        if pd.isna(target_quality_weight):
            target_quality_weight = 0.0

        if benchmark_status == "BENCHMARK_READY":
            effective_sample_factor = min(
                effective_sample_size / 10,
                1,
            )

            available_weight_factor = min(
                available_weight / 0.8,
                1,
            )

            confidence_score = (
                float(target_quality_weight) * 0.4
                + effective_sample_factor * 0.3
                + available_weight_factor * 0.3
            ) * 100
        else:
            confidence_score = 0.0

        output_rows.append(
            {
                "model_version": MODEL_VERSION,
                "apartment_id": target[
                    "apartment_id"
                ],
                "apartment_name": target[
                    "apartment_name"
                ],
                "search_month": target[
                    "search_month"
                ],
                "month_start_date": target[
                    "month_start_date"
                ],
                "cost_category": target[
                    "cost_category"
                ],
                "cost_category_name_ko": target[
                    "cost_category_name_ko"
                ],
                "target_cost_per_household_krw": (
                    target_value
                ),
                "target_data_quality_status": target[
                    "data_quality_status"
                ],
                "peer_count": peer_count,
                "effective_sample_size": round(
                    effective_sample_size,
                    2,
                ),
                "available_model_weight_pct": round(
                    available_weight * 100,
                    2,
                ),
                "peer_weighted_mean_krw": peer_mean,
                "peer_q1_krw": peer_q1,
                "peer_median_krw": peer_median,
                "peer_q3_krw": peer_q3,
                "peer_iqr_krw": peer_iqr,
                "weighted_mad_krw": weighted_mad,
                "gap_per_household_krw": (
                    gap_per_household
                ),
                "gap_pct": gap_pct,
                "robust_z_score": robust_z_score,
                "range_exceedance_ratio": (
                    range_exceedance_ratio
                ),
                "above_expected_high": (
                    above_expected_high
                ),
                "confidence_score": round(
                    confidence_score,
                    2,
                ),
                "benchmark_status": benchmark_status,
            }
        )

    return pd.DataFrame(output_rows)


def add_temporal_signals(
    scores: pd.DataFrame,
) -> pd.DataFrame:
    scores = scores.sort_values(
        by=[
            "cost_category",
            "search_month",
        ]
    ).reset_index(drop=True)

    scores[
        "trailing_3m_target_median_krw"
    ] = np.nan

    scores["consecutive_above_range_months"] = 0

    for _, indices in scores.groupby(
        "cost_category"
    ).groups.items():
        category_rows = scores.loc[
            indices
        ].sort_values("search_month")

        trailing_median = (
            category_rows[
                "target_cost_per_household_krw"
            ]
            .shift(1)
            .rolling(
                window=3,
                min_periods=2,
            )
            .median()
        )

        scores.loc[
            category_rows.index,
            "trailing_3m_target_median_krw",
        ] = trailing_median

        consecutive_count = 0

        for row_index in category_rows.index:
            if bool(
                scores.at[
                    row_index,
                    "above_expected_high",
                ]
            ):
                consecutive_count += 1
            else:
                consecutive_count = 0

            scores.at[
                row_index,
                "consecutive_above_range_months",
            ] = consecutive_count

    trailing_reference = scores[
        "trailing_3m_target_median_krw"
    ]

    scores["temporal_change_pct"] = (
        scores[
            "target_cost_per_household_krw"
        ]
        .sub(trailing_reference)
        .div(
            trailing_reference.where(
                trailing_reference.ne(0)
            )
        )
        .mul(100)
    )

    return scores


def add_anomaly_scores(
    scores: pd.DataFrame,
) -> pd.DataFrame:
    cross_scores = []
    range_scores = []
    temporal_scores = []
    persistence_scores = []
    raw_scores = []
    final_scores = []
    severities = []
    low_cost_flags = []
    anomaly_reasons = []
    alert_flags = []

    for _, row in scores.iterrows():
        if (
            row["benchmark_status"]
            != "BENCHMARK_READY"
            or pd.isna(
                row[
                    "target_cost_per_household_krw"
                ]
            )
        ):
            cross_score = None
            range_score = None
            temporal_score = None
            persistence_score = None
            raw_score = None
            final_score = None
            severity = "NOT_ASSESSED"
            low_cost_flag = False
            anomaly_reason = "INSUFFICIENT_DATA"
            is_alert = False

        else:
            robust_z = row["robust_z_score"]

            if pd.isna(robust_z):
                robust_z = 0.0

            range_ratio = row[
                "range_exceedance_ratio"
            ]

            if pd.isna(range_ratio):
                range_ratio = 0.0

            temporal_change = row[
                "temporal_change_pct"
            ]

            if pd.isna(temporal_change):
                temporal_change = 0.0

            persistence_months = row[
                "consecutive_above_range_months"
            ]

            cross_score = min(
                max(float(robust_z), 0)
                / 3
                * 100,
                100,
            )

            range_score = min(
                max(float(range_ratio), 0)
                / 1.5
                * 100,
                100,
            )

            temporal_score = min(
                max(float(temporal_change), 0)
                / 30
                * 100,
                100,
            )

            persistence_score = min(
                float(persistence_months)
                / 3
                * 100,
                100,
            )

            raw_score = (
                cross_score
                * SIGNAL_WEIGHTS[
                    "cross_sectional"
                ]
                + range_score
                * SIGNAL_WEIGHTS[
                    "expected_range"
                ]
                + temporal_score
                * SIGNAL_WEIGHTS[
                    "temporal_change"
                ]
                + persistence_score
                * SIGNAL_WEIGHTS[
                    "persistence"
                ]
            )

            confidence_factor = (
                float(row["confidence_score"])
                / 100
            )

            final_score = round(
                raw_score * confidence_factor,
                2,
            )

            severity = severity_from_score(
                final_score
            )

            low_cost_flag = bool(
                float(robust_z) <= -3
            )

            signal_values = {
                "PEER_DEVIATION": cross_score,
                "EXPECTED_RANGE_EXCESS": (
                    range_score
                ),
                "TEMPORAL_INCREASE": (
                    temporal_score
                ),
                "PERSISTENT_EXCESS": (
                    persistence_score
                ),
            }

            if low_cost_flag:
                anomaly_reason = (
                    "UNUSUALLY_LOW_COST_DATA_REVIEW"
                )
            else:
                anomaly_reason = max(
                    signal_values,
                    key=signal_values.get,
                )

            is_alert = bool(
                severity in {
                    "HIGH",
                    "CRITICAL",
                }
                or low_cost_flag
            )

        cross_scores.append(cross_score)
        range_scores.append(range_score)
        temporal_scores.append(temporal_score)
        persistence_scores.append(
            persistence_score
        )
        raw_scores.append(raw_score)
        final_scores.append(final_score)
        severities.append(severity)
        low_cost_flags.append(low_cost_flag)
        anomaly_reasons.append(anomaly_reason)
        alert_flags.append(is_alert)

    scores["cross_sectional_signal_score"] = (
        cross_scores
    )

    scores["expected_range_signal_score"] = (
        range_scores
    )

    scores["temporal_signal_score"] = (
        temporal_scores
    )

    scores["persistence_signal_score"] = (
        persistence_scores
    )

    scores["raw_anomaly_score"] = raw_scores
    scores["anomaly_score"] = final_scores
    scores["anomaly_severity"] = severities
    scores["low_cost_review_flag"] = (
        low_cost_flags
    )
    scores["anomaly_reason"] = anomaly_reasons
    scores["is_alert"] = alert_flags

    scores["review_focus"] = (
        scores["cost_category"]
        .map(REVIEW_FOCUS)
    )

    return scores


def build_category_summary(
    scores: pd.DataFrame,
    expected_ranges: pd.DataFrame,
) -> pd.DataFrame:
    expected_lookup = {
        row["cost_category"]: row
        for _, row in expected_ranges.iterrows()
    }

    output_rows: list[dict[str, Any]] = []

    for category, group in scores.groupby(
        "cost_category"
    ):
        group = group.sort_values(
            "search_month"
        )

        assessed = group.loc[
            group["anomaly_score"].notna()
        ]

        if assessed.empty:
            average_score = None
            maximum_score = None
            summary_score = None
        else:
            average_score = float(
                assessed["anomaly_score"].mean()
            )

            maximum_score = float(
                assessed["anomaly_score"].max()
            )

            summary_score = round(
                maximum_score * 0.6
                + average_score * 0.4,
                2,
            )

        signal_columns = {
            "PEER_DEVIATION": (
                "cross_sectional_signal_score"
            ),
            "EXPECTED_RANGE_EXCESS": (
                "expected_range_signal_score"
            ),
            "TEMPORAL_INCREASE": (
                "temporal_signal_score"
            ),
            "PERSISTENT_EXCESS": (
                "persistence_signal_score"
            ),
        }

        signal_averages = {}

        for signal_name, column in (
            signal_columns.items()
        ):
            signal_averages[signal_name] = (
                float(assessed[column].mean())
                if (
                    not assessed.empty
                    and assessed[column].notna().any()
                )
                else 0.0
            )

        dominant_signal = max(
            signal_averages,
            key=signal_averages.get,
        )

        summary_severity = severity_from_score(
            summary_score
        )

        if summary_severity in {
            "CRITICAL",
            "HIGH",
        }:
            review_recommendation = (
                "IMMEDIATE_REVIEW"
            )
        elif summary_severity == "MEDIUM":
            review_recommendation = (
                "CONTRACT_AND_SCOPE_REVIEW"
            )
        elif summary_severity == "LOW":
            review_recommendation = "MONITOR"
        else:
            review_recommendation = (
                "DATA_VALIDATION"
            )

        latest = group.iloc[-1]
        expected = expected_lookup.get(category)

        if expected is not None:
            indicative_annual_excess = (
                expected.get(
                    "indicative_annual_excess_cost_krw"
                )
            )
            annual_gap_pct = expected.get(
                "target_gap_pct"
            )
            annual_range_position = expected.get(
                "target_range_position"
            )
            expected_confidence = expected.get(
                "confidence_level"
            )
        else:
            indicative_annual_excess = None
            annual_gap_pct = None
            annual_range_position = None
            expected_confidence = None

        output_rows.append(
            {
                "model_version": MODEL_VERSION,
                "apartment_id": latest[
                    "apartment_id"
                ],
                "apartment_name": latest[
                    "apartment_name"
                ],
                "cost_category": category,
                "cost_category_name_ko": latest[
                    "cost_category_name_ko"
                ],
                "assessed_month_count": len(
                    assessed
                ),
                "alert_month_count": int(
                    group["is_alert"].sum()
                ),
                "high_or_critical_month_count": int(
                    group[
                        "anomaly_severity"
                    ].isin(
                        ["HIGH", "CRITICAL"]
                    ).sum()
                ),
                "above_expected_month_count": int(
                    group[
                        "above_expected_high"
                    ].sum()
                ),
                "low_cost_review_month_count": int(
                    group[
                        "low_cost_review_flag"
                    ].sum()
                ),
                "average_anomaly_score": (
                    average_score
                ),
                "maximum_anomaly_score": (
                    maximum_score
                ),
                "anomaly_summary_score": (
                    summary_score
                ),
                "summary_severity": (
                    summary_severity
                ),
                "dominant_signal": (
                    dominant_signal
                ),
                "latest_search_month": latest[
                    "search_month"
                ],
                "latest_anomaly_score": latest[
                    "anomaly_score"
                ],
                "latest_anomaly_severity": latest[
                    "anomaly_severity"
                ],
                "annual_gap_pct": annual_gap_pct,
                "annual_range_position": (
                    annual_range_position
                ),
                "indicative_annual_excess_cost_krw": (
                    indicative_annual_excess
                ),
                "confidence_level": (
                    expected_confidence
                ),
                "review_recommendation": (
                    review_recommendation
                ),
                "review_focus": REVIEW_FOCUS.get(
                    category
                ),
            }
        )

    return pd.DataFrame(output_rows).sort_values(
        by=[
            "anomaly_summary_score",
            "cost_category",
        ],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)


def write_model_card(
    scores: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    assessed_count = int(
        scores["anomaly_score"].notna().sum()
    )

    alert_count = int(
        scores["is_alert"].sum()
    )

    high_category_count = int(
        summary["summary_severity"]
        .isin(["HIGH", "CRITICAL"])
        .sum()
    )

    model_card = f"""# K-APT Hybrid Anomaly Detection Model Card

## 1. Model Overview

- Model version: `{MODEL_VERSION}`
- Monthly target observations: {len(scores)}
- Assessed observations: {assessed_count}
- Alert observations: {alert_count}
- High or critical cost categories: {high_category_count}/6

## 2. Purpose

The model screens monthly apartment management costs for unusual cost patterns and prioritizes areas for human review.

It does not determine fraud, overbilling, or inefficient management.

## 3. Signals

| Signal | Weight | Description |
|---|---:|---|
| Peer deviation | 50% | Robust deviation from the weighted peer median |
| Expected-range excess | 25% | Distance above the weighted peer 75th percentile |
| Temporal increase | 15% | Increase from the prior three-month median |
| Persistent excess | 10% | Consecutive months above the expected range |

## 4. Severity Thresholds

| Score | Severity |
|---:|---|
| 80–100 | Critical |
| 60–79.99 | High |
| 40–59.99 | Medium |
| 0–39.99 | Low |

## 5. Confidence Adjustment

The raw anomaly score is adjusted using:

- Target source-data quality
- Effective peer sample size
- Available peer-model weight

## 6. Limitations

- A high score is a review signal, not proof of inefficiency.
- One-time repairs can generate legitimate cost spikes.
- Differences in service quality and contract scope may explain cost differences.
- Missing values are not treated as zero.
- Unusually low costs are separately flagged because they may indicate incomplete disclosure or classification differences.

## 7. Required Human Review

Before issuing an advisory conclusion, review:

- Service contracts and renewal terms
- Staffing and operating scope
- Repair and maintenance records
- Budget-versus-actual reports
- Management-office explanations
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
    scores: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    alerts = scores.loc[
        scores["is_alert"]
    ].copy()

    ANOMALY_MONTHLY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    scores.to_csv(
        ANOMALY_MONTHLY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    summary.to_csv(
        ANOMALY_SUMMARY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    alerts.to_csv(
        ANOMALY_ALERT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    write_model_card(
        scores=scores,
        summary=summary,
    )

    monthly_duplicate_count = int(
        scores.duplicated(
            subset=[
                "search_month",
                "cost_category",
            ]
        ).sum()
    )

    summary_duplicate_count = int(
        summary.duplicated(
            subset=["cost_category"]
        ).sum()
    )

    assessed_count = int(
        scores["anomaly_score"].notna().sum()
    )

    alert_count = len(alerts)

    critical_count = int(
        scores["anomaly_severity"]
        .eq("CRITICAL")
        .sum()
    )

    high_count = int(
        scores["anomaly_severity"]
        .eq("HIGH")
        .sum()
    )

    print(f"[OK] 월별 이상징후 수: {len(scores):,}")
    print(f"[OK] 비용항목 요약 수: {len(summary):,}")
    print(f"[OK] 분석 가능 월별 건수: {assessed_count:,}")
    print(f"[OK] 경보 건수: {alert_count:,}")
    print(f"[QA] Critical 건수: {critical_count:,}")
    print(f"[QA] High 건수: {high_count:,}")
    print(
        f"[QA] 월별 중복 키 수: "
        f"{monthly_duplicate_count:,}"
    )
    print(
        f"[QA] 요약 중복 키 수: "
        f"{summary_duplicate_count:,}"
    )
    print(f"[OK] 월별 점수: {ANOMALY_MONTHLY_FILE}")
    print(f"[OK] 항목별 요약: {ANOMALY_SUMMARY_FILE}")
    print(f"[OK] 경보 목록: {ANOMALY_ALERT_FILE}")
    print(f"[OK] 모델 카드: {MODEL_CARD_FILE}")

    if len(scores) != 72:
        raise RuntimeError(
            "월별 이상징후 결과가 72행이 아닙니다."
        )

    if len(summary) != 6:
        raise RuntimeError(
            "비용항목 요약이 6행이 아닙니다."
        )

    if (
        monthly_duplicate_count > 0
        or summary_duplicate_count > 0
    ):
        raise RuntimeError(
            "이상징후 결과에 중복 키가 있습니다."
        )

    if alert_count == 0:
        print(
            "[INFO] High 또는 Critical 경보가 없습니다. "
            "이는 정상적인 분석 결과일 수 있습니다."
        )

    print(
        "[SUCCESS] Hybrid Anomaly Model v1을 생성했습니다."
    )


def main() -> None:
    features, peer_weights, expected_ranges = (
        load_inputs()
    )

    scores = build_monthly_peer_benchmarks(
        features=features,
        peer_weights=peer_weights,
    )

    scores = add_temporal_signals(scores)
    scores = add_anomaly_scores(scores)

    summary = build_category_summary(
        scores=scores,
        expected_ranges=expected_ranges,
    )

    validate_and_save(
        scores=scores,
        summary=summary,
    )


if __name__ == "__main__":
    main()