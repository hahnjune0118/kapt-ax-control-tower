# Power BI 최종 검증 체크리스트

코드 기반 검증 이후 Power BI Desktop에서 수행해야 하는 최종 화면 QA입니다. 메뉴명은 영어 UI 기준입니다.

## 1. 열기 전

```powershell
git pull
node scripts\build_powerbi_report.mjs
python scripts\validate_powerbi_project.py
npx --yes @microsoft/powerbi-report-authoring-cli@latest validate powerbi\KAPT_AX_Control_Tower.Report --pretty
```

합격 기준:

- 로컬 QA: `[PASS] 0 errors`
- Microsoft CLI: `errorCount: 0`
- `PBIR_SCHEMA_UNREACHABLE`만 남으면 네트워크 접근 경고인지 확인
- `git status --short`에 `.env`, `localSettings.json`, `cache.abf`가 없어야 함

## 2. Power BI Desktop 로드

1. `powerbi/KAPT_AX_Control_Tower.pbip`를 엽니다.
2. 경로 오류가 나오면 **Home > Transform data > Edit parameters**를 선택합니다.
3. `pDataRoot`를 `C:\Users\<사용자>\...\kapt-ax-control-tower\powerbi\data`로 변경합니다.
4. **Close & Apply** 후 **Home > Refresh**를 실행합니다.
5. Refresh 오류가 0건인지 확인합니다.

## 3. 모델 확인

**Model view**에서 다음을 확인합니다.

- 관계 17개
- Fact → Dimension 방향은 `Many to one (*:1)` / `Single`
- `FactMonthlyCost[month_start_date]` → `DimDate[Date]` 활성 관계
- `FactAnomalyMonthly[month_start_date]` → `DimDate[Date]` 활성 관계
- `DimDate[YearMonth]`의 **Sort by column**이 `YearMonthSort`
- 불필요한 `LocalDateTable` 없음
- `_Measures`에 공통 DAX 측정값이 모여 있음

## 4. 페이지별 화면 QA

공통 확인:

- 첫 화면은 `01 Management Overview`
- 사용자 페이지 5개와 숨김 `00 Model QA` 존재
- 상단 Page navigator가 5개 사용자 페이지 사이에서 작동
- 제목/카드/축/범례가 겹치거나 잘리지 않음
- 슬라이서 선택이 관련 카드와 차트를 필터링
- 모든 사용자 페이지 상단에 `분석 대상 | 마곡현대아파트`가 표시되고 단지명은 11pt Bold
- 단일 대상 보고서에 불필요한 아파트 선택기가 노출되지 않음
- 흰 배경·차콜 텍스트·오렌지 섹션 번호·엷은 제목의 컨설팅 보고서 스타일이 일관되게 적용
- 큰 금액 카드는 `억 원`·`천만 원`, 소액은 `만 원`·`원`으로 표시하며 `₩`·`M`·`K`를 사용하지 않음
- 범주형 선 그래프의 비용항목별 색상이 서로 구분되고 범례와 일치

### 01 Management Overview

- 대상 단지: 마곡현대아파트
- 지표상 연간 절감 검토액 약 3.4천만 원
- P3 2개, P4 4개
- 주요 검토 항목이 경비비·시설유지비로 표시
- 절감 검토액이 확정액이 아니라는 안내문 표시

### 02 Peer Benchmark

- 모델 선정 비교단지 30개
- 가중 평균 유사도 약 89.7
- `model_selected = true` 비교단지만 분석 차트에 사용
- 유사도·모델가중치·관측률을 함께 확인 가능
- 유사도·적합도 산점도의 매칭 단계별 색상이 구분됨

### 03 Cost Driver Analysis

- 대상/비교군 월평균이 비용항목별로 비교됨
- 월별 추이는 2025-07~2026-06 순서
- 비용항목 슬라이서가 표와 차트에 함께 적용

### 04 Anomaly Review

- 최대 이상징후 점수 34.3 내외
- 경보 1건
- 월, 비용항목, 이상징후 사유와 검토 초점 확인 가능
- 비용항목별 선 색상이 6개 항목을 구분할 수 있고 범례와 일치
- 빈 점수는 0으로 오인해 표시하지 않음

### 05 Action Agenda

- 조치 18개, 증빙 요청 24개
- 조치마다 담당자·기간·상태·승인 필요 여부 표시
- 미요청 증빙 24개
- 자동 실행 금지 및 사람 승인 안내문 표시

### 00 Model QA

- 페이지를 우클릭해 **Unhide page**로 일시 확인 가능
- 서울 단지 3,384 / 월별 Fact 3,600 / 비용항목 6
- 개수 카드는 `3.4K`, `3,384.0`처럼 축약하거나 소수로 표시하지 않고 `3,384개`, `3,600행`처럼 전체값과 단위를 표시
- 데이터 관측률과 모델 분석 가능률이 비정상 공백이 아님
- 확인 후 다시 **Hide page**

## 5. 상호작용·성능

1. 각 페이지에서 슬라이서 하나를 선택하고 모든 관련 시각화가 3초 내 반응하는지 확인합니다.
2. **Format > Edit interactions**에서 장식용 요소가 필터 대상으로 설정되지 않았는지 확인합니다.
3. **View > Performance analyzer**를 열고 **Start recording > Refresh visuals**를 실행합니다.
4. 유난히 느린 시각화가 있으면 DAX query 시간을 기록합니다.
5. 선택을 모두 해제하고 기본 상태로 저장합니다.

## 6. 저장·게시 전 통제

- `절감 가능액`처럼 실현 가능성을 암시하거나 절감 검토액을 확정 절감액으로 표현한 문구 없음
- 부정·비리·책임을 단정한 문구 없음
- 데이터 기준월과 공개데이터 한계 표시
- 사람 승인 필요 및 자동 실행 금지 표시
- API 키, 개인정보, 원본 API 응답 미포함
- Power BI Service 게시 시 대상 Workspace와 접근권한을 다시 확인

검증이 끝나면 **File > Save**로 PBIP를 저장하고 Power BI Desktop을 종료한 뒤 `git status --short`로 변경 파일을 검토합니다.
