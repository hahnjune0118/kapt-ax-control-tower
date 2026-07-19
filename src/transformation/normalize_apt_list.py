import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "kapt"
    / "apt_list_seoul_sample.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "dim_apartment_sample.csv"
)

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"원본 JSON 파일을 찾을 수 없습니다: {INPUT_FILE}"
    )

with INPUT_FILE.open("r", encoding="utf-8") as file:
    payload = json.load(file)

response_data = payload.get("response", payload)
body = response_data.get("body", {})
items = body.get("items", [])

if isinstance(items, dict):
    items = items.get("item", [])

if isinstance(items, dict):
    items = [items]

if not isinstance(items, list) or not items:
    raise RuntimeError("원본 JSON에 아파트 목록이 없습니다.")

raw_df = pd.DataFrame(items)

source_columns = [
    "kaptCode",
    "kaptName",
    "as1",
    "as2",
    "as3",
    "as4",
    "bjdCode",
]

missing_columns = [
    column
    for column in source_columns
    if column not in raw_df.columns
]

if missing_columns:
    raise RuntimeError(
        f"필수 컬럼이 없습니다: {', '.join(missing_columns)}"
    )

apartment_df = raw_df[source_columns].rename(
    columns={
        "kaptCode": "apartment_id",
        "kaptName": "apartment_name",
        "as1": "province",
        "as2": "city_district",
        "as3": "town",
        "as4": "village",
        "bjdCode": "legal_dong_code",
    }
)

text_columns = [
    "apartment_id",
    "apartment_name",
    "province",
    "city_district",
    "town",
    "village",
    "legal_dong_code",
]

for column in text_columns:
    apartment_df[column] = (
        apartment_df[column]
        .astype("string")
        .str.strip()
        .replace("", pd.NA)
    )

if apartment_df["apartment_id"].isna().any():
    raise RuntimeError("단지코드가 비어 있는 행이 있습니다.")

apartment_df["legal_dong_code"] = (
    apartment_df["legal_dong_code"]
    .str.replace(r"\.0$", "", regex=True)
    .str.zfill(10)
)

duplicate_count = int(
    apartment_df["apartment_id"].duplicated().sum()
)

apartment_df = apartment_df.drop_duplicates(
    subset=["apartment_id"],
    keep="first",
)

invalid_legal_dong_count = int(
    apartment_df["legal_dong_code"]
    .dropna()
    .str.fullmatch(r"\d{10}")
    .eq(False)
    .sum()
)

apartment_df["source_system"] = "K-APT"
apartment_df["loaded_at_kst"] = datetime.now(
    ZoneInfo("Asia/Seoul")
).isoformat(timespec="seconds")

apartment_df = apartment_df.sort_values(
    by=[
        "city_district",
        "town",
        "apartment_name",
    ],
    na_position="last",
).reset_index(drop=True)

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

apartment_df.to_csv(
    OUTPUT_FILE,
    index=False,
    encoding="utf-8-sig",
)

print(f"[OK] 원본 행 수: {len(raw_df)}")
print(f"[OK] 출력 행 수: {len(apartment_df)}")
print(f"[QA] 중복 단지코드 수: {duplicate_count}")
print(f"[QA] 잘못된 법정동코드 수: {invalid_legal_dong_count}")
print(f"[OK] CSV 저장 위치: {OUTPUT_FILE}")
print("[SUCCESS] Power BI용 단지 마스터를 생성했습니다.")