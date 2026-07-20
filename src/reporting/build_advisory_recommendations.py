from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]

ANOMALY_SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "model_anomaly_summary.csv"
)

EXPECTED_RANGE_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "model_expected_cost_range.csv"
)

CATEGORY_ASSESSMENT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "advisory_category_assessment.csv"
)

ACTION_REGISTER_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "advisory_action_register.csv"
)

EVIDENCE_REQUEST_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "advisory_evidence_requests.csv"
)

EXECUTIVE_SUMMARY_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "powerbi"
    / "advisory_executive_summary.csv"
)

ADVISORY_BRIEF_FILE = (
    PROJECT_ROOT
    / "docs"
    / "reports"
    / "pilot_ax_advisory_brief.md"
)


ENGINE_VERSION = "advisory-engine-v1.0"


SIGNAL_NAMES = {
    "PEER_DEVIATION": "비교단지 대비 편차",
    "EXPECTED_RANGE_EXCESS": "기대비용 범위 초과",
    "TEMPORAL_INCREASE": "최근 비용 급등",
    "PERSISTENT_EXCESS": "고비용 지속",
}


CATEGORY_PLAYBOOKS = {
    "labor": {
        "pain_point": (
            "인건비가 유사단지 기대수준을 상회할 "
            "가능성"
        ),
        "hypotheses": [
            "세대수 대비 관리인원이 많을 가능성",
            "수당·상여·보험료 등 인건비 구성의 차이",
            "직영·위탁 운영방식 또는 근무체계의 차이",
        ],
        "evidence": [
            "최근 12개월 인건비 원장 및 예산 대비 실적",
            "관리인원 명부와 직무·근무시간·교대표",
            "관리업체 위수탁계약서와 인력 산정기준",
            "급여·수당·상여·보험료 항목별 집계표",
        ],
        "actions": [
            {
                "action_type": "VALIDATE",
                "title": "인건비 구성 및 인원 대사",
                "detail": (
                    "K-APT 공시금액을 인건비 원장, "
                    "급여대장 및 계약금액과 대사한다."
                ),
                "owner": "관리사무소 회계담당",
                "time_horizon": "0~30일",
                "kpi": "원장-공시 대사 차이율",
                "digital_enablement": (
                    "Python 자동대사 및 Power BI 차이 알림"
                ),
            },
            {
                "action_type": "OPTIMIZE",
                "title": "인력·근무체계 적정성 검토",
                "detail": (
                    "세대수당 인원, 교대방식, 직무중복과 "
                    "직영·위탁 시나리오를 비교한다."
                ),
                "owner": "관리사무소장·입주자대표회의",
                "time_horizon": "1~3개월",
                "kpi": "세대당 인건비 및 관리인원/1천세대",
                "digital_enablement": (
                    "인력운영 시나리오 시뮬레이션"
                ),
            },
            {
                "action_type": "CONTROL_AUTOMATE",
                "title": "인건비 월별 통제 대시보드",
                "detail": (
                    "예산, 실제, 비교군 중앙값과 "
                    "편차를 매월 모니터링한다."
                ),
                "owner": "관리사무소장",
                "time_horizon": "상시",
                "kpi": "비교군 대비 인건비 편차율",
                "digital_enablement": (
                    "Power BI 임계치 경보와 월별 보고 자동화"
                ),
            },
        ],
    },
    "cleaning": {
        "pain_point": (
            "청소용역 단가 또는 서비스 범위가 "
            "유사단지 대비 높을 가능성"
        ),
        "hypotheses": [
            "청소인원 또는 작업빈도가 높은 가능성",
            "계약단가와 실제 서비스 범위의 불일치",
            "경쟁입찰 또는 계약 갱신 과정의 비효율",
        ],
        "evidence": [
            "청소용역 계약서와 과업지시서",
            "청소인원·근무시간·작업구역 현황",
            "최근 입찰서류와 업체별 견적 비교표",
            "월별 검수조서 및 용역비 지급내역",
        ],
        "actions": [
            {
                "action_type": "VALIDATE",
                "title": "청소계약 단가·범위 대사",
                "detail": (
                    "계약서상 인원·시간·작업범위를 "
                    "실제 운영 및 지급내역과 대사한다."
                ),
                "owner": "관리사무소 계약담당",
                "time_horizon": "0~30일",
                "kpi": "계약범위 미이행 건수",
                "digital_enablement": (
                    "계약서 OCR 및 지급내역 자동대사"
                ),
            },
            {
                "action_type": "OPTIMIZE",
                "title": "청소용역 재견적·범위 최적화",
                "detail": (
                    "비교견적을 확보하고 작업빈도와 "
                    "구역별 서비스 수준을 재설계한다."
                ),
                "owner": "입주자대표회의",
                "time_horizon": "1~3개월",
                "kpi": "세대당 청소비 및 경쟁견적 수",
                "digital_enablement": (
                    "입찰 견적 비교 및 단가 벤치마크"
                ),
            },
            {
                "action_type": "CONTROL_AUTOMATE",
                "title": "청소용역 SLA 모니터링",
                "detail": (
                    "작업실적, 민원, 검수결과와 "
                    "비용을 월별로 연결한다."
                ),
                "owner": "관리사무소장",
                "time_horizon": "상시",
                "kpi": "SLA 준수율 및 청소민원 건수",
                "digital_enablement": (
                    "Power BI SLA·비용 통합 모니터링"
                ),
            },
        ],
    },
    "guard": {
        "pain_point": (
            "경비인력과 교대방식 또는 계약단가가 "
            "유사단지 대비 높을 가능성"
        ),
        "hypotheses": [
            "경비인원 또는 초소 수가 상대적으로 많음",
            "교대방식과 휴게시간 설계의 차이",
            "경비용역 계약단가 또는 업무범위의 차이",
        ],
        "evidence": [
            "경비용역 계약서와 과업지시서",
            "경비인원·초소·교대표 및 근무시간표",
            "최근 입찰 및 비교견적 자료",
            "경비비 원장과 월별 지급내역",
        ],
        "actions": [
            {
                "action_type": "VALIDATE",
                "title": "경비인력·계약 대사",
                "detail": (
                    "계약인원, 실제 배치인원, 교대표와 "
                    "월별 지급액을 대사한다."
                ),
                "owner": "관리사무소 계약담당",
                "time_horizon": "0~30일",
                "kpi": "계약 대비 실제 배치 일치율",
                "digital_enablement": (
                    "근무표·지급액 자동 대사"
                ),
            },
            {
                "action_type": "OPTIMIZE",
                "title": "경비 운영 시나리오 검토",
                "detail": (
                    "초소, 교대방식, 무인설비 활용과 "
                    "서비스 수준을 함께 비교한다."
                ),
                "owner": "관리사무소장·입주자대표회의",
                "time_horizon": "1~3개월",
                "kpi": "세대당 경비비 및 초소당 인원",
                "digital_enablement": (
                    "인력·무인화 비용 시나리오 분석"
                ),
            },
            {
                "action_type": "CONTROL_AUTOMATE",
                "title": "경비비 편차 월별 경보",
                "detail": (
                    "비교군 범위와 예산을 초과하면 "
                    "검토요청을 자동 생성한다."
                ),
                "owner": "관리사무소장",
                "time_horizon": "상시",
                "kpi": "경비비 예산 초과율",
                "digital_enablement": (
                    "Power BI 이상징후 알림"
                ),
            },
        ],
    },
    "elevator": {
        "pain_point": (
            "승강기 유지보수 계약 또는 고장대응 비용이 "
            "기대수준을 상회할 가능성"
        ),
        "hypotheses": [
            "승강기 대수·연식 차이로 유지비가 높음",
            "유지보수 계약방식 또는 단가가 높음",
            "반복고장이나 부품교체가 집중됨",
        ],
        "evidence": [
            "승강기 대수·모델·설치연도 현황",
            "승강기 유지보수 계약서",
            "최근 12개월 고장·출동·부품교체 이력",
            "유지보수료 지급내역과 비교견적",
        ],
        "actions": [
            {
                "action_type": "VALIDATE",
                "title": "승강기 계약·고장이력 분석",
                "detail": (
                    "계약단가, 승강기 대수와 "
                    "고장·출동 빈도를 연결해 검토한다."
                ),
                "owner": "시설관리 담당",
                "time_horizon": "0~30일",
                "kpi": "승강기당 유지비 및 고장빈도",
                "digital_enablement": (
                    "고장이력·계약비용 통합 분석"
                ),
            },
            {
                "action_type": "OPTIMIZE",
                "title": "유지보수 계약 재설계",
                "detail": (
                    "단순유지·책임유지 계약방식과 "
                    "복수업체 견적을 비교한다."
                ),
                "owner": "입주자대표회의",
                "time_horizon": "1~3개월",
                "kpi": "승강기당 계약단가",
                "digital_enablement": (
                    "계약 시나리오 비용 비교"
                ),
            },
            {
                "action_type": "CONTROL_AUTOMATE",
                "title": "예방정비 모니터링",
                "detail": (
                    "고장빈도, 부품교체와 유지비 추세를 "
                    "연계해 이상징후를 관리한다."
                ),
                "owner": "시설관리 담당",
                "time_horizon": "상시",
                "kpi": "반복고장률 및 예방정비 이행률",
                "digital_enablement": (
                    "Power BI 설비상태 모니터링"
                ),
            },
        ],
    },
    "repairs": {
        "pain_point": (
            "수선비가 특정 월에 집중되거나 비용분류·"
            "업체선정 검토가 필요할 가능성"
        ),
        "hypotheses": [
            "일회성 대규모 수선공사가 발생함",
            "일반수선비와 장기수선충당금 사용의 분류 차이",
            "업체선정과 공사단가 비교가 부족함",
        ],
        "evidence": [
            "최근 12개월 수선비 원장과 증빙",
            "공사계약서·견적서·검수조서",
            "장기수선계획과 장기수선충당금 사용내역",
            "입찰공고·업체평가·의결자료",
        ],
        "actions": [
            {
                "action_type": "VALIDATE",
                "title": "수선비 발생원인·분류 검증",
                "detail": (
                    "고액 수선비를 공사별로 분해하고 "
                    "회계분류 및 승인근거를 확인한다."
                ),
                "owner": "관리사무소 회계·시설담당",
                "time_horizon": "0~30일",
                "kpi": "증빙완비율 및 분류오류 건수",
                "digital_enablement": (
                    "고액거래 자동추출 및 증빙 연결"
                ),
            },
            {
                "action_type": "OPTIMIZE",
                "title": "공사 조달·견적 절차 개선",
                "detail": (
                    "복수견적, 입찰, 업체평가와 "
                    "공사단가 벤치마크를 표준화한다."
                ),
                "owner": "입주자대표회의",
                "time_horizon": "1~3개월",
                "kpi": "경쟁견적률 및 예정가 대비 낙찰률",
                "digital_enablement": (
                    "견적비교 및 업체평가 워크플로"
                ),
            },
            {
                "action_type": "CONTROL_AUTOMATE",
                "title": "수선비 이상거래 통제",
                "detail": (
                    "고액·반복·분할 거래를 탐지하고 "
                    "승인자료 확인을 자동 요청한다."
                ),
                "owner": "관리사무소장",
                "time_horizon": "상시",
                "kpi": "이상거래 검토 완료율",
                "digital_enablement": (
                    "규칙기반 이상거래 경보"
                ),
            },
        ],
    },
    "facility": {
        "pain_point": (
            "공용시설 유지보수 범위 또는 계약단가가 "
            "유사단지 대비 높을 가능성"
        ),
        "hypotheses": [
            "노후설비로 반복 유지보수가 발생함",
            "시설관리 계약범위와 실제 서비스의 차이",
            "예방정비 부족으로 사후수리 비용이 증가함",
        ],
        "evidence": [
            "주요 설비 목록·연식·상태 현황",
            "시설유지보수 계약서와 과업범위",
            "고장·점검·수리 이력",
            "시설유지비 원장과 업체별 지급내역",
        ],
        "actions": [
            {
                "action_type": "VALIDATE",
                "title": "시설비 계약·설비이력 대사",
                "detail": (
                    "시설별 유지비, 고장빈도와 "
                    "계약서비스 이행 여부를 검토한다."
                ),
                "owner": "시설관리 담당",
                "time_horizon": "0~30일",
                "kpi": "계약서비스 이행률",
                "digital_enablement": (
                    "설비·계약·지급 데이터 통합"
                ),
            },
            {
                "action_type": "OPTIMIZE",
                "title": "예방정비·계약범위 최적화",
                "detail": (
                    "반복고장 설비를 식별하고 예방정비와 "
                    "교체 시나리오를 비교한다."
                ),
                "owner": "관리사무소장·입주자대표회의",
                "time_horizon": "1~3개월",
                "kpi": "반복고장률 및 설비당 유지비",
                "digital_enablement": (
                    "수리·교체 생애주기 비용 분석"
                ),
            },
            {
                "action_type": "CONTROL_AUTOMATE",
                "title": "시설 유지비 예측·경보",
                "detail": (
                    "설비별 고장과 비용추세를 기반으로 "
                    "예산초과 위험을 모니터링한다."
                ),
                "owner": "시설관리 담당",
                "time_horizon": "상시",
                "kpi": "예방정비율 및 예산 편차율",
                "digital_enablement": (
                    "Power BI 설비비용 조기경보"
                ),
            },
        ],
    },
}


