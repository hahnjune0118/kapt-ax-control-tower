import argparse
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = PROJECT_ROOT / ".env"

COHORT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "pilot_cohort.csv"
)

RAW_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "kapt"
    / "common_cost_bulk.jsonl"
)

FAILURE_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "kapt"
    / "common_cost_bulk_failures.csv"
)

CONFIG_FILE = (
    PROJECT_ROOT
    / "configs"
    / "cost_collection.json"
)

CATEGORIES = {
    "labor": "getHsmpLaborCostInfoV2",
    "cleaning": "getHsmpCleaningCostInfoV2",
    "guard": "getHsmpGuardCostInfoV2",
    "elevator": "getHsmpElevatorMntncCostInfoV2",
    "repairs": "getHsmpRepairsCostInfoV2",
    "facility": "getHsmpFacilityMntncCostInfoV2",
}

SUCCESS_CODES = {
    "",
    "0",
    "00",
    "0000",
    "NORMAL_CODE",
}

NO_DATA_CODES = {
    "03",
    "NODATA_ERROR",
    "INFO-200",
}

MAX_RETRIES = 4
DEFAULT_DELAY_SECONDS = 0.15


class RetryableApiError(RuntimeError):
    pass


class PermanentApiError(RuntimeError):
    pass


def current_kst() -> str:
    return datetime.now(
        ZoneInfo("Asia/Seoul")
    ).isoformat(timespec="seconds")


def validate_month(value: str) -> str:
    try:
        parsed = datetime.strptime(value, "%Y%m")
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "월은 YYYYMM 형식이어야 합니다."
        ) from error

    return parsed.strftime("%Y%m")


def shift_month(yyyymm: str, offset: int) -> str:
    year = int(yyyymm[:4])
    month = int(yyyymm[4:])

    total_month = year * 12 + month - 1 + offset
    shifted_year, shifted_month_index = divmod(
        total_month,
        12,
    )

    return f"{shifted_year}{shifted_month_index + 1:02d}"


def previous_month() -> str:
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    current = f"{now.year}{now.month:02d}"
    return shift_month(current, -1)


def create_months(
    end_month: str,
    month_count: int,
) -> list[str]:
    return [
        shift_month(end_month, offset)
        for offset in range(-(month_count - 1), 1)
    ]


def load_settings() -> tuple[str, str]:
    load_dotenv(ENV_FILE)

    service_key = os.getenv(
        "DATA_GO_KR_SERVICE_KEY",
        "",
    ).strip()

    base_endpoint = os.getenv(
        "KAPT_COMMON_COST_ENDPOINT",
        "",
    ).strip()

    if not service_key:
        raise ValueError(
            "DATA_GO_KR_SERVICE_KEY가 .env에 없습니다."
        )

    if not base_endpoint:
        raise ValueError(
            "KAPT_COMMON_COST_ENDPOINT가 .env에 없습니다."
        )

    parsed = urlparse(base_endpoint)

    if (
        parsed.scheme != "https"
        or parsed.netloc != "apis.data.go.kr"
    ):
        raise ValueError(
            "KAPT_COMMON_COST_ENDPOINT가 올바른 "
            "공공데이터포털 URL이 아닙니다."
        )

    return service_key, base_endpoint.rstrip("/")


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

    required = {
        "apartment_id",
        "apartment_name",
        "cohort_role",
    }

    missing = required - set(cohort.columns)

    if missing:
        raise ValueError(
            f"파일럿 비교군 필수 칼럼이 없습니다: {sorted(missing)}"
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
            f"파일럿 비교군이 50개가 아닙니다: {len(cohort)}"
        )

    return cohort.reset_index(drop=True)


def extract_item(
    payload: dict,
) -> dict | None:
    root = payload.get("response", payload)
    header = root.get("header") or {}

    result_code = str(
        header.get("resultCode", "")
    ).strip()

    result_message = str(
        header.get("resultMsg", "")
    ).strip()

    upper_message = result_message.upper()

    if (
        result_code in NO_DATA_CODES
        or "NO DATA" in upper_message
        or "데이터없" in result_message.replace(" ", "")
        or "데이터가없" in result_message.replace(" ", "")
    ):
        return None

    if result_code not in SUCCESS_CODES:
        raise PermanentApiError(
            f"API 응답 오류 {result_code}: "
            f"{result_message[:100]}"
        )

    body = root.get("body") or {}
    items = body.get("items")

    if isinstance(items, dict):
        item = items.get("item")
    else:
        item = items

    if item is None:
        item = body.get("item")

    if item in (None, "", []):
        return None

    if isinstance(item, list):
        if not item:
            return None

        for element in item:
            if isinstance(element, dict):
                return element

        return None

    if isinstance(item, dict):
        return item

    return None


