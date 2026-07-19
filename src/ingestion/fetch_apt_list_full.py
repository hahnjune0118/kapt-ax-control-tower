import json
import math
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

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "kapt"
    / "apt_list_seoul_full.json"
)

SIDO_CODE = "11"
PAGE_SIZE = 100

load_dotenv(ENV_FILE)

service_key = os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()
base_endpoint = os.getenv("KAPT_LIST_ENDPOINT", "").strip()

if not service_key:
    raise RuntimeError("DATA_GO_KR_SERVICE_KEY가 비어 있습니다.")

if not base_endpoint:
    raise RuntimeError("KAPT_LIST_ENDPOINT가 비어 있습니다.")

url = f"{base_endpoint.rstrip('/')}/getSidoAptList3"


def create_session() -> requests.Session:
    retry_policy = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_policy)

    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


def fetch_page(
    session: requests.Session,
    page_number: int,
) -> tuple[dict, list[dict]]:
    params = {
        "serviceKey": service_key,
        "sidoCode": SIDO_CODE,
        "pageNo": page_number,
        "numOfRows": PAGE_SIZE,
    }

    try:
        response = session.get(
            url,
            params=params,
            timeout=(10, 30),
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            f"{page_number}페이지 통신 실패: "
            f"{type(exc).__name__}"
        ) from None

    safe_preview = response.text[:500].replace(
        service_key,
        "[REDACTED]",
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"{page_number}페이지 HTTP 오류: "
            f"{response.status_code}\n{safe_preview}"
        )

    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError:
        raise RuntimeError(
            f"{page_number}페이지가 JSON이 아닙니다.\n"
            f"{safe_preview}"
        ) from None

    response_data = payload.get("response", payload)
    header = response_data.get("header", {})
    body = response_data.get("body", {})

    result_code = str(header.get("resultCode", ""))
    result_message = str(header.get("resultMsg", ""))

    if result_code != "00":
        raise RuntimeError(
            f"{page_number}페이지 API 오류: "
            f"{result_code} / {result_message}"
        )

    items = body.get("items", [])

    if isinstance(items, dict):
        items = items.get("item", [])

    if isinstance(items, dict):
        items = [items]

    if not isinstance(items, list):
        items = []

    return body, items


def main() -> None:
    all_items: list[dict] = []

    with create_session() as session:
        first_body, first_items = fetch_page(
            session=session,
            page_number=1,
        )

        total_count = int(
            first_body.get("totalCount", len(first_items))
        )

        total_pages = max(
            1,
            math.ceil(total_count / PAGE_SIZE),
        )

        all_items.extend(first_items)

        print(
            f"[PAGE] 1/{total_pages} "
            f"- 누적 {len(all_items):,}건"
        )

        for page_number in range(2, total_pages + 1):
            _, page_items = fetch_page(
                session=session,
                page_number=page_number,
            )

            all_items.extend(page_items)

            print(
                f"[PAGE] {page_number}/{total_pages} "
                f"- 누적 {len(all_items):,}건"
            )

            time.sleep(0.1)

    if len(all_items) != total_count:
        raise RuntimeError(
            f"수집 건수 불일치: "
            f"예상 {total_count:,}건, "
            f"실제 {len(all_items):,}건"
        )

    apartment_ids = [
        str(item.get("kaptCode", "")).strip()
        for item in all_items
    ]

    missing_id_count = sum(
        not apartment_id
        for apartment_id in apartment_ids
    )

    duplicate_id_count = (
        len(apartment_ids)
        - len(set(apartment_ids))
    )

    if missing_id_count:
        raise RuntimeError(
            f"단지코드 누락: {missing_id_count}건"
        )

    if duplicate_id_count:
        raise RuntimeError(
            f"단지코드 중복: {duplicate_id_count}건"
        )

    output_payload = {
        "header": {
            "resultCode": "00",
            "resultMsg": "NORMAL SERVICE.",
        },
        "body": {
            "items": all_items,
            "numOfRows": len(all_items),
            "pageNo": 1,
            "totalCount": total_count,
        },
        "metadata": {
            "source_system": "K-APT",
            "sido_code": SIDO_CODE,
            "fetched_at_kst": datetime.now(
                ZoneInfo("Asia/Seoul")
            ).isoformat(timespec="seconds"),
            "page_size": PAGE_SIZE,
            "page_count": total_pages,
        },
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output_payload,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"[QA] 예상 건수: {total_count:,}")
    print(f"[QA] 실제 건수: {len(all_items):,}")
    print(f"[QA] 단지코드 누락: {missing_id_count}")
    print(f"[QA] 단지코드 중복: {duplicate_id_count}")
    print(f"[OK] 저장 위치: {OUTPUT_FILE}")
    print("[SUCCESS] 서울 전체 단지 수집 완료")


if __name__ == "__main__":
    main()