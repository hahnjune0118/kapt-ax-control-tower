# K-APT AX Control Tower — Project Charter

## 1. Project Objective

공개된 공동주택 데이터를 활용하여 특정 아파트 단지의 관리비 비효율,
조달 검토 필요사항 및 장기수선충당금 부족 가능성을 진단하고,
입주자대표회의와 관리사무소가 실행할 수 있는 개선과제를 제시한다.

## 2. Core Pain Point

K-apt는 관리비, 입찰, 유지관리 및 감사정보를 공개하지만,
정보가 서로 분리되어 있고 비전문가가 이를 실제 의사결정으로
전환하기 어렵다.

본 프로젝트는 공개정보와 실제 관리행동 사이의
Transparency-to-Action Gap을 해소한다.

## 3. Primary Users

### 입주자대표회의

- 관리비와 계약금액의 적정성 검토
- 장기수선충당금 조정
- 입찰 및 계약 관련 의사결정

### 관리사무소

- 비용 변동 원인 분석
- 입찰 준비와 증빙 관리
- 감사 및 입주민 질의 대응

## 4. Decisions Supported

1. 어떤 관리비 항목을 우선 검토해야 하는가?
2. 실제 비용이 단지 특성을 고려한 기대비용보다 높은가?
3. 어떤 계약에 추가 증빙검토가 필요한가?
4. 장기수선충당금이 미래 공사비를 충당할 수 있는가?
5. 다음 입주자대표회의에서 어떤 안건을 상정해야 하는가?

## 5. MVP Scope

- 대상단지 1개
- 비교단지 20~30개
- 최근 36개월 관리비 분석
- 최근 3년 입찰 및 수의계약 분석
- 향후 5년 장기수선충당금 시뮬레이션
- Power BI 5~6개 보고서 페이지
- AI Action Pack 생성

## 6. Non-goals

- 비리 또는 담합 확정 판정
- 외부회계감사 대체
- 법률자문 제공
- 세대별 개인정보 분석
- 아파트 매매가격 예측
- 전국 모든 단지의 실시간 운영

## 7. Core Analytical Engines

1. Peer Group Selection
2. Expected Cost Model
3. Procurement Review Engine
4. Long-term Repair Stress Model
5. RAG-based Action Agent

## 8. Success Criteria

### Data

- 관리비 원천자료와 분석자료 간 금액 대사
- 핵심 데이터의 기준월과 출처 추적
- 대상단지와 비교단지 선정근거 제시

### Analytics

- 실제 관리비와 기대관리비 차이 산출
- 주요 계약 위험신호 설명
- 장기수선충당금 부족연도 및 추가부담액 시뮬레이션

### Decision Support

- 상위 3개 개선과제 제시
- 각 과제의 금액적 중요성, 근거, 신뢰도 표시
- 입주자대표회의용 보고서 생성

### Responsible AI

- 공개데이터만으로 부정행위를 단정하지 않음
- 모든 AI 권고에 데이터 또는 문서 출처 표시
- 데이터 부족 시 판단을 유보함