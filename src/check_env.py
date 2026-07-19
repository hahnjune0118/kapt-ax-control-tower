import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

KEY_NAME = "DATA_GO_KR_SERVICE_KEY"

ENDPOINT_NAMES = [
    "KAPT_LIST_ENDPOINT",
    "KAPT_BASIC_ENDPOINT",
    "KAPT_COMMON_COST_ENDPOINT",
]

if not ENV_FILE.exists():
    raise FileNotFoundError(
        f".env 파일을 찾을 수 없습니다: {ENV_FILE}"
    )

load_dotenv(ENV_FILE)

required_variables = [
    KEY_NAME,
    *ENDPOINT_NAMES,
]

missing_variables = [
    name
    for name in required_variables
    if not os.getenv(name, "").strip()
]

if missing_variables:
    raise RuntimeError(
        ".env에서 다음 값이 비어 있습니다: "
        + ", ".join(missing_variables)
    )

service_key = os.environ[KEY_NAME].strip()

if len(service_key) < 20:
    raise ValueError("공공데이터포털 인증키가 너무 짧습니다.")

print("[OK] .env 파일 발견")
print(f"[OK] 인증키 로딩 완료: {len(service_key)}자")

for endpoint_name in ENDPOINT_NAMES:
    endpoint = os.environ[endpoint_name].strip()
    parsed_endpoint = urlparse(endpoint)

    if (
        parsed_endpoint.scheme not in {"http", "https"}
        or not parsed_endpoint.netloc
    ):
        raise ValueError(
            f"{endpoint_name}가 올바른 URL이 아닙니다."
        )

    if "serviceKey" in endpoint or "ServiceKey" in endpoint:
        raise ValueError(
            f"{endpoint_name}에 인증키를 포함하면 안 됩니다."
        )

    print(
        f"[OK] {endpoint_name}: "
        f"{parsed_endpoint.netloc}{parsed_endpoint.path}"
    )

print("[SUCCESS] 전체 환경변수 검증을 통과했습니다.")