def numeric_value(
    value: Any,
    default: float = 0.0,
) -> float:
    number = pd.to_numeric(
        value,
        errors="coerce",
    )

    if pd.isna(number):
        return default

    return float(number)


def priority_band(score: float) -> str:
    if score >= 70:
        return "P1_CRITICAL"

    if score >= 45:
        return "P2_HIGH"

    if score >= 20:
        return "P3_MEDIUM"

    return "P4_MONITOR"


def load_inputs() -> pd.DataFrame:
    if not ANOMALY_SUMMARY_FILE.exists():
        raise FileNotFoundError(
            f"이상징후 요약이 없습니다: "
            f"{ANOMALY_SUMMARY_FILE}"
        )

    if not EXPECTED_RANGE_FILE.exists():
        raise FileNotFoundError(
            f"기대비용 범위가 없습니다: "
            f"{EXPECTED_RANGE_FILE}"
        )

    anomaly = pd.read_csv(
        ANOMALY_SUMMARY_FILE,
        dtype={
            "apartment_id": "string",
            "cost_category": "string",
        },
    )

    expected = pd.read_csv(
        EXPECTED_RANGE_FILE,
        dtype={
            "cost_category": "string",
        },
    )

    required_anomaly_columns = {
        "apartment_id",
        "apartment_name",
        "cost_category",
        "cost_category_name_ko",
        "anomaly_summary_score",
        "summary_severity",
        "alert_month_count",
        "low_cost_review_month_count",
        "annual_gap_pct",
        "annual_range_position",
        "indicative_annual_excess_cost_krw",
        "dominant_signal",
        "confidence_level",
        "latest_search_month",
    }

    missing_columns = (
        required_anomaly_columns
        - set(anomaly.columns)
    )

    if missing_columns:
        raise ValueError(
            f"이상징후 요약 필수 칼럼이 없습니다: "
            f"{sorted(missing_columns)}"
        )

    expected_columns = [
        "cost_category",
        "model_status",
        "model_peer_count",
        "effective_sample_size",
        "expected_low_cost_per_household_krw",
        "expected_median_cost_per_household_krw",
        "expected_high_cost_per_household_krw",
    ]

    missing_expected = (
        set(expected_columns)
        - set(expected.columns)
    )

    if missing_expected:
        raise ValueError(
            f"기대비용 필수 칼럼이 없습니다: "
            f"{sorted(missing_expected)}"
        )

    expected_subset = expected[
        expected_columns
    ].copy()

    result = anomaly.merge(
        expected_subset,
        on="cost_category",
        how="left",
        validate="one_to_one",
    )

    if len(result) != 6:
        raise ValueError(
            f"비용항목이 6개가 아닙니다: {len(result)}"
        )

    return result