def request_item(
    session: requests.Session,
    base_endpoint: str,
    service_key: str,
    operation: str,
    apartment_id: str,
    search_month: str,
) -> dict | None:
    endpoint = f"{base_endpoint}/{operation}"

    params = {
        "serviceKey": service_key,
        "kaptCode": apartment_id,
        "searchDate": search_month,
    }

    last_error = "알 수 없는 오류"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.get(
                endpoint,
                params=params,
                headers={"Accept": "application/json"},
                timeout=(10, 30),
            )
        except requests.RequestException as error:
            last_error = (
                f"네트워크 오류: {type(error).__name__}"
            )

            if attempt < MAX_RETRIES:
                time.sleep(2 ** (attempt - 1))
                continue

            raise RetryableApiError(last_error) from None

        status_code = response.status_code

        if status_code == 429 or status_code >= 500:
            last_error = f"재시도 가능 HTTP 오류: {status_code}"

            if attempt < MAX_RETRIES:
                time.sleep(2 ** (attempt - 1))
                continue

            raise RetryableApiError(last_error)

        if status_code != 200:
            raise PermanentApiError(
                f"HTTP 상태 코드: {status_code}"
            )

        try:
            payload = response.json()
        except ValueError:
            last_error = "JSON 응답 변환 실패"

            if attempt < MAX_RETRIES:
                time.sleep(2 ** (attempt - 1))
                continue

            raise RetryableApiError(last_error) from None

        return extract_item(payload)

    raise RetryableApiError(last_error)


def probe_latest_month(
    session: requests.Session,
    base_endpoint: str,
    service_key: str,
    target_id: str,
) -> str:
    start_month = previous_month()

    print(
        f"[INFO] 최신 가용 월 탐색 시작: {start_month}"
    )
    print(f"[INFO] 탐색 대상 단지: {target_id}")

    discovered_month: str | None = None

    for back_offset in range(18):
        search_month = shift_month(
            start_month,
            -back_offset,
        )

        print(f"[CHECK] {search_month}")

        for category, operation in CATEGORIES.items():
            try:
                item = request_item(
                    session=session,
                    base_endpoint=base_endpoint,
                    service_key=service_key,
                    operation=operation,
                    apartment_id=target_id,
                    search_month=search_month,
                )
            except RetryableApiError as error:
                print(
                    f"[WARNING] {category}: {error}"
                )
                continue
            except PermanentApiError as error:
                print(
                    f"[ERROR] {category}: {error}"
                )
                raise

            if item is not None:
                discovered_month = search_month
                print(
                    f"[FOUND] {search_month} / {category}"
                )
                break

        if discovered_month:
            break

    if discovered_month is None:
        raise RuntimeError(
            "최근 18개월에서 관리비 데이터를 찾지 못했습니다."
        )

    print("[INFO] 6개 API 동작 여부를 확인합니다.")

    for category, operation in CATEGORIES.items():
        try:
            item = request_item(
                session=session,
                base_endpoint=base_endpoint,
                service_key=service_key,
                operation=operation,
                apartment_id=target_id,
                search_month=discovered_month,
            )

            status = "DATA" if item is not None else "NO_DATA"

            print(
                f"[PROBE] {category}: {status}"
            )
        except (
            RetryableApiError,
            PermanentApiError,
        ) as error:
            print(
                f"[PROBE] {category}: FAIL / {error}"
            )

    print(
        f"[RESULT] 추천 종료월: {discovered_month}"
    )
    print(
        "[NEXT] 다음 명령의 YYYYMM을 추천 종료월로 바꾸세요."
    )
    print(
        "python src\\ingestion\\fetch_common_cost_bulk.py "
        f"--end-month {discovered_month}"
    )

    return discovered_month


