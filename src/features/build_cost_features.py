from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

MONTHLY_FACT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "fact_common_cost_monthly.csv"
)

COHORT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "pilot_cohort.csv"
)

MONTHLY_FEATURE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "fact_cost_features_monthly.csv"
)

APARTMENT_ANNUAL_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "fact_apartment_cost_annual.csv"
)

TARGET_MONTHLY_BENCHMARK_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "fact_target_benchmark_monthly.csv"
)

TARGET_ANNUAL_BENCHMARK_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "fact_target_benchmark_annual.csv"
)


MIN_OBSERVED_MONTHS = 9
MIN_PEER_COUNT = 10

USABLE_QUALITY_STATUSES = {
    "OBSERVED",
    "PARTIAL_COMPONENTS",
}


def load_inputs() -> pd.DataFrame:
    if not MONTHLY_FACT_FILE.exists():
        raise FileNotFoundError(
            f"월별 관리비 팩트가 없습니다: {MONTHLY_FACT_FILE}"
        )

    if not COHORT_FILE.exists():
        raise FileNotFoundError(
            f"파일럿 비교군 파일이 없습니다: {COHORT_FILE}"
        )

    fact = pd.read_csv(
        MONTHLY_FACT_FILE,
        dtype={
            "apartment_id": "string",
            "search_month": "string",
            "cost_category": "string",
            "cohort_role": "string",
        },
    )

    cohort = pd.read_csv(
        COHORT_FILE,
        dtype={
            "apartment_id": "string",
        },
    )

    required_fact_columns = {
        "apartment_id",
        "apartment_name",
        "cohort_role",
        "search_month",
        "cost_category",
        "cost_category_name_ko",
        "cost_amount_krw",
        "data_quality_status",
    }

    missing_fact_columns = (
        required_fact_columns - set(fact.columns)
    )

    if missing_fact_columns:
        raise ValueError(
            f"관리비 팩트 필수 칼럼이 없습니다: "
            f"{sorted(missing_fact_columns)}"
        )

    required_profile_columns = {
        "apartment_id",
        "household_count",
        "management_area_m2",
    }

    missing_profile_columns = (
        required_profile_columns - set(cohort.columns)
    )

    if missing_profile_columns:
        raise ValueError(
            f"비교군 필수 칼럼이 없습니다: "
            f"{sorted(missing_profile_columns)}"
        )

    fact["apartment_id"] = (
        fact["apartment_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    cohort["apartment_id"] = (
        cohort["apartment_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    fact["cohort_role"] = (
        fact["cohort_role"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    fact["cost_amount_krw"] = pd.to_numeric(
        fact["cost_amount_krw"],
        errors="coerce",
    )

    profile = cohort[
        [
            "apartment_id",
            "household_count",
            "management_area_m2",
        ]
    ].drop_duplicates(
        subset=["apartment_id"],
        keep="first",
    )

    profile["household_count"] = pd.to_numeric(
        profile["household_count"],
        errors="coerce",
    )

    profile["management_area_m2"] = pd.to_numeric(
        profile["management_area_m2"],
        errors="coerce",
    )

    features = fact.merge(
        profile,
        on="apartment_id",
        how="left",
        validate="many_to_one",
    )

    key_columns = [
        "apartment_id",
        "search_month",
        "cost_category",
    ]

    duplicate_count = int(
        features.duplicated(
            subset=key_columns
        ).sum()
    )

    if duplicate_count > 0:
        raise RuntimeError(
            f"월별 관리비 키 중복이 있습니다: {duplicate_count}"
        )

    features["feature_usable"] = (
        features["data_quality_status"]
        .isin(USABLE_QUALITY_STATUSES)
        & features["cost_amount_krw"].notna()
        & features["household_count"].gt(0)
    )

    features["feature_reliable"] = (
        features["data_quality_status"].eq("OBSERVED")
        & features["cost_amount_krw"].notna()
        & features["household_count"].gt(0)
    )

    features["per_household_available"] = (
        features["feature_usable"]
        & features["household_count"].gt(0)
    )

    features["per_m2_available"] = (
        features["feature_usable"]
        & features["management_area_m2"].gt(0)
    )

    features["cost_per_household_krw"] = (
        features["cost_amount_krw"]
        .div(features["household_count"])
        .where(features["per_household_available"])
    )

    features["cost_per_management_m2_krw"] = (
        features["cost_amount_krw"]
        .div(features["management_area_m2"])
        .where(features["per_m2_available"])
    )

    quality_weights = {
        "OBSERVED": 1.0,
        "PARTIAL_COMPONENTS": 0.7,
        "MISSING_AMOUNT": 0.0,
        "SOURCE_NO_DATA": 0.0,
        "NOT_COLLECTED": 0.0,
        "INVALID_NUMBER": 0.0,
    }

    features["source_quality_weight"] = (
        features["data_quality_status"]
        .map(quality_weights)
        .fillna(0.0)
    )

    print(f"[INFO] 월별 팩트 수: {len(features):,}")
    print(
        f"[INFO] 사용 가능 피처 수: "
        f"{int(features['feature_usable'].sum()):,}"
    )
    print(
        f"[INFO] 신뢰도 높은 피처 수: "
        f"{int(features['feature_reliable'].sum()):,}"
    )

    return features


def classify_outlier(
    value: float | None,
    q1: float | None,
    q3: float | None,
) -> str:
    if (
        value is None
        or pd.isna(value)
        or q1 is None
        or pd.isna(q1)
        or q3 is None
        or pd.isna(q3)
    ):
        return "NOT_ASSESSED"

    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    if value > upper_bound:
        return "HIGH_OUTLIER"

    if value < lower_bound:
        return "LOW_OUTLIER"

    return "WITHIN_RANGE"


def calculate_percentile(
    target_value: float | None,
    peer_values: pd.Series,
) -> float | None:
    if (
        target_value is None
        or pd.isna(target_value)
        or peer_values.empty
    ):
        return None

    percentile = (
        peer_values.le(target_value).sum()
        / len(peer_values)
        * 100
    )

    return round(float(percentile), 2)


def build_monthly_target_benchmark(
    features: pd.DataFrame,
) -> pd.DataFrame:
    target_rows = features.loc[
        features["cohort_role"].eq("TARGET")
    ].copy()

    peer_rows = features.loc[
        features["cohort_role"].eq("PEER")
    ].copy()

    expected_target_rows = (
        target_rows["search_month"].nunique()
        * target_rows["cost_category"].nunique()
    )

    if len(target_rows) != expected_target_rows:
        raise RuntimeError(
            "대상 단지 월별 행 수가 예상과 다릅니다."
        )

    benchmark_rows: list[dict[str, Any]] = []

    for _, target in target_rows.iterrows():
        peer_pool = peer_rows.loc[
            peer_rows["search_month"].eq(
                target["search_month"]
            )
            & peer_rows["cost_category"].eq(
                target["cost_category"]
            )
            & peer_rows["feature_usable"]
            & peer_rows[
                "cost_per_household_krw"
            ].notna()
        ]

        peer_values = peer_pool[
            "cost_per_household_krw"
        ].astype(float)

        peer_count = len(peer_values)

        if peer_count > 0:
            peer_mean = float(peer_values.mean())
            peer_median = float(peer_values.median())
            peer_q1 = float(peer_values.quantile(0.25))
            peer_q3 = float(peer_values.quantile(0.75))
            peer_std = (
                float(peer_values.std(ddof=1))
                if peer_count > 1
                else None
            )
        else:
            peer_mean = None
            peer_median = None
            peer_q1 = None
            peer_q3 = None
            peer_std = None

        target_value = target[
            "cost_per_household_krw"
        ]

        if not target["feature_usable"]:
            benchmark_status = "TARGET_UNUSABLE"

        elif peer_count < MIN_PEER_COUNT:
            benchmark_status = "INSUFFICIENT_PEERS"

        else:
            benchmark_status = "BENCHMARK_READY"

        if (
            benchmark_status == "BENCHMARK_READY"
            and peer_median is not None
            and peer_median != 0
        ):
            gap_krw = float(
                target_value - peer_median
            )
            gap_pct = float(
                gap_krw / peer_median * 100
            )
            indicative_excess_cost = max(
                gap_krw, 0
            ) * float(target["household_count"])
        else:
            gap_krw = None
            gap_pct = None
            indicative_excess_cost = None

        benchmark_rows.append(
            {
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
                "target_cost_amount_krw": target[
                    "cost_amount_krw"
                ],
                "target_cost_per_household_krw": (
                    target_value
                ),
                "target_data_quality_status": target[
                    "data_quality_status"
                ],
                "peer_count": peer_count,
                "peer_mean_cost_per_household_krw": (
                    peer_mean
                ),
                "peer_median_cost_per_household_krw": (
                    peer_median
                ),
                "peer_q1_cost_per_household_krw": (
                    peer_q1
                ),
                "peer_q3_cost_per_household_krw": (
                    peer_q3
                ),
                "peer_std_cost_per_household_krw": (
                    peer_std
                ),
                "target_gap_std_cost_per_household_krw": (
                    peer_std
                ),
                "target_per_household_krw": (
                    gap_krw
                ),
                "target_gap_pct": gap_pct,
                "target_percentile": (
                    calculate_percentile(
                        target_value,
                        peer_values,
                    )
                    if peer_count >= MIN_PEER_COUNT
                    else None
                ),
                "outlier_status": classify_outlier(
                    target_value,
                    peer_q1,
                    peer_q3,
                ),
                "indicative_monthly_excess_cost_krw": (
                    indicative_excess_cost
                ),
                "benchmark_status": benchmark_status,
            }
        )

    return pd.DataFrame(benchmark_rows)


def build_apartment_annual_features(
    features: pd.DataFrame,
) -> pd.DataFrame:
    annual_rows: list[dict[str, Any]] = []

    group_columns = [
        "apartment_id",
        "cost_category",
    ]

    for _, group in features.groupby(
        group_columns,
        sort=False,
    ):
        first = group.iloc[0]

        usable = group.loc[
            group["feature_usable"]
            & group[
                "cost_per_household_krw"
            ].notna()
        ]

        reliable = group.loc[
            group["feature_reliable"]
            & group[
                "cost_per_household_krw"
            ].notna()
        ]

        m2_usable = group.loc[
            group["feature_usable"]
            & group[
                "cost_per_management_m2_krw"
            ].notna()
        ]

        source_month_count = len(group)
        observed_month_count = len(usable)
        reliable_month_count = len(reliable)
        m2_observed_month_count = len(m2_usable)

        partial_month_count = int(
            group["data_quality_status"]
            .eq("PARTIAL_COMPONENTS")
            .sum()
        )

        coverage_pct = (
            observed_month_count
            / source_month_count
            * 100
            if source_month_count
            else 0
        )

        if observed_month_count >= MIN_OBSERVED_MONTHS:
            annualized_total_cost = (
                usable["cost_amount_krw"].sum(
                    min_count=1
                )
                / observed_month_count
                * 12
            )

            annualized_per_household = (
                usable[
                    "cost_per_household_krw"
                ].sum(min_count=1)
                / observed_month_count
                * 12
            )
        else:
            annualized_total_cost = None
            annualized_per_household = None

        if (
            m2_observed_month_count
            >= MIN_OBSERVED_MONTHS
        ):
            annualized_per_m2 = (
                m2_usable[
                    "cost_per_management_m2_krw"
                ].sum(min_count=1)
                / m2_observed_month_count
                * 12
            )
        else:
            annualized_per_m2 = None

        if observed_month_count < MIN_OBSERVED_MONTHS:
            annual_quality_status = (
                "INSUFFICIENT_DATA"
            )
        elif partial_month_count > 0:
            annual_quality_status = (
                "PARTIAL_SOURCE_FIELDS"
            )
        elif observed_month_count == source_month_count:
            annual_quality_status = "COMPLETE"
        else:
            annual_quality_status = (
                "USABLE_WITH_GAPS"
            )

        annual_rows.append(
            {
                "apartment_id": first[
                    "apartment_id"
                ],
                "apartment_name": first[
                    "apartment_name"
                ],
                "cohort_role": first[
                    "cohort_role"
                ],
                "cost_category": first[
                    "cost_category"
                ],
                "cost_category_name_ko": first[
                    "cost_category_name_ko"
                ],
                "household_count": first[
                    "household_count"
                ],
                "management_area_m2": first[
                    "management_area_m2"
                ],
                "source_month_count": (
                    source_month_count
                ),
                "observed_month_count": (
                    observed_month_count
                ),
                "reliable_month_count": (
                    reliable_month_count
                ),
                "partial_month_count": (
                    partial_month_count
                ),
                "coverage_pct": round(
                    coverage_pct,
                    2,
                ),
                "average_quality_weight": round(
                    float(
                        group[
                            "source_quality_weight"
                        ].mean()
                    ),
                    4,
                ),
                "annualized_total_cost_krw": (
                    annualized_total_cost
                ),
                "annualized_cost_per_household_krw": (
                    annualized_per_household
                ),
                "annualized_cost_per_management_m2_krw": (
                    annualized_per_m2
                ),
                "annual_quality_status": (
                    annual_quality_status
                ),
            }
        )

    return pd.DataFrame(annual_rows)


def build_annual_target_benchmark(
    annual_features: pd.DataFrame,
) -> pd.DataFrame:
    target_rows = annual_features.loc[
        annual_features["cohort_role"].eq("TARGET")
    ].copy()

    peer_rows = annual_features.loc[
        annual_features["cohort_role"].eq("PEER")
    ].copy()

    benchmark_rows: list[dict[str, Any]] = []

    for _, target in target_rows.iterrows():
        peer_pool = peer_rows.loc[
            peer_rows["cost_category"].eq(
                target["cost_category"]
            )
            & peer_rows[
                "annualized_cost_per_household_krw"
            ].notna()
        ]

        peer_values = peer_pool[
            "annualized_cost_per_household_krw"
        ].astype(float)

        peer_count = len(peer_values)

        if peer_count > 0:
            peer_mean = float(peer_values.mean())
            peer_median = float(peer_values.median())
            peer_q1 = float(peer_values.quantile(0.25))
            peer_q3 = float(peer_values.quantile(0.75))
        else:
            peer_mean = None
            peer_median = None
            peer_q1 = None
            peer_q3 = None

        target_value = target[
            "annualized_cost_per_household_krw"
        ]

        if pd.isna(target_value):
            benchmark_status = "TARGET_UNUSABLE"

        elif peer_count < MIN_PEER_COUNT:
            benchmark_status = "INSUFFICIENT_PEERS"

        else:
            benchmark_status = "BENCHMARK_READY"

        percentile = (
            calculate_percentile(
                target_value,
                peer_values,
            )
            if benchmark_status == "BENCHMARK_READY"
            else None
        )

        outlier_status = classify_outlier(
            target_value,
            peer_q1,
            peer_q3,
        )

        if (
            benchmark_status == "BENCHMARK_READY"
            and peer_median is not None
            and peer_median != 0
        ):
            gap_krw = float(
                target_value - peer_median
            )
            gap_pct = float(
                gap_krw / peer_median * 100
            )

            indicative_excess_cost = (
                max(gap_krw, 0)
                * float(target["household_count"])
            )
        else:
            gap_krw = None
            gap_pct = None
            indicative_excess_cost = None

        if benchmark_status == "BENCHMARK_READY":
            positive_gap_pct = max(
                gap_pct or 0,
                0,
            )
            percentile_excess = max(
                (percentile or 0) - 50,
                0,
            )
            outlier_bonus = (
                10
                if outlier_status == "HIGH_OUTLIER"
                else 0
            )

            raw_score = min(
                positive_gap_pct,
                100,
            ) * 0.6

            raw_score += min(
                percentile_excess,
                50,
            ) * 0.6

            raw_score += outlier_bonus

            peer_confidence = min(
                peer_count / 30,
                1,
            )

            coverage_confidence = min(
                target["observed_month_count"] / 12,
                1,
            )

            opportunity_score = round(
                min(raw_score, 100)
                * peer_confidence
                * coverage_confidence,
                2,
            )
        else:
            opportunity_score = None

        if opportunity_score is None:
            priority_band = "NOT_ASSESSED"
        elif opportunity_score >= 70:
            priority_band = "HIGH"
        elif opportunity_score >= 40:
            priority_band = "MEDIUM"
        else:
            priority_band = "LOW"

        if (
            benchmark_status == "BENCHMARK_READY"
            and peer_count >= 30
            and target["observed_month_count"] == 12
            and target["partial_month_count"] == 0
        ):
            confidence_level = "HIGH"
        elif (
            benchmark_status == "BENCHMARK_READY"
            and peer_count >= 20
            and target["observed_month_count"]
            >= MIN_OBSERVED_MONTHS
        ):
            confidence_level = "MEDIUM"
        else:
            confidence_level = "LOW"

        benchmark_rows.append(
            {
                "apartment_id": target[
                    "apartment_id"
                ],
                "apartment_name": target[
                    "apartment_name"
                ],
                "cost_category": target[
                    "cost_category"
                ],
                "cost_category_name_ko": target[
                    "cost_category_name_ko"
                ],
                "observed_month_count": target[
                    "observed_month_count"
                ],
                "coverage_pct": target[
                    "coverage_pct"
                ],
                "annual_quality_status": target[
                    "annual_quality_status"
                ],
                "target_annualized_total_cost_krw": (
                    target[
                        "annualized_total_cost_krw"
                    ]
                ),
                "target_annualized_cost_per_household_krw": (
                    target_value
                ),
                "peer_count": peer_count,
                "peer_mean_annualized_cost_per_household_krw": (
                    peer_mean
                ),
                "peer_median_annualized_cost_per_household_krw": (
                    peer_median
                ),
                "peer_q1_annualized_cost_per_household_krw": (
                    peer_q1
                ),
                "peer_q3_annualized_cost_per_household_krw": (
                    peer_q3
                ),
                "target_gap_per_household_krw": (
                    gap_krw
                ),
                "target_gap_pct": gap_pct,
                "target_percentile": percentile,
                "outlier_status": outlier_status,
                "indicative_annual_excess_cost_krw": (
                    indicative_excess_cost
                ),
                "opportunity_score": (
                    opportunity_score
                ),
                "priority_band": priority_band,
                "confidence_level": confidence_level,
                "benchmark_status": benchmark_status,
            }
        )

    benchmark = pd.DataFrame(benchmark_rows)

    return benchmark.sort_values(
        by=[
            "opportunity_score",
            "cost_category",
        ],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)


def validate_and_save(
    monthly_features: pd.DataFrame,
    annual_features: pd.DataFrame,
    target_monthly: pd.DataFrame,
    target_annual: pd.DataFrame,
) -> None:
    outputs = [
        (
            monthly_features,
            MONTHLY_FEATURE_FILE,
        ),
        (
            annual_features,
            APARTMENT_ANNUAL_FILE,
        ),
        (
            target_monthly,
            TARGET_MONTHLY_BENCHMARK_FILE,
        ),
        (
            target_annual,
            TARGET_ANNUAL_BENCHMARK_FILE,
        ),
    ]

    for dataframe, output_file in outputs:
        output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        dataframe.to_csv(
            output_file,
            index=False,
            encoding="utf-8-sig",
        )

    monthly_duplicate_count = int(
        monthly_features.duplicated(
            subset=[
                "apartment_id",
                "search_month",
                "cost_category",
            ]
        ).sum()
    )

    annual_duplicate_count = int(
        annual_features.duplicated(
            subset=[
                "apartment_id",
                "cost_category",
            ]
        ).sum()
    )

    target_monthly_duplicate_count = int(
        target_monthly.duplicated(
            subset=[
                "search_month",
                "cost_category",
            ]
        ).sum()
    )

    target_annual_duplicate_count = int(
        target_annual.duplicated(
            subset=["cost_category"]
        ).sum()
    )

    minimum_annual_peer_count = int(
        target_annual["peer_count"].min()
    )

    benchmark_ready_count = int(
        target_annual["benchmark_status"]
        .eq("BENCHMARK_READY")
        .sum()
    )

    print(
        f"[OK] 월별 피처 수: "
        f"{len(monthly_features):,}"
    )
    print(
        f"[OK] 단지별 연간 피처 수: "
        f"{len(annual_features):,}"
    )
    print(
        f"[OK] 대상 월별 벤치마크 수: "
        f"{len(target_monthly):,}"
    )
    print(
        f"[OK] 대상 연간 벤치마크 수: "
        f"{len(target_annual):,}"
    )
    print(
        f"[QA] 월별 중복 키 수: "
        f"{monthly_duplicate_count:,}"
    )
    print(
        f"[QA] 연간 중복 키 수: "
        f"{annual_duplicate_count:,}"
    )
    print(
        f"[QA] 대상 월별 중복 키 수: "
        f"{target_monthly_duplicate_count:,}"
    )
    print(
        f"[QA] 대상 연간 중복 키 수: "
        f"{target_annual_duplicate_count:,}"
    )
    print(
        f"[QA] 연간 최소 비교단지 수: "
        f"{minimum_annual_peer_count:,}"
    )
    print(
        f"[QA] 분석 가능 비용항목 수: "
        f"{benchmark_ready_count:,}/6"
    )
    print(
        f"[OK] 월별 피처: {MONTHLY_FEATURE_FILE}"
    )
    print(
        f"[OK] 단지별 연간 피처: "
        f"{APARTMENT_ANNUAL_FILE}"
    )
    print(
        f"[OK] 대상 월별 벤치마크: "
        f"{TARGET_MONTHLY_BENCHMARK_FILE}"
    )
    print(
        f"[OK] 대상 연간 벤치마크: "
        f"{TARGET_ANNUAL_BENCHMARK_FILE}"
    )

    if len(monthly_features) != 3600:
        raise RuntimeError(
            "월별 피처 행 수가 3,600이 아닙니다."
        )

    if len(annual_features) != 300:
        raise RuntimeError(
            "단지별 연간 피처 행 수가 300이 아닙니다."
        )

    if len(target_monthly) != 72:
        raise RuntimeError(
            "대상 월별 벤치마크 행 수가 72가 아닙니다."
        )

    if len(target_annual) != 6:
        raise RuntimeError(
            "대상 연간 벤치마크 행 수가 6이 아닙니다."
        )

    total_duplicate_count = (
        monthly_duplicate_count
        + annual_duplicate_count
        + target_monthly_duplicate_count
        + target_annual_duplicate_count
    )

    if total_duplicate_count > 0:
        raise RuntimeError(
            "피처 테이블에 중복 키가 있습니다."
        )

    if minimum_annual_peer_count < MIN_PEER_COUNT:
        print(
            "[WARNING] 일부 비용항목의 비교단지가 "
            "10개 미만입니다."
        )

    print(
        "[SUCCESS] 관리비 벤치마크 피처를 생성했습니다."
    )


def main() -> None:
    monthly_features = load_inputs()

    target_monthly = (
        build_monthly_target_benchmark(
            monthly_features
        )
    )

    annual_features = (
        build_apartment_annual_features(
            monthly_features
        )
    )

    target_annual = (
        build_annual_target_benchmark(
            annual_features
        )
    )

    validate_and_save(
        monthly_features=monthly_features,
        annual_features=annual_features,
        target_monthly=target_monthly,
        target_annual=target_annual,
    )


if __name__ == "__main__":
    main()