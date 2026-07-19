import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"
OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "kapt"
    / "apt_list_seoul_sample.json"
)

load_dotenv(ENV_FILE)

service_key = os.getenv("DATA_GO_KR_SERVICE_KEY", "").strip()
base_endpoint = os.getenv("KAPT_LIST_ENDPOINT", "").strip()

if not service_key:
    raise RuntimeError("DATA_GO_KR_SERVICE_KEY가 비어 있습니다.")

if not base_endpoint:
    raise RuntimeError("KAPT_LIST_ENDPOINT가 비어 있습니다.")

url = f"{base_endpoint.rstrip('/')}/getSidoAptList3"

params = {
    "serviceKey": service_key,
    "sidoCode": "11",
    "pageNo": 1,
    "numOfRows": 10,
}

print("[INFO] 서울 아파트 단지 목록을 요청합니다.")

try:
    response = requests.get(
        url,
        params=params,
        timeout=30,
    )
except requests.RequestException as exc:
    raise RuntimeError(
        f"API 통신에 실패했습니다: {type(exc).__name__}"
    ) from None

print(f"[INFO] HTTP 상태 코드: {response.status_code}")

safe_preview = response.text[:500].replace(
    service_key,
    "[REDACTED]",
)

if response.status_code != 200:
    raise RuntimeError(
        f"API 호출 실패\n"
        f"HTTP 상태 코드: {response.status_code}\n"
        f"응답 내용: {safe_preview}"
    )

try:
    payload = response.json()
except requests.exceptions.JSONDecodeError:
    raise RuntimeError(
        "API가 JSON이 아닌 응답을 반환했습니다.\n"
        f"응답 내용: {safe_preview}"
    ) from None

response_data = payload.get("response", payload)
header = response_data.get("header", {})
body = response_data.get("body", {})

result_code = str(header.get("resultCode", ""))
result_message = str(header.get("resultMsg", ""))

if result_code and result_code not in {"00", "0", "000"}:
    raise RuntimeError(
        f"공공데이터포털 오류: {result_code} / {result_message}"
    )

items = body.get("items", [])

if isinstance(items, dict):
    items = items.get("item", [])

if isinstance(items, dict):
    items = [items]

if not isinstance(items, list):
    items = []

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

with OUTPUT_FILE.open(
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        payload,
        file,
        ensure_ascii=False,
        indent=2,
    )

total_count = body.get("totalCount", len(items))

print(f"[OK] 전체 단지 수: {total_count}")
print(f"[OK] 이번 호출 수집 건수: {len(items)}")
print(f"[OK] 저장 위치: {OUTPUT_FILE}")

for index, item in enumerate(items[:3], start=1):
    print(
        f"[SAMPLE {index}] "
        f"{item.get('kaptName', '이름 없음')} / "
        f"{item.get('kaptCode', '코드 없음')}"
    )

print("[SUCCESS] K-apt 표본 데이터 수집을 완료했습니다.")