def make_key(
    apartment_id: str,
    search_month: str,
    category: str,
) -> tuple[str, str, str]:
    return apartment_id, search_month, category


def load_completed_keys(
    retry_no_data: bool,
) -> set[tuple[str, str, str]]:
    completed: set[tuple[str, str, str]] = set()

    if not RAW_FILE.exists():
        return completed

    with RAW_FILE.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(
                    f"[WARNING] JSONL {line_number}번째 줄을 "
                    "읽지 못해 건너뜁니다."
                )
                continue

            status = record.get("status")

            if status == "SUCCESS":
                completed.add(
                    make_key(
                        record["apartment_id"],
                        record["search_month"],
                        record["cost_category"],
                    )
                )

            if status == "NO_DATA" and not retry_no_data:
                completed.add(
                    make_key(
                        record["apartment_id"],
                        record["search_month"],
                        record["cost_category"],
                    )
                )

    return completed


def write_collection_config(
    end_month: str,
    months: list[str],
    cohort_count: int,
    peer_count: int,
) -> None:
    config = {
        "project": "K-APT AX Control Tower",
        "generated_at_kst": current_kst(),
        "end_month": end_month,
        "months": months,
        "month_count": len(months),
        "apartment_count": cohort_count,
        "category_count": len(CATEGORIES),
        "expected_request_count": (
            cohort_count
            * len(months)
            * len(CATEGORIES)
        ),
        "categories": CATEGORIES,
        "request_policy": {
            "max_retries": MAX_RETRIES,
            "resume_enabled": True,
            "no_data_is_completed": True,
        },
        "cohort": {
            "target_count": 1,
            "peer_count": peer_count,
        },
    }

    CONFIG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    CONFIG_FILE.write_text(
        json.dumps(
            config,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def collect_costs(
    session: requests.Session,
    base_endpoint: str,
    service_key: str,
    cohort: pd.DataFrame,
    end_month: str,
    month_count: int,
    delay_seconds: float,
    retry_no_data: bool,
) -> None:
    months = create_months(
        end_month=end_month,
        month_count=month_count,
    )

    tasks: list[dict] = []

    for _, apartment in cohort.iterrows():
        for search_month in months:
            for category, operation in CATEGORIES.items():
                tasks.append(
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
                        "operation": operation,
                    }
                )

    task_keys = {
        make_key(
            task["apartment_id"],
            task["search_month"],
            task["cost_category"],
        )
        for task in tasks
    }

    completed_keys = (
        load_completed_keys(retry_no_data)
        & task_keys
    )

    pending_tasks = [
        task
        for task in tasks
        if make_key(
            task["apartment_id"],
            task["search_month"],
            task["cost_category"],
        )
        not in completed_keys
    ]

    print(f"[INFO] 수집 대상 월: {months[0]}~{months[-1]}")
    print(f"[INFO] 단지 수: {len(cohort):,}")
    print(f"[INFO] 전체 예상 건수: {len(tasks):,}")
    print(f"[INFO] 기존 완료 건수: {len(completed_keys):,}")
    print(f"[INFO] 이번 실행 대상: {len(pending_tasks):,}")

    RAW_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    failures: list[dict] = []
    success_count = 0
    no_data_count = 0

    with RAW_FILE.open(
        mode="a",
        encoding="utf-8",
    ) as output_file:
        for index, task in enumerate(
            pending_tasks,
            start=1,
        ):
            try:
                item = request_item(
                    session=session,
                    base_endpoint=base_endpoint,
                    service_key=service_key,
                    operation=task["operation"],
                    apartment_id=task["apartment_id"],
                    search_month=task["search_month"],
                )

                status = (
                    "SUCCESS"
                    if item is not None
                    else "NO_DATA"
                )

                record = {
                    **task,
                    "status": status,
                    "collected_at_kst": current_kst(),
                    "item": item,
                }

                output_file.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                output_file.flush()

                key = make_key(
                    task["apartment_id"],
                    task["search_month"],
                    task["cost_category"],
                )
                completed_keys.add(key)

                if status == "SUCCESS":
                    success_count += 1
                else:
                    no_data_count += 1

            except (
                RetryableApiError,
                PermanentApiError,
            ) as error:
                failures.append(
                    {
                        "apartment_id": task[
                            "apartment_id"
                        ],
                        "apartment_name": task[
                            "apartment_name"
                        ],
                        "search_month": task[
                            "search_month"
                        ],
                        "cost_category": task[
                            "cost_category"
                        ],
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                    }
                )

            if (
                index % 25 == 0
                or index == len(pending_tasks)
            ):
                print(
                    f"[PROGRESS] {index:,}/{len(pending_tasks):,}"
                    f" - 데이터 {success_count:,}"
                    f", 미공시 {no_data_count:,}"
                    f", 실패 {len(failures):,}"
                )

            if delay_seconds > 0:
                time.sleep(delay_seconds)

    failure_columns = [
        "apartment_id",
        "apartment_name",
        "search_month",
        "cost_category",
        "error_type",
        "error_message",
    ]

    with FAILURE_FILE.open(
        mode="w",
        encoding="utf-8-sig",
        newline="",
    ) as failure_file:
        writer = csv.DictWriter(
            failure_file,
            fieldnames=failure_columns,
        )
        writer.writeheader()
        writer.writerows(failures)

    coverage = (
        len(completed_keys) / len(tasks) * 100
        if tasks
        else 0
    )

    peer_count = int(
        cohort["cohort_role"]
        .astype("string")
        .str.upper()
        .eq("PEER")
        .sum()
    )

    write_collection_config(
        end_month=end_month,
        months=months,
        cohort_count=len(cohort),
        peer_count=peer_count,
    )

    print(f"[RESULT] 이번 데이터 성공: {success_count:,}")
    print(f"[RESULT] 이번 미공시: {no_data_count:,}")
    print(f"[RESULT] 이번 실패: {len(failures):,}")
    print(f"[RESULT] 누적 완료: {len(completed_keys):,}")
    print(f"[RESULT] 커버리지: {coverage:.2f}%")
    print(f"[OK] 원본 파일: {RAW_FILE}")
    print(f"[OK] 실패 파일: {FAILURE_FILE}")
    print(f"[OK] 설정 파일: {CONFIG_FILE}")

    if failures:
        print(
            "[WARNING] 실패 건이 있습니다. "
            "같은 명령을 다시 실행하면 실패 건만 재시도합니다."
        )
    else:
        print(
            "[SUCCESS] 12개월 공용관리비 수집을 완료했습니다."
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="K-APT 공용관리비 12개월 수집"
    )

    parser.add_argument(
        "--probe",
        action="store_true",
        help="최근 가용 월과 API 동작 여부만 확인",
    )

    parser.add_argument(
        "--end-month",
        type=validate_month,
        help="수집 종료월, 예: 202605",
    )

    parser.add_argument(
        "--months",
        type=int,
        default=12,
        help="수집 개월 수",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help="API 호출 사이 대기시간(초)",
    )

    parser.add_argument(
        "--retry-no-data",
        action="store_true",
        help="기존 NO_DATA 건도 다시 요청",
    )

    args = parser.parse_args()

    if args.months < 1:
        parser.error("--months는 1 이상이어야 합니다.")

    service_key, base_endpoint = load_settings()
    cohort = load_cohort()

    target_rows = cohort.loc[
        cohort["cohort_role"]
        .astype("string")
        .str.upper()
        .eq("TARGET")
    ]

    if len(target_rows) != 1:
        raise ValueError(
            "pilot_cohort.csv에 TARGET이 정확히 1개여야 합니다."
        )

    target_id = target_rows.iloc[0]["apartment_id"]

    with requests.Session() as session:
        if args.probe:
            probe_latest_month(
                session=session,
                base_endpoint=base_endpoint,
                service_key=service_key,
                target_id=target_id,
            )
            return

        if not args.end_month:
            parser.error(
                "--probe 또는 --end-month YYYYMM을 입력하세요."
            )

        collect_costs(
            session=session,
            base_endpoint=base_endpoint,
            service_key=service_key,
            cohort=cohort,
            end_month=args.end_month,
            month_count=args.months,
            delay_seconds=args.delay,
            retry_no_data=args.retry_no_data,
        )


if __name__ == "__main__":
    main()