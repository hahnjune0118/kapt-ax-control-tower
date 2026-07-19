import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv


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
    / "apt_profile_sample.json"
)

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
        "서울 전체 단지 목록을 찾을 수 없습니다: "
        f"{APARTMENT_LIST_FILE}"
    )


def extract_response_data(payload: dict) -> dict:
    response_data = payload.get("response", payload)

    if not isinstance(response_data, dict):
        raise RuntimeError("API 응답 구조가 올바르지 않습니다.")

    return response_data


def extract_item(payload: dict) -> dict:
    response_data = extract_response_data(payload)
    body = response_data.get("body", {})

    if not isinstance(body, dict):
        raise RuntimeError("API 응답의 body가 올바르지 않습니다.")

    item = body.get("item", {})

    if isinstance(item, list):
        item = item[0] if item else {}

    if not isinstance(item, dict) or not item:
        raise RuntimeError("API 응답에 단지 정보가 없습니다.")

    return item


def request_profile(
    operation: str,
    key_parameter_name: str,
    apartment_id: str,
) -> dict:
    url = f"{base_endpoint.rstrip('/')}/{operation}"

    params = {
        key_parameter_name: service_key,
        "kaptCode": apartment_id,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=(10, 30),
        )
    except requests.RequestException as exc:
        raise RuntimeError(
            f"{operation} 통신 실패: "
            f"{type(exc).__name__}"
        ) from None

    safe_preview = response.text[:500].replace(
        service_key,
        "[REDACTED]",
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"{operation} HTTP 오류: "
            f"{response.status_code}\n"
            f"{safe_preview}"
        )

    try:
        payload = response.json()
    except requests.exceptions.JSONDecodeError:
        raise RuntimeError(
            f"{operation}이 JSON이 아닌 응답을 반환했습니다.\n"
            f"{safe_preview}"
        ) from None

    response_data = extract_response_data(payload)
    header = response_data.get("header", {})

    result_code = str(header.get("resultCode", ""))
    result_message = str(header.get("resultMsg", ""))

    if result_code not in {"00", "0", "000"}:
        raise RuntimeError(
            f"{operation} API 오류: "
            f"{result_code} / {result_message}"
        )

    return payload


with APARTMENT_LIST_FILE.open(
    "r",
    encoding="utf-8",
) as file:
    apartment_list_payload = json.load(file)

list_response_data = extract_response_data(
    apartment_list_payload
)

list_body = list_response_data.get("body", {})
apartments = list_body.get("items", [])

if isinstance(apartments, dict):
    apartments = apartments.get("item", [])

if isinstance(apartments, dict):
    apartments = [apartments]

if not isinstance(apartments, list):
    apartments = []

target_apartment = next(
    (
        apartment
        for apartment in apartments
        if str(apartment.get("kaptCode", "")).strip()
    ),
    None,
)

if target_apartment is None:
    raise RuntimeError(
        "표본으로 사용할 단지를 찾지 못했습니다."
    )

target_apartment_id = str(
    target_apartment["kaptCode"]
).strip()

target_apartment_name = str(
    target_apartment.get("kaptName", "")
).strip()

print(
    f"[INFO] 표본 단지: "
    f"{target_apartment_name} / "
    f"{target_apartment_id}"
)

print("[INFO] 공동주택 기본정보를 요청합니다.")

basic_payload = request_profile(
    operation="getAphusBassInfoV4",
    key_parameter_name="serviceKey",
    apartment_id=target_apartment_id,
)

print("[OK] 기본정보 호출 성공")
print("[INFO] 공동주택 상세정보를 요청합니다.")

detail_payload = request_profile(
    operation="getAphusDtlInfoV4",
    key_parameter_name="ServiceKey",
    apartment_id=target_apartment_id,
)

print("[OK] 상세정보 호출 성공")

basic_item = extract_item(basic_payload)
detail_item = extract_item(detail_payload)

basic_apartment_id = str(
    basic_item.get("kaptCode", "")
).strip()

detail_apartment_id = str(
    detail_item.get("kaptCode", "")
).strip()

if basic_apartment_id != target_apartment_id:
    raise RuntimeError(
        "기본정보의 단지코드가 요청 단지와 다릅니다."
    )

if detail_apartment_id != target_apartment_id:
    raise RuntimeError(
        "상세정보의 단지코드가 요청 단지와 다릅니다."
    )

output_payload = {
    "metadata": {
        "source_system": "K-APT",
        "apartment_id": target_apartment_id,
        "apartment_name": target_apartment_name,
        "fetched_at_kst": datetime.now(
            ZoneInfo("Asia/Seoul")
        ).isoformat(timespec="seconds"),
        "basic_operation": "getAphusBassInfoV4",
        "detail_operation": "getAphusDtlInfoV4",
    },
    "basic_response": basic_payload,
    "detail_response": detail_payload,
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

print(f"[PROFILE] 단지명: {basic_item.get('kaptName')}")
print(f"[PROFILE] 세대수: {basic_item.get('kaptdaCnt')}")
print(f"[PROFILE] 난방방식: {basic_item.get('codeHeatNm')}")
print(f"[PROFILE] 관리방식: {basic_item.get('codeMgrNm')}")
print(f"[PROFILE] 사용승인일: {basic_item.get('kaptUsedate')}")
print(f"[PROFILE] 승강기수: {detail_item.get('kaptdEcnt')}")
print(f"[PROFILE] 경비인원: {detail_item.get('kaptdScnt')}")
print(f"[PROFILE] 청소인원: {detail_item.get('kaptdClcnt')}")
print(f"[OK] 원본 저장 위치: {OUTPUT_FILE}")
print("[SUCCESS] 공동주택 프로필 표본 수집 완료")