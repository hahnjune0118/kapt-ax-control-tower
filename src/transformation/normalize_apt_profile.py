import json
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROFILE_JSONL = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "kapt"
    / "apt_profile_base.jsonl"
)

APARTMENT_DIM_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "dim_apartment.csv"
)

OUTPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "dim_apartment_profile_base.csv"
)


def clean_value(value: Any) -> str | None:
    """API 값의 공백·null 문자열을 정리합니다."""
    if value is None:
        return None

    text = str(value).strip()

    if text.lower() in {"", "none", "null", "nan"}:
        return None

    return text


def find_profile_payload(value: Any) -> dict[str, Any] | None:
    """
    JSONL 저장 구조가 바뀌어도 K-APT 기본정보 객체를 탐색합니다.
    """

    if isinstance(value, dict):
        # 우선 자주 사용하는 중첩 구조를 탐색합니다.
        for key in (
            "item",
            "profile",
            "data",
            "raw_item",
            "raw",
            "response",
            "body",
            "items",
        ):
            if key in value:
                found = find_profile_payload(value[key])
                if found is not None:
                    return found

        # K-APT 기본정보 필드를 가진 객체인지 확인합니다.
        profile_keys = {
            "kaptCode",
            "kaptName",
            "kaptdaCnt",
            "kaptUsedate",
            "codeHeatNm",
        }

        if profile_keys.intersection(value.keys()):
            return value

        # 기타 중첩 객체를 탐색합니다.
        for nested_value in value.values():
            found = find_profile_payload(nested_value)
            if found is not None:
                return found

    if isinstance(value, list):
        for element in value:
            found = find_profile_payload(element)
            if found is not None:
                return found

    return None


def choose_value(
    item: dict[str, Any],
    record: dict[str, Any],
    *keys: str,
) -> str | None:
    """프로필 객체와 외부 저장 객체에서 첫 번째 유효 값을 찾습니다."""

    for source in (item, record):
        for key in keys:
            value = clean_value(source.get(key))

            if value is not None:
                return value

    return None


def read_profile_jsonl() -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    with PROFILE_JSONL.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"JSONL {line_number}번째 줄을 읽을 수 없습니다: {error}"
                ) from error

            item = find_profile_payload(record)

            if item is None:
                print(
                    f"[WARNING] {line_number}번째 줄에서 "
                    "기본정보 객체를 찾지 못했습니다."
                )
                continue

            apartment_id = choose_value(
                item,
                record,
                "kaptCode",
                "apartment_id",
            )

            if apartment_id is None:
                print(
                    f"[WARNING] {line_number}번째 줄에 "
                    "단지코드가 없어 제외합니다."
                )
                continue

            rows.append(
                {
                    "apartment_id": apartment_id,
                    "profile_apartment_name": choose_value(
                        item,
                        record,
                        "kaptName",
                        "apartment_name",
                    ),
                    "lot_address": choose_value(
                        item,
                        record,
                        "kaptAddr",
                    ),
                    "road_address": choose_value(
                        item,
                        record,
                        "doroJuso",
                    ),
                    "sale_type": choose_value(
                        item,
                        record,
                        "codeSaleNm",
                    ),
                    "heating_type": choose_value(
                        item,
                        record,
                        "codeHeatNm",
                    ),
                    "management_type": choose_value(
                        item,
                        record,
                        "codeMgrNm",
                    ),
                    "hall_type": choose_value(
                        item,
                        record,
                        "codeHallNm",
                    ),
                    "total_area_m2": choose_value(
                        item,
                        record,
                        "kaptTarea",
                    ),
                    "management_area_m2": choose_value(
                        item,
                        record,
                        "kaptMarea",
                    ),
                    "private_area_m2": choose_value(
                        item,
                        record,
                        "privArea",
                    ),
                    "building_count": choose_value(
                        item,
                        record,
                        "kaptDongCnt",
                    ),
                    "household_count": choose_value(
                        item,
                        record,
                        "kaptdaCnt",
                        "hoCnt",
                    ),
                    "households_under_60m2": choose_value(
                        item,
                        record,
                        "kaptMparea60",
                    ),
                    "households_60_to_85m2": choose_value(
                        item,
                        record,
                        "kaptMparea85",
                    ),
                    "households_85_to_135m2": choose_value(
                        item,
                        record,
                        "kaptMparea135",
                    ),
                    "households_over_135m2": choose_value(
                        item,
                        record,
                        "kaptMparea136",
                    ),
                    "approval_date": choose_value(
                        item,
                        record,
                        "kaptUsedate",
                    ),
                    "max_floor": choose_value(
                        item,
                        record,
                        "kaptTopFloor",
                    ),
                    "basement_floor": choose_value(
                        item,
                        record,
                        "kaptBaseFloor",
                    ),
                    "construction_company": choose_value(
                        item,
                        record,
                        "kaptBcompany",
                    ),
                    "management_company": choose_value(
                        item,
                        record,
                        "kaptAcompany",
                    ),
                    "profile_available": True,
                    "profile_source_system": "K-APT_BASIC_V4",
                    "profile_loaded_at_kst": choose_value(
                        item,
                        record,
                        "fetched_at_kst",
                        "loaded_at_kst",
                        "collected_at_kst",
                    ),
                }
            )

    if not rows:
        raise RuntimeError("정규화할 기본정보 레코드가 없습니다.")

    return pd.DataFrame(rows)


