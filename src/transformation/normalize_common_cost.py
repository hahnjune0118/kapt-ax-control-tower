import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "kapt"
    / "common_cost_bulk.jsonl"
)

COHORT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "pilot_cohort.csv"
)

CONFIG_FILE = (
    PROJECT_ROOT
    / "configs"
    / "cost_collection.json"
)

FACT_MONTHLY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "fact_common_cost_monthly.csv"
)

FACT_COMPONENT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "fact_common_cost_component.csv"
)

DIM_CATEGORY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "dim_cost_category.csv"
)

DIM_MONTH_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "dim_month.csv"
)


CATEGORY_DEFINITIONS = {
    "labor": {
        "category_name_ko": "인건비",
        "display_order": 1,
        "components": {
            "pay": "급여",
            "sundryCost": "제수당",
            "bonus": "상여금",
            "pension": "퇴직금",
            "accidentPremium": "산재보험료",
            "employPremium": "고용보험료",
            "nationalPension": "국민연금",
            "healthPremium": "건강보험료",
            "welfareBenefit": "복리후생비",
        },
    },
    "cleaning": {
        "category_name_ko": "청소비",
        "display_order": 2,
        "components": {
            "cleanCost": "청소비",
        },
    },
    "guard": {
        "category_name_ko": "경비비",
        "display_order": 3,
        "components": {
            "guardCost": "경비비",
        },
    },
    "elevator": {
        "category_name_ko": "승강기유지비",
        "display_order": 4,
        "components": {
            "elevCost": "승강기유지비",
        },
    },
    "repairs": {
        "category_name_ko": "수선비",
        "display_order": 5,
        "components": {
            "lrefCost1": "수선비",
        },
    },
    "facility": {
        "category_name_ko": "시설유지비",
        "display_order": 6,
        "components": {
            "lrefCost2": "시설유지비",
        },
    },
}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    if text.lower() in {
        "",
        "none",
        "null",
        "nan",
        "-",
    }:
        return None

    return text


def parse_amount(value: Any) -> float | None:
    text = clean_text(value)

    if text is None:
        return None

    text = (
        text.replace(",", "")
        .replace("원", "")
        .replace(" ", "")
    )

    number = pd.to_numeric(
        text,
        errors="coerce",
    )

    if pd.isna(number):
        return None

    return float(number)


def load_config() -> tuple[list[str], set[str]]:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"수집 설정 파일이 없습니다: {CONFIG_FILE}"
        )

    config = json.loads(
        CONFIG_FILE.read_text(encoding="utf-8")
    )

    months = [
        str(value)
        for value in config.get("months", [])
    ]

    configured_categories = set(
        config.get("categories", {}).keys()
    )

    if len(months) != 12:
        raise ValueError(
            f"설정 파일의 대상 월이 12개가 아닙니다: {len(months)}"
        )

    defined_categories = set(
        CATEGORY_DEFINITIONS.keys()
    )

    if configured_categories != defined_categories:
        raise ValueError(
            "수집 설정과 정규화 비용항목이 일치하지 않습니다.\n"
            f"설정: {sorted(configured_categories)}\n"
            f"정의: {sorted(defined_categories)}"
        )

    return months, configured_categories


