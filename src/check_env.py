import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

if not ENV_FILE.exists():
    raise FileNotFoundError(f".env 파일을 찾을 수 없습니다: {ENV_FILE}")

load_dotenv(ENV_FILE)

required_variables = [
    "DATA_GO_KR_SERVICE_KEY",
    "KAPT_LIST_ENDPOINT",
]

missing_variables = [
    name
    for name in required_variables
    if not os.getenv(name, "").strip()
]

if missing_variables:
    missing_text = ", ".join(missing_variables)
    raise RuntimeError(f".env에서 다음 값이 비어 있습니다: {missing_text}")

service_key = os.environ["DATA_GO_KR_SERVICE_KEY"].strip()
endpoint = os.environ["KAPT_LIST_ENDPOINT"].strip()

parsed_endpoint = urlparse(endpoint)

if parsed_endpoint.scheme not in {"http", "https"} or not parsed_endpoint.netloc:
    raise ValueError("KAPT_LIST_ENDPOINT가 올바른 URL이 아닙니다.")

if "serviceKey" in endpoint:
    raise ValueError(
        "Endpoint에 serviceKey를 포함하지 마세요. "
        "인증키는 DATA_GO_KR_SERVICE_KEY에만 저장해야 합니다."
    )

print("[OK] .env 파일 발견")
print(f"[OK] 인증키 로딩 완료: {len(service_key)}자")
print(f"[OK] Endpoint 로딩 완료: {parsed_endpoint.netloc}")
print("[SUCCESS] 환경변수 검증을 통과했습니다.")