def calculate_priority_score(
    row: pd.Series,
) -> float:
    anomaly_score = max(
        numeric_value(
            row["anomaly_summary_score"]
        ),
        0,
    )

    positive_gap = min(
        max(
            numeric_value(
                row["annual_gap_pct"]
            ),
            0,
        ),
        100,
    )

    alert_months = min(
        max(
            numeric_value(
                row["alert_month_count"]
            ),
            0,
        ),
        12,
    )

    persistence_score = (
        alert_months / 12 * 100
    )

    raw_score = (
        anomaly_score * 0.60
        + positive_gap * 0.25
        + persistence_score * 0.15
    )

    confidence = str(
        row["confidence_level"]
    ).upper()

    confidence_multiplier = {
        "HIGH": 1.00,
        "MEDIUM": 0.90,
        "LOW": 0.75,
    }.get(confidence, 0.70)

    score = raw_score * confidence_multiplier

    low_cost_review_count = numeric_value(
        row["low_cost_review_month_count"]
    )

    if low_cost_review_count > 0:
        score = max(score, 35)

    return round(
        min(max(score, 0), 100),
        2,
    )


def create_category_assessment(
    model_results: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for _, model_row in model_results.iterrows():
        category = model_row["cost_category"]
        playbook = CATEGORY_PLAYBOOKS[category]

        score = calculate_priority_score(
            model_row
        )

        priority = priority_band(score)

        low_cost_review_count = numeric_value(
            model_row[
                "low_cost_review_month_count"
            ]
        )

        if low_cost_review_count > 0:
            recommendation_status = (
                "DATA_VALIDATION_REQUIRED"
            )
        elif priority in {
            "P1_CRITICAL",
            "P2_HIGH",
        }:
            recommendation_status = (
                "MANAGEMENT_REVIEW_REQUIRED"
            )
        elif priority == "P3_MEDIUM":
            recommendation_status = (
                "FOCUSED_REVIEW"
            )
        else:
            recommendation_status = "MONITOR"

        gap_pct = numeric_value(
            model_row["annual_gap_pct"]
        )

        range_position = str(
            model_row["annual_range_position"]
        )

        dominant_signal = str(
            model_row["dominant_signal"]
        )

        recommendation_basis = (
            f"이상징후 점수 "
            f"{numeric_value(model_row['anomaly_summary_score']):.2f}, "
            f"연간 비교군 격차 {gap_pct:.2f}%, "
            f"범위 위치 {range_position}, "
            f"주요 신호 "
            f"{SIGNAL_NAMES.get(dominant_signal, dominant_signal)}"
        )

        rows.append(
            {
                "engine_version": ENGINE_VERSION,
                "apartment_id": model_row[
                    "apartment_id"
                ],
                "apartment_name": model_row[
                    "apartment_name"
                ],
                "cost_category": category,
                "cost_category_name_ko": model_row[
                    "cost_category_name_ko"
                ],
                "advisory_priority_score": score,
                "advisory_priority": priority,
                "recommendation_status": (
                    recommendation_status
                ),
                "screened_pain_point": playbook[
                    "pain_point"
                ],
                "hypothesis_1": playbook[
                    "hypotheses"
                ][0],
                "hypothesis_2": playbook[
                    "hypotheses"
                ][1],
                "hypothesis_3": playbook[
                    "hypotheses"
                ][2],
                "primary_recommended_action": (
                    playbook["actions"][0]["title"]
                ),
                "review_focus": model_row.get(
                    "review_focus",
                    playbook["actions"][0]["detail"],
                ),
                "recommendation_basis": (
                    recommendation_basis
                ),
                "anomaly_summary_score": (
                    model_row[
                        "anomaly_summary_score"
                    ]
                ),
                "summary_severity": model_row[
                    "summary_severity"
                ],
                "alert_month_count": model_row[
                    "alert_month_count"
                ],
                "annual_gap_pct": model_row[
                    "annual_gap_pct"
                ],
                "annual_range_position": (
                    model_row[
                        "annual_range_position"
                    ]
                ),
                "indicative_annual_opportunity_krw": (
                    model_row[
                        "indicative_annual_excess_cost_krw"
                    ]
                ),
                "model_peer_count": model_row[
                    "model_peer_count"
                ],
                "effective_sample_size": (
                    model_row[
                        "effective_sample_size"
                    ]
                ),
                "confidence_level": model_row[
                    "confidence_level"
                ],
                "model_status": model_row[
                    "model_status"
                ],
                "latest_search_month": model_row[
                    "latest_search_month"
                ],    
                "human_validation_required": True,
                "auto_execution_allowed": False,
                "conclusion_status": (
                    "HYPOTHESIS_NOT_CONFIRMED"
                ),
            }
        )

    assessment = pd.DataFrame(rows).sort_values(
        by=[
            "advisory_priority_score",
            "cost_category",
        ],
        ascending=[False, True],
    ).reset_index(drop=True)

    assessment.insert(
        0,
        "advisory_priority_rank",
        range(1, len(assessment) + 1),
    )

    assessment.insert(
        1,
        "recommendation_id",
        [
            f"REC-{rank:02d}"
            for rank in assessment[
                "advisory_priority_rank"
            ]
        ],
    )

    return assessment


def create_action_register(
    assessment: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for _, category_row in assessment.iterrows():
        category = category_row[
            "cost_category"
        ]

        playbook = CATEGORY_PLAYBOOKS[category]

        for sequence, action in enumerate(
            playbook["actions"],
            start=1,
        ):
            if action["action_type"] == "OPTIMIZE":
                indicative_opportunity = (
                    category_row[
                        "indicative_annual_opportunity_krw"
                    ]
                )
            else:
                indicative_opportunity = None

            rows.append(
                {
                    "action_id": (
                        f"ACT-"
                        f"{int(category_row['advisory_priority_rank']):02d}"
                        f"-{sequence:02d}"
                    ),
                    "recommendation_id": category_row[
                        "recommendation_id"
                    ],
                    "apartment_id": category_row[
                        "apartment_id"
                    ],
                    "apartment_name": category_row[
                        "apartment_name"
                    ],
                    "cost_category": category,
                    "cost_category_name_ko": (
                        category_row[
                            "cost_category_name_ko"
                        ]
                    ),
                    "category_priority_rank": (
                        category_row[
                            "advisory_priority_rank"
                        ]
                    ),
                    "advisory_priority": (
                        category_row[
                            "advisory_priority"
                        ]
                    ),
                    "action_sequence": sequence,
                    "action_type": action[
                        "action_type"
                    ],
                    "action_title": action["title"],
                    "action_detail": action["detail"],
                    "business_owner": action["owner"],
                    "time_horizon": action[
                        "time_horizon"
                    ],
                    "success_kpi": action["kpi"],
                    "digital_enablement": action[
                        "digital_enablement"
                    ],
                    "indicative_opportunity_krw": (
                        indicative_opportunity
                    ),
                    "action_status": "PROPOSED",
                    "human_approval_required": True,
                    "auto_execution_allowed": False,
                }
            )

    return pd.DataFrame(rows)


def create_evidence_requests(
    assessment: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for _, category_row in assessment.iterrows():
        category = category_row[
            "cost_category"
        ]

        playbook = CATEGORY_PLAYBOOKS[category]

        if category_row["advisory_priority"] in {
            "P1_CRITICAL",
            "P2_HIGH",
        }:
            evidence_priority = "HIGH"
        elif (
            category_row["advisory_priority"]
            == "P3_MEDIUM"
        ):
            evidence_priority = "MEDIUM"
        else:
            evidence_priority = "LOW"

        for sequence, document_name in enumerate(
            playbook["evidence"],
            start=1,
        ):
            rows.append(
                {
                    "evidence_request_id": (
                        f"EVD-"
                        f"{int(category_row['advisory_priority_rank']):02d}"
                        f"-{sequence:02d}"
                    ),
                    "recommendation_id": category_row[
                        "recommendation_id"
                    ],
                    "apartment_id": category_row[
                        "apartment_id"
                    ],
                    "cost_category": category,
                    "cost_category_name_ko": (
                        category_row[
                            "cost_category_name_ko"
                        ]
                    ),
                    "evidence_priority": (
                        evidence_priority
                    ),
                    "document_name": document_name,
                    "request_purpose": (
                        category_row[
                            "screened_pain_point"
                        ]
                        + " 가설 검증"
                    ),
                    "expected_provider": (
                        "관리사무소 또는 입주자대표회의"
                    ),
                    "request_status": "NOT_REQUESTED",
                    "contains_personal_data_review": True,
                }
            )

    return pd.DataFrame(rows)


def format_won(value: Any) -> str:
    number = numeric_value(value)

    return f"{number:,.0f}원"


def write_advisory_brief(
    assessment: pd.DataFrame,
    executive_summary: pd.DataFrame,
) -> None:
    summary = executive_summary.iloc[0]
    top_three = assessment.head(3)

    table_rows = []

    for _, row in assessment.iterrows():
        table_rows.append(
            "| "
            + " | ".join(
                [
                    str(
                        int(
                            row[
                                "advisory_priority_rank"
                            ]
                        )
                    ),
                    str(
                        row[
                            "cost_category_name_ko"
                        ]
                    ),
                    str(
                        row["advisory_priority"]
                    ),
                    f"{numeric_value(row['advisory_priority_score']):.1f}",
                    f"{numeric_value(row['annual_gap_pct']):.1f}%",
                    format_won(
                        row[
                            "indicative_annual_opportunity_krw"
                        ]
                    ),
                    str(
                        row[
                            "recommendation_status"
                        ]
                    ),
                ]
            )
            + " |"
        )

    top_action_lines = []

    for _, row in top_three.iterrows():
        top_action_lines.append(
            f"{int(row['advisory_priority_rank'])}. "
            f"**{row['cost_category_name_ko']}** — "
            f"{row['screened_pain_point']}. "
            f"우선 조치: {row['primary_recommended_action']}."
        )

    report = f"""# K-APT AX Advisory Pilot Brief

## 1. Executive Summary

- 분석 대상: **{summary["apartment_name"]}** (`{summary["apartment_id"]}`)
- 분석 기준월: {summary["data_as_of_month"]}
- 검토 비용항목: 6개
- P1·P2 우선검토 항목: {int(summary["high_priority_category_count"])}개
- 모델 경보 월: {int(summary["total_alert_month_count"])}건
- 지표상 연간 기회금액: **{format_won(summary["total_indicative_opportunity_krw"])}**
- 의사결정 상태: **HUMAN REVIEW REQUIRED**

기회금액은 비교단지 가중 중앙값을 기준으로 계산한 참고값이며 확정 절감액이 아닙니다.

## 2. Priority Assessment

| 순위 | 비용항목 | 우선순위 | 점수 | 비교군 격차 | 지표상 기회금액 | 상태 |
|---:|---|---|---:|---:|---:|---|
{chr(10).join(table_rows)}

## 3. Top Advisory Actions

{chr(10).join(top_action_lines)}

## 4. AX Enablement

1. K-APT 공시자료와 관리비 원장·계약금액 자동대사
2. 유사단지 가중 벤치마크와 기대비용 범위 자동 산출
3. Power BI를 통한 월별 이상징후 및 계약 갱신 알림
4. 증빙 요청, 담당자 배정, 검토 상태를 Action Register로 관리
5. 고위험 신호에 대해 사람의 승인 후 조치 실행

## 5. Required Validation

모델 결과를 확정적인 비효율 또는 부당지출로 해석해서는 안 됩니다. 다음 자료를 추가 검토해야 합니다.

- 관리비 원장과 예산 대비 실적
- 용역 및 유지보수 계약서
- 입찰·견적·업체선정 자료
- 인력·설비·서비스 범위 자료
- 관리사무소와 입주자대표회의의 설명

## 6. Responsible AI Statement

- 공개데이터 누락을 0원으로 대체하지 않았습니다.
- 모든 추천은 `HYPOTHESIS_NOT_CONFIRMED` 상태로 생성됩니다.
- 시스템은 계약 해지, 인력 감축, 업체 변경을 자동 실행하지 않습니다.
- 최종 의사결정에는 계약조건, 서비스 품질과 현장상황에 대한 사람의 검토가 필요합니다.
"""

    ADVISORY_BRIEF_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ADVISORY_BRIEF_FILE.write_text(
        report,
        encoding="utf-8",
    )


def validate_and_save(
    assessment: pd.DataFrame,
    actions: pd.DataFrame,
    evidence: pd.DataFrame,
) -> None:
    total_opportunity = (
        assessment[
            "indicative_annual_opportunity_krw"
        ]
        .apply(numeric_value)
        .clip(lower=0)
        .sum()
    )

    high_priority_count = int(
        assessment["advisory_priority"]
        .isin(
            [
                "P1_CRITICAL",
                "P2_HIGH",
            ]
        )
        .sum()
    )

    total_alerts = int(
        assessment["alert_month_count"]
        .apply(numeric_value)
        .sum()
    )

    top_category = assessment.iloc[0]

    executive_summary = pd.DataFrame(
        [
            {
                "engine_version": ENGINE_VERSION,
                "apartment_id": top_category[
                    "apartment_id"
                ],
                "apartment_name": top_category[
                    "apartment_name"
                ],
                "data_as_of_month": assessment[
                    "latest_search_month"
                ].max(),
                "category_count": len(
                    assessment
                ),
                "high_priority_category_count": (
                    high_priority_count
                ),
                "total_alert_month_count": (
                    total_alerts
                ),
                "top_priority_category": (
                    top_category[
                        "cost_category_name_ko"
                    ]
                ),
                "top_priority_score": (
                    top_category[
                        "advisory_priority_score"
                    ]
                ),
                "total_indicative_opportunity_krw": (
                    total_opportunity
                ),
                "proposed_action_count": len(
                    actions
                ),
                "evidence_request_count": len(
                    evidence
                ),
                "decision_status": (
                    "HUMAN_REVIEW_REQUIRED"
                ),
            }
        ]
    )

    CATEGORY_ASSESSMENT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    assessment.to_csv(
        CATEGORY_ASSESSMENT_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    actions.to_csv(
        ACTION_REGISTER_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    evidence.to_csv(
        EVIDENCE_REQUEST_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    executive_summary.to_csv(
        EXECUTIVE_SUMMARY_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    write_advisory_brief(
        assessment=assessment,
        executive_summary=executive_summary,
    )

    assessment_duplicates = int(
        assessment.duplicated(
            subset=["cost_category"]
        ).sum()
    )

    action_duplicates = int(
        actions.duplicated(
            subset=["action_id"]
        ).sum()
    )

    evidence_duplicates = int(
        evidence.duplicated(
            subset=["evidence_request_id"]
        ).sum()
    )

    print(
        f"[OK] 비용항목 평가 수: "
        f"{len(assessment):,}"
    )
    print(
        f"[OK] 제안 조치 수: "
        f"{len(actions):,}"
    )
    print(
        f"[OK] 증빙 요청 수: "
        f"{len(evidence):,}"
    )
    print(
        f"[OK] P1·P2 항목 수: "
        f"{high_priority_count:,}"
    )
    print(
        f"[OK] 지표상 기회금액 합계: "
        f"{total_opportunity:,.0f}원"
    )
    print(
        f"[QA] 비용항목 중복 수: "
        f"{assessment_duplicates:,}"
    )
    print(
        f"[QA] 조치 ID 중복 수: "
        f"{action_duplicates:,}"
    )
    print(
        f"[QA] 증빙 ID 중복 수: "
        f"{evidence_duplicates:,}"
    )
    print(
        f"[OK] 비용항목 평가: "
        f"{CATEGORY_ASSESSMENT_FILE}"
    )
    print(
        f"[OK] Action Register: "
        f"{ACTION_REGISTER_FILE}"
    )
    print(
        f"[OK] 증빙 요청목록: "
        f"{EVIDENCE_REQUEST_FILE}"
    )
    print(
        f"[OK] 경영진 요약: "
        f"{EXECUTIVE_SUMMARY_FILE}"
    )
    print(
        f"[OK] Advisory Brief: "
        f"{ADVISORY_BRIEF_FILE}"
    )

    if len(assessment) != 6:
        raise RuntimeError(
            "비용항목 평가가 6행이 아닙니다."
        )

    if len(actions) != 18:
        raise RuntimeError(
            "제안 조치가 18행이 아닙니다."
        )

    if len(evidence) != 24:
        raise RuntimeError(
            "증빙 요청이 24행이 아닙니다."
        )

    if (
        assessment_duplicates > 0
        or action_duplicates > 0
        or evidence_duplicates > 0
    ):
        raise RuntimeError(
            "Advisory 결과에 중복 키가 있습니다."
        )

    print(
        "[SUCCESS] AX Advisory Recommendation Engine을 "
        "완료했습니다."
    )


def main() -> None:
    model_results = load_inputs()

    assessment = create_category_assessment(
        model_results
    )

    actions = create_action_register(
        assessment
    )

    evidence = create_evidence_requests(
        assessment
    )

    validate_and_save(
        assessment=assessment,
        actions=actions,
        evidence=evidence,
    )


if __name__ == "__main__":
    main()