import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SOURCE_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "powerbi"
    / "data"
)

MANIFEST_FILE = (
    OUTPUT_DIR
    / "snapshot_manifest.json"
)


SNAPSHOT_FILES = {
    "dim_apartment_profile_base.csv": 3384,
    "pilot_cohort.csv": 50,
    "dim_cost_category.csv": 6,
    "fact_cost_features_monthly.csv": 3600,
    "fact_apartment_cost_annual.csv": 300,
    "model_anomaly_scores_monthly.csv": 72,
    "model_expected_cost_range.csv": 6,
    "advisory_category_assessment.csv": 6,
    "advisory_action_register.csv": 18,
    "advisory_evidence_requests.csv": 24,
    "model_peer_weights.csv": 49,
}


def calculate_sha256(
    file_path: Path,
) -> str:
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest_files = []

    for file_name, expected_rows in (
        SNAPSHOT_FILES.items()
    ):
        source = SOURCE_DIR / file_name
        destination = OUTPUT_DIR / file_name

        if not source.exists():
            raise FileNotFoundError(
                f"Power BI 원본 파일이 없습니다: {source}"
            )

        dataframe = pd.read_csv(source)

        actual_rows = len(dataframe)

        if actual_rows != expected_rows:
            raise ValueError(
                f"{file_name} 행 수가 예상과 다릅니다. "
                f"예상 {expected_rows:,}, 실제 {actual_rows:,}"
            )

        shutil.copy2(
            source,
            destination,
        )

        manifest_files.append(
            {
                "file_name": file_name,
                "row_count": actual_rows,
                "sha256": calculate_sha256(
                    destination
                ),
            }
        )

        print(
            f"[OK] {file_name}: "
            f"{actual_rows:,}행"
        )

    manifest = {
        "project": "K-APT AX Control Tower",
        "snapshot_type": (
            "PUBLIC_PORTFOLIO_DATA"
        ),
        "generated_at_kst": datetime.now(
            ZoneInfo("Asia/Seoul")
        ).isoformat(timespec="seconds"),
        "contains_api_key": False,
        "contains_raw_api_response": False,
        "contains_personal_information": False,
        "files": manifest_files,
    }

    MANIFEST_FILE.write_text(
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"[OK] 매니페스트: {MANIFEST_FILE}")
    print(
        "[SUCCESS] Power BI 공개 스냅샷을 생성했습니다."
    )


if __name__ == "__main__":
    main()