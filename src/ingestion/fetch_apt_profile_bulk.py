import argparse
import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"

APARTMENT_LIST_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "kapt"
    / "apt_list_seoul_full.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "kapt"
    / "apt_profile_base.jsonl"
)

FAILURE_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "kapt"
    / "apt_profile_base_failures.csv"
)

OPERATION = "getAphusBassInfoV4"

load_dotenv(ENV_FILE)

service_key = os.getenv(
    "DATA_GO_KR_SERVICE_KEY",
    "",
).strip()

base_endpoint = os.getenv(
    "KAPT_BASIC_ENDPOINT",
    "",
).strip()

if not service_key:
    raise RuntimeError(
        "DATA_GO_KR_SERVICE_KEY가 비어 있습니다."
    )

if not base_endpoint:
    raise RuntimeError(
        "KAPT_BASIC_ENDPOINT가 비어 있습니다."
    )

if not APARTMENT_LIST_FILE.exists():
    raise FileNotFoundError(
        f"서울 단지 목록이 없습니다: {APARTMENT_LIST_FILE}"
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="이번 실행에서 수집할 최대 단지 수",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="API 호출 사이 대기시간(초)",
    )

    return parser.parse_args()


def create_session() -> requests.Session:
    retry_policy = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504,
        ],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry_policy
    )

    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def extract_response_data(payload: dict) -> dict:
    response_data = payload.get("response", payload)

    if not isinstance(response_data, dict):
        raise RuntimeError("API 응답 구조가 잘못됐습니다.")

    return response_data


def extract_item(payload: dict) -> dict:
    response_data = extract_response_data(payload)
    body = response_data.get("body", {})

    if not isinstance(body, dict):
        raise RuntimeError("API body 구조가 잘못됐습니다.")

    item = body.get("item", {})

    if isinstance(item, list):
        item = item[0] if item else {}

    if not isinstance(item, dict) or not item:
        raise RuntimeError("API 응답에 item이 없습니다.")

    return item


def load_apartments() -> list[dict]:
    with APARTMENT_LIST_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    response_data = extract_response_data(payload)
    body = response_data.get("body", {})
    items = body.get("items", [])

    if isinstance(items, dict):
        items = items.get("item", [])

    if isinstance(items, dict):
        items = [items]

    if not isinstance(items, list):
        raise RuntimeError("단지 목록 형식이 잘못됐습니다.")

    apartment_by_id: dict[str, dict] = {}

    for item in items:
        if not isinstance(item, dict):
            continue

        apartment_id = str(
            item.get("kaptCode", "")
        ).strip()

        if apartment_id and apartment_id not in apartment_by_id:
            apartment_by_id[apartment_id] = item

    if not apartment_by_id:
        raise RuntimeError("수집할 단지가 없습니다.")

    return list(apartment_by_id.values())


def load_completed_ids() -> set[str]:
    completed_ids: set[str] = set()

    if not OUTPUT_FILE.exists():
        return completed_ids

    with OUTPUT_FILE.open(
        "r",
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
                raise RuntimeError(
                    f"JSONL {line_number}번째 줄이 손상됐습니다."
                ) from None

            apartment_id = str(
                record
                .get("metadata", {})
                .get("apartment_id", "")
            ).strip()

            if apartment_id:
                completed_ids.add(apartment_id)

    return completed_ids


def fetch_profile(
    session: requests.Session,
    apartment_id: str,
) -> tuple[dict, dict]:
    url = f"{base_endpoint.rstrip('/')}/{OPERATION}"

    params = {
        "serviceKey": service_key,
        "kaptCode": apartment_id,
    }

    try:
        response = session.get(
            url,
            params=params,
            timeout=(10, 30),
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            f"통신 실패: {type(exc).__name__}"
        ) from None

    safe_preview = response.text[:500].replace(
        service_key,
        "[REDACTED]",
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"HTTP {response.status_code}: {safe_preview}"
        )

    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError:
        raise RuntimeError(
            f"JSON 응답이 아닙니다: {safe_preview}"
        ) from None

    response_data = extract_response_data(payload)
    header = response_data.get("header", {})

    result_code = str(
        header.get("resultCode", "")
    )

    result_message = str(
        header.get("resultMsg", "")
    )

    if result_code not in {"00", "0", "000"}:
        raise RuntimeError(
            f"API 오류 {result_code}: {result_message}"
        )

    item = extract_item(payload)

    returned_id = str(
        item.get("kaptCode", "")
    ).strip()

    if returned_id != apartment_id:
        raise RuntimeError(
            f"단지코드 불일치: {returned_id}"
        )

    return payload, item


def save_failures(
    failures: list[dict],
) -> None:
    FAILURE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "apartment_id",
        "apartment_name",
        "error_type",
        "error_message",
        "failed_at_kst",
    ]

    with FAILURE_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(failures)


