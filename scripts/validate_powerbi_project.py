"""Validate the version-controlled Power BI project without opening Desktop.

The checks cover PBIR page/visual structure, semantic-model field references,
relationship endpoints, and the exported public portfolio snapshot.
Only the Python standard library is required.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "powerbi" / "KAPT_AX_Control_Tower.Report"
MODEL = ROOT / "powerbi" / "KAPT_AX_Control_Tower.SemanticModel" / "definition"
DATA = ROOT / "powerbi" / "data"

EXPECTED_PAGES = [
    "01 Executive Overview",
    "02 Peer Benchmark",
    "03 Cost Driver & Trend",
    "04 Anomaly Explorer",
    "05 Advisory Action Center",
    "00 Model QA",
]

GRAINS = {
    "dim_apartment_profile_base.csv": ("apartment_id",),
    "pilot_cohort.csv": ("apartment_id",),
    "dim_cost_category.csv": ("cost_category",),
    "fact_cost_features_monthly.csv": (
        "apartment_id",
        "search_month",
        "cost_category",
    ),
    "fact_apartment_cost_annual.csv": ("apartment_id", "cost_category"),
    "model_anomaly_scores_monthly.csv": (
        "apartment_id",
        "search_month",
        "cost_category",
    ),
    "model_expected_cost_range.csv": ("apartment_id", "cost_category"),
    "advisory_category_assessment.csv": ("recommendation_id",),
    "advisory_action_register.csv": ("action_id",),
    "advisory_evidence_requests.csv": ("evidence_request_id",),
    "model_peer_weights.csv": ("apartment_id",),
}


class QA:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.stats: Counter[str] = Counter()

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def warn(self, condition: bool, message: str) -> None:
        if not condition:
            self.warnings.append(message)


def parse_tmdl_model(qa: QA) -> dict[str, dict[str, set[str]]]:
    entities: dict[str, dict[str, set[str]]] = {}
    table_pattern = re.compile(r"^table\s+(?:'([^']+)'|([^\s]+))")
    field_pattern = re.compile(r"^\s+(column|measure)\s+(?:'([^']+)'|([^=\s]+))")

    for path in sorted((MODEL / "tables").glob("*.tmdl")):
        lines = path.read_text(encoding="utf-8-sig").splitlines()
        if not lines:
            continue
        match = table_pattern.match(lines[0])
        qa.require(match is not None, f"TMDL table declaration missing: {path}")
        if match is None:
            continue
        table = match.group(1) or match.group(2)
        entities[table] = {"columns": set(), "measures": set()}
        for line in lines[1:]:
            field = field_pattern.match(line)
            if field:
                kind, quoted, bare = field.groups()
                entities[table][f"{kind}s"].add(quoted or bare)

    qa.stats["model_tables"] = len(entities)
    qa.stats["model_columns"] = sum(len(v["columns"]) for v in entities.values())
    qa.stats["model_measures"] = sum(len(v["measures"]) for v in entities.values())
    return entities


def iter_field_refs(value: object):
    if isinstance(value, dict):
        for kind in ("Column", "Measure"):
            field = value.get(kind)
            if not isinstance(field, dict):
                continue
            entity = (
                field.get("Expression", {})
                .get("SourceRef", {})
                .get("Entity")
            )
            prop = field.get("Property")
            if entity and prop:
                yield kind, entity, prop
        for child in value.values():
            yield from iter_field_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_field_refs(child)


def validate_report(qa: QA, entities: dict[str, dict[str, set[str]]]) -> None:
    metadata = json.loads(
        (REPORT / "definition" / "pages" / "pages.json").read_text(encoding="utf-8")
    )
    page_order = metadata.get("pageOrder", [])
    qa.require(len(page_order) == len(set(page_order)), "pages.json has duplicate page IDs")

    page_names: list[str] = []
    visual_count = 0
    field_ref_count = 0
    for page_id in page_order:
        page_dir = REPORT / "definition" / "pages" / page_id
        page_path = page_dir / "page.json"
        qa.require(page_path.exists(), f"Page metadata missing: {page_id}")
        if not page_path.exists():
            continue
        page = json.loads(page_path.read_text(encoding="utf-8"))
        page_names.append(page.get("displayName", ""))
        qa.require(page.get("name") == page_id, f"Page folder/name mismatch: {page_id}")
        qa.require(page.get("width") == 1280 and page.get("height") == 720,
                   f"Unexpected canvas size: {page.get('displayName')}")

        visual_paths = sorted((page_dir / "visuals").glob("*/visual.json"))
        visual_count += len(visual_paths)
        for path in visual_paths:
            visual = json.loads(path.read_text(encoding="utf-8"))
            position = visual.get("position", {})
            x, y = position.get("x", 0), position.get("y", 0)
            width, height = position.get("width", 0), position.get("height", 0)
            qa.require(width > 0 and height > 0, f"Non-positive visual size: {path}")
            qa.require(x >= 0 and y >= 0 and x + width <= 1280 and y + height <= 720,
                       f"Visual outside canvas: {path}")
            for kind, entity, prop in iter_field_refs(visual):
                field_ref_count += 1
                qa.require(entity in entities, f"Unknown model entity {entity}: {path}")
                if entity in entities:
                    bucket = "columns" if kind == "Column" else "measures"
                    qa.require(prop in entities[entity][bucket],
                               f"Unknown {kind.lower()} {entity}[{prop}]: {path}")

    qa.require(page_names == EXPECTED_PAGES,
               f"Unexpected page order/names: {page_names}")
    qa.require(metadata.get("activePageName") == page_order[0],
               "The first page is not the active page")
    qa.require(
        json.loads(
            (REPORT / "definition" / "pages" / page_order[-1] / "page.json")
            .read_text(encoding="utf-8")
        ).get("visibility") == "HiddenInViewMode",
        "00 Model QA must be hidden in view mode",
    )
    qa.stats["report_pages"] = len(page_names)
    qa.stats["report_visuals"] = visual_count
    qa.stats["field_references"] = field_ref_count


def validate_relationships(qa: QA, entities: dict[str, dict[str, set[str]]]) -> None:
    text = (MODEL / "relationships.tmdl").read_text(encoding="utf-8-sig")
    endpoints = re.findall(r"^\s+(?:fromColumn|toColumn):\s+([^.]+)\.(.+)$", text, re.M)
    qa.require(len(endpoints) % 2 == 0, "Relationship endpoint count is not even")
    for entity, column in endpoints:
        qa.require(
            entity in entities and column in entities[entity]["columns"],
            f"Unknown relationship endpoint: {entity}.{column}",
        )
    qa.stats["relationships"] = len(endpoints) // 2


def sha256_variants(path: Path) -> set[str]:
    """Return hashes for Git LF and Windows-export CRLF representations."""
    content = path.read_bytes()
    crlf_content = content.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    return {
        hashlib.sha256(content).hexdigest(),
        hashlib.sha256(crlf_content).hexdigest(),
    }


def validate_snapshot(qa: QA) -> None:
    manifest_path = DATA / "snapshot_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    qa.require(manifest.get("contains_api_key") is False, "Manifest reports an API key")
    qa.require(manifest.get("contains_raw_api_response") is False,
               "Manifest reports a raw API response")
    qa.require(manifest.get("contains_personal_information") is False,
               "Manifest reports personal information")

    entries = {entry["file_name"]: entry for entry in manifest.get("files", [])}
    qa.require(set(entries) == set(GRAINS), "Manifest file set does not match QA contract")

    for filename, grain in GRAINS.items():
        path = DATA / filename
        qa.require(path.exists(), f"Snapshot file missing: {filename}")
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            qa.require(reader.fieldnames is not None, f"CSV header missing: {filename}")
            rows = list(reader)
        qa.require(len(rows) == entries[filename]["row_count"],
                   f"Row count mismatch: {filename}")
        qa.require(entries[filename]["sha256"] in sha256_variants(path),
                   f"SHA-256 mismatch: {filename}")
        keys = [tuple(row.get(column, "").strip() for column in grain) for row in rows]
        qa.require(all(all(value for value in key) for key in keys),
                   f"Blank grain key: {filename} {grain}")
        qa.require(len(keys) == len(set(keys)), f"Duplicate grain: {filename} {grain}")
        qa.stats["snapshot_rows"] += len(rows)

    with (DATA / "fact_cost_features_monthly.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        monthly = list(csv.DictReader(handle))
    months = sorted({row["search_month"] for row in monthly})
    qa.require(months == [f"2025{month:02d}" for month in range(7, 13)] +
               [f"2026{month:02d}" for month in range(1, 7)],
               f"Unexpected monthly coverage: {months}")
    qa.stats["snapshot_months"] = len(months)


def main() -> int:
    qa = QA()
    entities = parse_tmdl_model(qa)
    validate_report(qa, entities)
    validate_relationships(qa, entities)
    validate_snapshot(qa)

    print("[POWER BI PROJECT QA]")
    for name, value in sorted(qa.stats.items()):
        print(f"[STAT] {name}: {value:,}")
    for warning in qa.warnings:
        print(f"[WARNING] {warning}")
    for error in qa.errors:
        print(f"[ERROR] {error}")
    if qa.errors:
        print(f"[FAIL] {len(qa.errors)} error(s), {len(qa.warnings)} warning(s)")
        return 1
    print(f"[PASS] 0 errors, {len(qa.warnings)} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