def load_cohort() -> pd.DataFrame:
    if not COHORT_FILE.exists():
        raise FileNotFoundError(
            f"파일럿 비교군 파일이 없습니다: {COHORT_FILE}"
        )

    cohort = pd.read_csv(
        COHORT_FILE,
        dtype={
            "apartment_id": "string",
            "cohort_role": "string",
        },
    )

    required_columns = {
        "apartment_id",
        "apartment_name",
        "cohort_role",
    }

    missing_columns = (
        required_columns - set(cohort.columns)
    )

    if missing_columns:
        raise ValueError(
            f"비교군 필수 칼럼이 없습니다: "
            f"{sorted(missing_columns)}"
        )

    cohort["apartment_id"] = (
        cohort["apartment_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    cohort = cohort.drop_duplicates(
        subset=["apartment_id"],
        keep="first",
    )

    if len(cohort) != 50:
        raise ValueError(
            f"비교군 단지 수가 50개가 아닙니다: {len(cohort)}"
        )

    return cohort[
        [
            "apartment_id",
            "apartment_name",
            "cohort_role",
        ]
    ].reset_index(drop=True)


def load_raw_records(
    months: list[str],
    valid_apartment_ids: set[str],
    valid_categories: set[str],
) -> tuple[pd.DataFrame, int, int]:
    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"공용관리비 원본 파일이 없습니다: {RAW_FILE}"
        )

    rows: list[dict[str, Any]] = []
    invalid_line_count = 0

    with RAW_FILE.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(
            file,
            start=1,
        ):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                invalid_line_count += 1
                print(
                    f"[WARNING] JSONL {line_number}번째 줄을 "
                    "읽지 못했습니다."
                )
                continue

            apartment_id = clean_text(
                record.get("apartment_id")
            )
            search_month = clean_text(
                record.get("search_month")
            )
            category = clean_text(
                record.get("cost_category")
            )

            if apartment_id is None:
                invalid_line_count += 1
                continue

            apartment_id = apartment_id.upper()

            if (
                apartment_id not in valid_apartment_ids
                or search_month not in months
                or category not in valid_categories
            ):
                continue

            rows.append(
                {
                    "apartment_id": apartment_id,
                    "search_month": search_month,
                    "cost_category": category,
                    "collection_status": clean_text(
                        record.get("status")
                    ),
                    "operation": clean_text(
                        record.get("operation")
                    ),
                    "collected_at_kst": clean_text(
                        record.get("collected_at_kst")
                    ),
                    "item": record.get("item"),
                    "_source_line": line_number,
                }
            )

    if not rows:
        raise RuntimeError(
            "현재 분석 기간에 해당하는 원본 레코드가 없습니다."
        )

    raw_df = pd.DataFrame(rows)

    key_columns = [
        "apartment_id",
        "search_month",
        "cost_category",
    ]

    duplicate_count = int(
        raw_df.duplicated(
            subset=key_columns,
            keep="last",
        ).sum()
    )

    raw_df = (
        raw_df.sort_values("_source_line")
        .drop_duplicates(
            subset=key_columns,
            keep="last",
        )
        .reset_index(drop=True)
    )

    return (
        raw_df,
        duplicate_count,
        invalid_line_count,
    )


def create_expected_grid(
    cohort: pd.DataFrame,
    months: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, str]] = []

    for _, apartment in cohort.iterrows():
        for search_month in months:
            for category in CATEGORY_DEFINITIONS:
                rows.append(
                    {
                        "apartment_id": apartment[
                            "apartment_id"
                        ],
                        "apartment_name": apartment[
                            "apartment_name"
                        ],
                        "cohort_role": apartment[
                            "cohort_role"
                        ],
                        "search_month": search_month,
                        "cost_category": category,
                    }
                )

    return pd.DataFrame(rows)