def main() -> None:
    args = parse_arguments()

    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit는 1 이상이어야 합니다.")

    if args.delay < 0:
        raise ValueError("--delay는 0 이상이어야 합니다.")

    apartments = load_apartments()
    completed_ids = load_completed_ids()

    pending_apartments = [
        apartment
        for apartment in apartments
        if str(
            apartment.get("kaptCode", "")
        ).strip() not in completed_ids
    ]

    if args.limit is not None:
        pending_apartments = pending_apartments[
            :args.limit
        ]

    print(f"[INFO] 전체 단지 수: {len(apartments):,}")
    print(f"[INFO] 기존 완료 수: {len(completed_ids):,}")
    print(
        f"[INFO] 이번 실행 대상: "
        f"{len(pending_apartments):,}"
    )

    if not pending_apartments:
        print("[SUCCESS] 추가로 수집할 단지가 없습니다.")
        return

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    failures: list[dict] = []
    success_count = 0

    with create_session() as session:
        with OUTPUT_FILE.open(
            "a",
            encoding="utf-8",
        ) as output_file:
            for sequence, apartment in enumerate(
                pending_apartments,
                start=1,
            ):
                apartment_id = str(
                    apartment.get("kaptCode", "")
                ).strip()

                apartment_name = str(
                    apartment.get("kaptName", "")
                ).strip()

                try:
                    payload, item = fetch_profile(
                        session=session,
                        apartment_id=apartment_id,
                    )

                    record = {
                        "metadata": {
                            "source_system": "K-APT",
                            "operation": OPERATION,
                            "apartment_id": apartment_id,
                            "list_apartment_name": apartment_name,
                            "fetched_at_kst": datetime.now(
                                ZoneInfo("Asia/Seoul")
                            ).isoformat(timespec="seconds"),
                        },
                        "response": payload,
                    }

                    output_file.write(
                        json.dumps(
                            record,
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

                    output_file.flush()

                    completed_ids.add(apartment_id)
                    success_count += 1

                except RuntimeError as exc:
                    failures.append(
                        {
                            "apartment_id": apartment_id,
                            "apartment_name": apartment_name,
                            "error_type": type(exc).__name__,
                            "error_message": str(exc)[:300],
                            "failed_at_kst": datetime.now(
                                ZoneInfo("Asia/Seoul")
                            ).isoformat(timespec="seconds"),
                        }
                    )

                if (
                    sequence == 1
                    or sequence % 25 == 0
                    or sequence == len(pending_apartments)
                ):
                    print(
                        f"[PROGRESS] "
                        f"{sequence:,}/"
                        f"{len(pending_apartments):,} "
                        f"- 성공 {success_count:,}, "
                        f"실패 {len(failures):,}"
                    )

                time.sleep(args.delay)

    save_failures(failures)

    coverage_rate = (
        len(completed_ids)
        / len(apartments)
        * 100
    )

    print(f"[RESULT] 이번 성공: {success_count:,}")
    print(f"[RESULT] 이번 실패: {len(failures):,}")
    print(f"[RESULT] 누적 저장: {len(completed_ids):,}")
    print(f"[RESULT] 커버리지: {coverage_rate:.2f}%")
    print(f"[OK] 원본 파일: {OUTPUT_FILE}")
    print(f"[OK] 실패 파일: {FAILURE_FILE}")

    if failures:
        print(
            "[WARNING] 실패한 단지가 있습니다. "
            "같은 명령을 다시 실행하면 실패 건만 재시도합니다."
        )
        raise SystemExit(1)

    print("[SUCCESS] 단지 기본정보 수집 완료")


if __name__ == "__main__":
    main()