def main() -> None:
    if not PROFILE_JSONL.exists():
        raise FileNotFoundError(
            f"프로필 원본 파일이 없습니다: {PROFILE_JSONL}"
        )

    if not APARTMENT_DIM_CSV.exists():
        raise FileNotFoundError(
            f"단지 마스터 파일이 없습니다: {APARTMENT_DIM_CSV}"
        )

    apartment_df = pd.read_csv(
        APARTMENT_DIM_CSV,
        dtype={"apartment_id": "string"},
    )

    profile_df = read_profile_jsonl()

    apartment_df["apartment_id"] = (
        apartment_df["apartment_id"].astype("string").str.strip()
    )

    profile_df["apartment_id"] = (
        profile_df["apartment_id"].astype("string").str.strip()
    )

    duplicate_count = int(
        profile_df.duplicated(
            subset=["apartment_id"],
            keep="last",
        ).sum()
    )

    profile_df = profile_df.drop_duplicates(
        subset=["apartment_id"],
        keep="last",
    )

    numeric_columns = [
        "total_area_m2",
        "management_area_m2",
        "private_area_m2",
        "building_count",
        "household_count",
        "households_under_60m2",
        "households_60_to_85m2",
        "households_85_to_135m2",
        "households_over_135m2",
        "max_floor",
        "basement_floor",
    ]

    for column in numeric_columns:
        profile_df[column] = pd.to_numeric(
            profile_df[column],
            errors="coerce",
        )

    integer_columns = [
        "building_count",
        "household_count",
        "households_under_60m2",
        "households_60_to_85m2",
        "households_85_to_135m2",
        "households_over_135m2",
        "max_floor",
        "basement_floor",
    ]

    for column in integer_columns:
        profile_df[column] = (
            profile_df[column].round().astype("Int64")
        )

    raw_approval_date = (
        profile_df["approval_date"]
        .astype("string")
        .str.strip()
    )

    profile_df["approval_date"] = pd.to_datetime(
        raw_approval_date,
        format="mixed",
        errors="coerce",
    )

    profile_df["approval_year"] = (
        profile_df["approval_date"].dt.year.astype("Int64")
    )

    current_kst = datetime.now(
        ZoneInfo("Asia/Seoul")
    ).isoformat(timespec="seconds")

    profile_df["profile_loaded_at_kst"] = (
        profile_df["profile_loaded_at_kst"].fillna(current_kst)
    )

    result_df = apartment_df.merge(
        profile_df,
        on="apartment_id",
        how="left",
        validate="one_to_one",
    )

    result_df["profile_available"] = (
        result_df["profile_available"].eq(True)
    )

    matched_count = int(result_df["profile_available"].sum())
    total_count = len(result_df)
    unmatched_count = total_count - matched_count
    match_rate = matched_count / total_count * 100

    # Power BI에서 날짜 형식을 쉽게 인식하도록 변환합니다.
    result_df["approval_date"] = (
        result_df["approval_date"].dt.strftime("%Y-%m-%d")
    )

    OUTPUT_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_df.to_csv(
        OUTPUT_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"[OK] 전체 단지 수: {total_count:,}")
    print(f"[OK] 기본정보 고유 수: {len(profile_df):,}")
    print(f"[QA] 중복 제거 수: {duplicate_count:,}")
    print(f"[QA] 기본정보 연결 수: {matched_count:,}")
    print(f"[QA] 미연결 단지 수: {unmatched_count:,}")
    print(f"[QA] 매칭률: {match_rate:.2f}%")
    print(f"[OK] CSV 저장 위치: {OUTPUT_CSV}")

    unmatched = result_df.loc[
        ~result_df["profile_available"],
        ["apartment_id", "apartment_name"],
    ]

    if not unmatched.empty:
        print("[INFO] 미연결 단지:")
        print(unmatched.to_string(index=False))

    if match_rate < 98:
        raise RuntimeError(
            f"기본정보 매칭률이 기준 미달입니다: {match_rate:.2f}%"
        )

    print("[SUCCESS] Power BI용 단지 기본정보를 생성했습니다.")


if __name__ == "__main__":
    main()