def normalize_records(
    merged_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    monthly_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []

    for _, row in merged_df.iterrows():
        apartment_id = row["apartment_id"]
        search_month = row["search_month"]
        category = row["cost_category"]

        definition = CATEGORY_DEFINITIONS[category]
        components = definition["components"]

        collection_status = clean_text(
            row.get("collection_status")
        )

        if collection_status is None:
            collection_status = "NOT_COLLECTED"

        item = row.get("item")

        if not isinstance(item, dict):
            item = {}

        source_apartment_id = clean_text(
            item.get("kaptCode")
        )
        source_search_month = clean_text(
            item.get("searchDate")
        )

        source_key_match = True

        if source_apartment_id is not None:
            source_key_match = (
                source_key_match
                and source_apartment_id.upper()
                == apartment_id
            )

        if source_search_month is not None:
            source_key_match = (
                source_key_match
                and source_search_month
                == search_month
            )

        parsed_amounts: list[float] = []
        invalid_component_count = 0

        for component_code, component_name in (
            components.items()
        ):
            raw_value = item.get(component_code)
            component_amount = parse_amount(raw_value)

            if collection_status == "SUCCESS":
                if component_amount is not None:
                    component_status = "OBSERVED"
                    parsed_amounts.append(
                        component_amount
                    )
                elif clean_text(raw_value) is not None:
                    component_status = "INVALID_NUMBER"
                    invalid_component_count += 1
                else:
                    component_status = "MISSING_COMPONENT"

            elif collection_status == "NO_DATA":
                component_status = "SOURCE_NO_DATA"

            else:
                component_status = "NOT_COLLECTED"

            component_rows.append(
                {
                    "apartment_id": apartment_id,
                    "search_month": search_month,
                    "month_start_date": (
                        f"{search_month[:4]}-"
                        f"{search_month[4:]}-01"
                    ),
                    "cost_category": category,
                    "cost_category_name_ko": definition[
                        "category_name_ko"
                    ],
                    "component_code": component_code,
                    "component_name_ko": component_name,
                    "component_amount_krw": (
                        component_amount
                    ),
                    "component_status": component_status,
                    "collection_status": (
                        collection_status
                    ),
                    "source_field": component_code,
                    "collected_at_kst": row.get(
                        "collected_at_kst"
                    ),
                }
            )

        expected_component_count = len(components)
        observed_component_count = len(parsed_amounts)

        if collection_status == "NO_DATA":
            cost_amount = None
            quality_status = "SOURCE_NO_DATA"

        elif collection_status != "SUCCESS":
            cost_amount = None
            quality_status = "NOT_COLLECTED"

        elif invalid_component_count > 0:
            cost_amount = (
                sum(parsed_amounts)
                if parsed_amounts
                else None
            )
            quality_status = "INVALID_NUMBER"

        elif observed_component_count == 0:
            cost_amount = None
            quality_status = "MISSING_AMOUNT"

        elif (
            observed_component_count
            < expected_component_count
        ):
            cost_amount = sum(parsed_amounts)
            quality_status = "PARTIAL_COMPONENTS"

        else:
            cost_amount = sum(parsed_amounts)
            quality_status = "OBSERVED"

        monthly_rows.append(
            {
                "apartment_id": apartment_id,
                "apartment_name": row[
                    "apartment_name"
                ],
                "cohort_role": row["cohort_role"],
                "search_month": search_month,
                "month_start_date": (
                    f"{search_month[:4]}-"
                    f"{search_month[4:]}-01"
                ),
                "year": int(search_month[:4]),
                "month": int(search_month[4:]),
                "cost_category": category,
                "cost_category_name_ko": definition[
                    "category_name_ko"
                ],
                "cost_amount_krw": cost_amount,
                "collection_status": collection_status,
                "data_quality_status": quality_status,
                "is_observed": cost_amount is not None,
                "is_negative_amount": (
                    cost_amount is not None
                    and cost_amount < 0
                ),
                "expected_component_count": (
                    expected_component_count
                ),
                "observed_component_count": (
                    observed_component_count
                ),
                "source_key_match": source_key_match,
                "source_system": (
                    "K-APT_COMMON_COST_V2"
                ),
                "operation": row.get("operation"),
                "collected_at_kst": row.get(
                    "collected_at_kst"
                ),
            }
        )

    return (
        pd.DataFrame(monthly_rows),
        pd.DataFrame(component_rows),
    )


def create_category_dimension() -> pd.DataFrame:
    rows = []

    for category, definition in (
        CATEGORY_DEFINITIONS.items()
    ):
        rows.append(
            {
                "cost_category": category,
                "cost_category_name_ko": definition[
                    "category_name_ko"
                ],
                "display_order": definition[
                    "display_order"
                ],
                "component_count": len(
                    definition["components"]
                ),
            }
        )

    return pd.DataFrame(rows)


def create_month_dimension(
    months: list[str],
) -> pd.DataFrame:
    rows = []

    for search_month in months:
        year = int(search_month[:4])
        month = int(search_month[4:])

        rows.append(
            {
                "search_month": search_month,
                "month_start_date": (
                    f"{year}-{month:02d}-01"
                ),
                "year": year,
                "quarter": f"Q{(month - 1) // 3 + 1}",
                "month": month,
                "year_month_label": (
                    f"{year}-{month:02d}"
                ),
                "display_order": year * 100 + month,
            }
        )

    return pd.DataFrame(rows)


def main() -> None:
    months, valid_categories = load_config()
    cohort = load_cohort()

    valid_apartment_ids = set(
        cohort["apartment_id"].tolist()
    )

    raw_df, duplicate_count, invalid_line_count = (
        load_raw_records(
            months=months,
            valid_apartment_ids=valid_apartment_ids,
            valid_categories=valid_categories,
        )
    )

    expected_df = create_expected_grid(
        cohort=cohort,
        months=months,
    )

    key_columns = [
        "apartment_id",
        "search_month",
        "cost_category",
    ]

    merged_df = expected_df.merge(
        raw_df[
            key_columns
            + [
                "collection_status",
                "operation",
                "collected_at_kst",
                "item",
            ]
        ],
        on=key_columns,
        how="left",
        validate="one_to_one",
    )

    fact_monthly, fact_component = (
        normalize_records(merged_df)
    )

    dim_category = create_category_dimension()
    dim_month = create_month_dimension(months)

    FACT_MONTHLY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fact_monthly.to_csv(
        FACT_MONTHLY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    fact_component.to_csv(
        FACT_COMPONENT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    dim_category.to_csv(
        DIM_CATEGORY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    dim_month.to_csv(
        DIM_MONTH_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    expected_count = (
        len(cohort)
        * len(months)
        * len(CATEGORY_DEFINITIONS)
    )

    collected_count = int(
        fact_monthly["collection_status"]
        .isin(["SUCCESS", "NO_DATA"])
        .sum()
    )

    collected_coverage = (
        collected_count / expected_count * 100
    )

    observed_count = int(
        fact_monthly["is_observed"].sum()
    )

    no_data_count = int(
        fact_monthly["data_quality_status"]
        .eq("SOURCE_NO_DATA")
        .sum()
    )

    partial_count = int(
        fact_monthly["data_quality_status"]
        .eq("PARTIAL_COMPONENTS")
        .sum()
    )

    missing_amount_count = int(
        fact_monthly["data_quality_status"]
        .eq("MISSING_AMOUNT")
        .sum()
    )

    not_collected_count = int(
        fact_monthly["data_quality_status"]
        .eq("NOT_COLLECTED")
        .sum()
    )

    invalid_number_count = int(
        fact_monthly["data_quality_status"]
        .eq("INVALID_NUMBER")
        .sum()
    )

    negative_amount_count = int(
        fact_monthly["is_negative_amount"].sum()
    )

    source_mismatch_count = int(
        (~fact_monthly["source_key_match"]).sum()
    )

    fact_duplicate_count = int(
        fact_monthly.duplicated(
            subset=key_columns
        ).sum()
    )

    print(f"[OK] 예상 팩트 행 수: {expected_count:,}")
    print(f"[OK] 실제 팩트 행 수: {len(fact_monthly):,}")
    print(f"[OK] 구성요소 행 수: {len(fact_component):,}")
    print(f"[OK] 비용항목 차원 수: {len(dim_category):,}")
    print(f"[OK] 월 차원 수: {len(dim_month):,}")
    print(f"[QA] 수집 커버리지: {collected_coverage:.2f}%")
    print(f"[QA] 금액 관측 수: {observed_count:,}")
    print(f"[QA] 원천 미공시 수: {no_data_count:,}")
    print(f"[QA] 부분 구성요소 수: {partial_count:,}")
    print(f"[QA] 금액 누락 수: {missing_amount_count:,}")
    print(f"[QA] 미수집 수: {not_collected_count:,}")
    print(f"[QA] 숫자 변환 실패 수: {invalid_number_count:,}")
    print(f"[QA] 음수 금액 수: {negative_amount_count:,}")
    print(f"[QA] 원천 키 불일치 수: {source_mismatch_count:,}")
    print(f"[QA] 원본 중복 제거 수: {duplicate_count:,}")
    print(f"[QA] 잘못된 JSONL 수: {invalid_line_count:,}")
    print(f"[QA] 팩트 중복 키 수: {fact_duplicate_count:,}")
    print(f"[OK] 월별 팩트: {FACT_MONTHLY_FILE}")
    print(f"[OK] 구성요소 팩트: {FACT_COMPONENT_FILE}")
    print(f"[OK] 비용항목 차원: {DIM_CATEGORY_FILE}")
    print(f"[OK] 월 차원: {DIM_MONTH_FILE}")

    if len(fact_monthly) != expected_count:
        raise RuntimeError(
            "월별 관리비 팩트 행 수가 예상과 다릅니다."
        )

    if fact_duplicate_count > 0:
        raise RuntimeError(
            "월별 관리비 팩트에 중복 키가 있습니다."
        )

    if source_mismatch_count > 0:
        raise RuntimeError(
            "요청 단지·월과 API 응답 키가 일치하지 않습니다."
        )

    if collected_coverage < 98:
        raise RuntimeError(
            f"수집 커버리지가 기준 미달입니다: "
            f"{collected_coverage:.2f}%"
        )

    print(
        "[SUCCESS] Power BI용 공용관리비 팩트를 "
        "생성했습니다."
    )


if __name__ == "__main__":
    main()