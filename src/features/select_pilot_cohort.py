import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROFILE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "dim_apartment_profile_base.csv"
)

SHORTLIST_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "pilot_candidate_shortlist.csv"
)

COHORT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "pilot_cohort.csv"
)

CONFIG_FILE = PROJECT_ROOT / "configs" / "pilot.json"


def load_eligible_profiles() -> pd.DataFrame:
    if not PROFILE_FILE.exists():
        raise FileNotFoundError(
            f"단지 기본정보 파일이 없습니다: {PROFILE_FILE}"
        )

    df = pd.read_csv(
        PROFILE_FILE,
        dtype={"apartment_id": "string"},
    )

    required_columns = {
        "apartment_id",
        "apartment_name",
        "city_district",
        "household_count",
        "approval_year",
        "heating_type",
        "management_type",
        "profile_available",
    }

    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"필수 칼럼이 없습니다: {sorted(missing_columns)}"
        )

    df["apartment_id"] = (
        df["apartment_id"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    text_columns = [
        "apartment_name",
        "city_district",
        "heating_type",
        "management_type",
    ]

    for column in text_columns:
        df[column] = (
            df[column]
            .astype("string")
            .str.strip()
            .replace("", pd.NA)
        )

    numeric_columns = [
        "household_count",
        "approval_year",
        "building_count",
        "total_area_m2",
        "management_area_m2",
        "private_area_m2",
    ]

    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

    df["profile_available"] = (
        df["profile_available"]
        .astype("string")
        .str.lower()
        .eq("true")
    )

    eligibility = (
        df["profile_available"]
        & df["apartment_id"].notna()
        & df["apartment_name"].notna()
        & df["city_district"].notna()
        & df["household_count"].gt(0)
        & df["approval_year"].notna()
        & df["heating_type"].notna()
        & df["management_type"].notna()
    )

    eligible_df = df.loc[eligibility].copy()

    completeness_columns = [
        column
        for column in [
            "apartment_name",
            "city_district",
            "household_count",
            "approval_year",
            "heating_type",
            "management_type",
            "building_count",
            "total_area_m2",
            "road_address",
        ]
        if column in eligible_df.columns
    ]

    eligible_df["profile_completeness_pct"] = (
        eligible_df[completeness_columns]
        .notna()
        .mean(axis=1)
        .mul(100)
        .round(2)
    )

    if len(eligible_df) < 50:
        raise RuntimeError(
            "비교군 구성을 위한 유효 단지가 50개 미만입니다."
        )

    print(f"[INFO] 전체 단지 수: {len(df):,}")
    print(f"[INFO] 비교군 적격 단지 수: {len(eligible_df):,}")

    return eligible_df.reset_index(drop=True)


def calculate_differences(
    profiles: pd.DataFrame,
    target: pd.Series,
) -> pd.DataFrame:
    peers = profiles.loc[
        profiles["apartment_id"] != target["apartment_id"]
    ].copy()

    peers["household_diff_ratio"] = (
        peers["household_count"]
        .sub(target["household_count"])
        .abs()
        .div(target["household_count"])
    )

    peers["approval_year_diff"] = (
        peers["approval_year"]
        .sub(target["approval_year"])
        .abs()
    )

    peers["same_district"] = (
        peers["city_district"] == target["city_district"]
    )

    peers["same_heating_type"] = (
        peers["heating_type"] == target["heating_type"]
    )

    peers["same_management_type"] = (
        peers["management_type"] == target["management_type"]
    )

    return peers


def create_candidate_shortlist(
    profiles: pd.DataFrame,
    shortlist_size: int,
    desired_peer_count: int,
) -> pd.DataFrame:
    rankings: list[dict] = []
    total = len(profiles)

    for sequence, (_, target) in enumerate(
        profiles.iterrows(),
        start=1,
    ):
        peers = calculate_differences(profiles, target)

        strict_mask = (
            peers["same_district"]
            & peers["same_heating_type"]
            & peers["same_management_type"]
            & peers["household_diff_ratio"].le(0.30)
            & peers["approval_year_diff"].le(7)
        )

        expanded_mask = (
            peers["same_district"]
            & peers["same_heating_type"]
            & peers["same_management_type"]
            & peers["household_diff_ratio"].le(0.50)
            & peers["approval_year_diff"].le(10)
        )

        strict_peer_count = int(strict_mask.sum())
        expanded_peer_count = int(expanded_mask.sum())

        readiness_score = (
            min(strict_peer_count / desired_peer_count, 1) * 60
            + min(expanded_peer_count / desired_peer_count, 1) * 25
            + float(target["profile_completeness_pct"]) * 0.15
        )

        rankings.append(
            {
                "apartment_id": target["apartment_id"],
                "apartment_name": target["apartment_name"],
                "city_district": target["city_district"],
                "household_count": int(target["household_count"]),
                "approval_year": int(target["approval_year"]),
                "heating_type": target["heating_type"],
                "management_type": target["management_type"],
                "strict_peer_count": strict_peer_count,
                "expanded_peer_count": expanded_peer_count,
                "profile_completeness_pct": target[
                    "profile_completeness_pct"
                ],
                "readiness_score": round(readiness_score, 2),
            }
        )

        if sequence % 500 == 0 or sequence == total:
            print(
                f"[PROGRESS] 후보 평가 {sequence:,}/{total:,}"
            )

    shortlist = pd.DataFrame(rankings).sort_values(
        by=[
            "readiness_score",
            "strict_peer_count",
            "expanded_peer_count",
            "apartment_id",
        ],
        ascending=[False, False, False, True],
    )

    shortlist.insert(
        0,
        "candidate_rank",
        range(1, len(shortlist) + 1),
    )

    shortlist = shortlist.head(shortlist_size)

    SHORTLIST_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shortlist.to_csv(
        SHORTLIST_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"[OK] 후보 단지 수: {len(shortlist):,}")
    print(f"[OK] 후보 파일: {SHORTLIST_FILE}")

    return shortlist


def create_pilot_cohort(
    profiles: pd.DataFrame,
    target_id: str,
    peer_count: int,
) -> pd.DataFrame:
    target_id = target_id.strip().upper()

    target_rows = profiles.loc[
        profiles["apartment_id"] == target_id
    ]

    if target_rows.empty:
        raise ValueError(
            f"적격 단지에서 대상 코드를 찾을 수 없습니다: {target_id}"
        )

    target = target_rows.iloc[0]
    peers = calculate_differences(profiles, target)

    peers["match_tier"] = 7

    rules = [
        (
            1,
            "같은 자치구·난방·관리, 세대수 ±30%, 연도 ±7",
            (
                peers["same_district"]
                & peers["same_heating_type"]
                & peers["same_management_type"]
                & peers["household_diff_ratio"].le(0.30)
                & peers["approval_year_diff"].le(7)
            ),
        ),
        (
            2,
            "같은 자치구·난방·관리, 세대수 ±50%, 연도 ±10",
            (
                peers["same_district"]
                & peers["same_heating_type"]
                & peers["same_management_type"]
                & peers["household_diff_ratio"].le(0.50)
                & peers["approval_year_diff"].le(10)
            ),
        ),
        (
            3,
            "같은 자치구·난방, 세대수 ±50%, 연도 ±12",
            (
                peers["same_district"]
                & peers["same_heating_type"]
                & peers["household_diff_ratio"].le(0.50)
                & peers["approval_year_diff"].le(12)
            ),
        ),
        (
            4,
            "같은 자치구, 세대수 ±70%, 연도 ±15",
            (
                peers["same_district"]
                & peers["household_diff_ratio"].le(0.70)
                & peers["approval_year_diff"].le(15)
            ),
        ),
        (
            5,
            "서울 전체·같은 난방·관리, 세대수 ±50%, 연도 ±10",
            (
                peers["same_heating_type"]
                & peers["same_management_type"]
                & peers["household_diff_ratio"].le(0.50)
                & peers["approval_year_diff"].le(10)
            ),
        ),
        (
            6,
            "서울 전체·같은 난방, 세대수 ±100%, 연도 ±20",
            (
                peers["same_heating_type"]
                & peers["household_diff_ratio"].le(1.00)
                & peers["approval_year_diff"].le(20)
            ),
        ),
    ]

    rule_names = {
        1: rules[0][1],
        2: rules[1][1],
        3: rules[2][1],
        4: rules[3][1],
        5: rules[4][1],
        6: rules[5][1],
        7: "서울 전체 보완 비교군",
    }

    for tier, _, condition in rules:
        assign_mask = (
            peers["match_tier"].eq(7)
            & condition
        )
        peers.loc[assign_mask, "match_tier"] = tier

    peers["match_rule"] = peers["match_tier"].map(
        rule_names
    )

    peers["peer_distance_score"] = (
        peers["match_tier"].sub(1).mul(100)
        + peers["household_diff_ratio"].mul(50)
        + peers["approval_year_diff"].mul(2)
    ).round(4)

    similarity_penalty = (
        peers["household_diff_ratio"]
        .clip(upper=2)
        .mul(40)
        + peers["approval_year_diff"]
        .div(20)
        .clip(upper=1)
        .mul(30)
        + peers["match_tier"]
        .sub(1)
        .mul(5)
    )

    peers["similarity_score"] = (
        100 - similarity_penalty
    ).clip(lower=0).round(2)

    selected_peers = (
        peers.sort_values(
            by=[
                "match_tier",
                "peer_distance_score",
                "profile_completeness_pct",
                "apartment_id",
            ],
            ascending=[True, True, False, True],
        )
        .head(peer_count)
        .copy()
    )

    if len(selected_peers) < peer_count:
        raise RuntimeError(
            f"비교단지가 부족합니다: {len(selected_peers)}/{peer_count}"
        )

    selected_peers.insert(
        0,
        "peer_rank",
        range(1, len(selected_peers) + 1),
    )
    selected_peers.insert(0, "cohort_role", "PEER")

    target_row = target.to_frame().T
    target_row["cohort_role"] = "TARGET"
    target_row["peer_rank"] = 0
    target_row["match_tier"] = 0
    target_row["match_rule"] = "분석 대상 단지"
    target_row["household_diff_ratio"] = 0.0
    target_row["approval_year_diff"] = 0
    target_row["peer_distance_score"] = 0.0
    target_row["similarity_score"] = 100.0
    target_row["same_district"] = True
    target_row["same_heating_type"] = True
    target_row["same_management_type"] = True

    cohort = pd.concat(
        [target_row, selected_peers],
        ignore_index=True,
    )

    front_columns = [
        "cohort_role",
        "peer_rank",
        "apartment_id",
        "apartment_name",
        "city_district",
        "household_count",
        "approval_year",
        "heating_type",
        "management_type",
        "match_tier",
        "match_rule",
        "household_diff_ratio",
        "approval_year_diff",
        "similarity_score",
        "peer_distance_score",
    ]

    remaining_columns = [
        column
        for column in cohort.columns
        if column not in front_columns
    ]

    cohort = cohort[front_columns + remaining_columns]

    COHORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cohort.to_csv(
        COHORT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    CONFIG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    config = {
        "project": "K-APT AX Control Tower",
        "generated_at_kst": datetime.now(
            ZoneInfo("Asia/Seoul")
        ).isoformat(timespec="seconds"),
        "target": {
            "apartment_id": str(target["apartment_id"]),
            "apartment_name": str(target["apartment_name"]),
            "city_district": str(target["city_district"]),
            "household_count": int(target["household_count"]),
            "approval_year": int(target["approval_year"]),
            "heating_type": str(target["heating_type"]),
            "management_type": str(target["management_type"]),
        },
        "cohort": {
            "target_count": 1,
            "peer_count": peer_count,
            "total_count": len(cohort),
        },
        "selection_policy": {
            "primary_household_tolerance": 0.30,
            "primary_approval_year_tolerance": 7,
            "fallback_tiers_enabled": True,
            "ranking_direction": "lower_peer_distance_is_better",
        },
    }

    CONFIG_FILE.write_text(
        json.dumps(
            config,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"[OK] 대상 단지: "
        f"{target['apartment_name']} / {target['apartment_id']}"
    )
    print(f"[OK] 비교단지 수: {len(selected_peers):,}")
    print(f"[OK] 전체 코호트 수: {len(cohort):,}")
    print(f"[OK] 코호트 파일: {COHORT_FILE}")
    print(f"[OK] 설정 파일: {CONFIG_FILE}")
    print("[SUCCESS] 파일럿 비교군 구성을 완료했습니다.")

    return cohort


def main() -> None:
    parser = argparse.ArgumentParser(
        description="K-APT 파일럿 대상 및 비교군 선정"
    )

    parser.add_argument(
        "--target-id",
        help="분석 대상 K-APT 단지코드",
    )

    parser.add_argument(
        "--shortlist-size",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--peer-count",
        type=int,
        default=49,
    )

    args = parser.parse_args()
    profiles = load_eligible_profiles()

    if args.target_id:
        create_pilot_cohort(
            profiles=profiles,
            target_id=args.target_id,
            peer_count=args.peer_count,
        )
    else:
        create_candidate_shortlist(
            profiles=profiles,
            shortlist_size=args.shortlist_size,
            desired_peer_count=args.peer_count,
        )


if __name__ == "__main__":
    main()