# RAGstar Backend

dmesg OOM 로그를 RAG 파이프라인으로 진단하는 시스템의 백엔드 서버 (FastAPI + SQLite).

## 시스템 아키텍처

```
[사용자]
   ↓
[Streamlit 프론트엔드]  → https://github.com/RAGstar-sogang/Web-server
   ↓ HTTP
[FastAPI 백엔드 (AWS EC2)]  ← 이 리포
   ↑ polling (5초 간격)
[AI 워커 (학교 서버 GPU 컨테이너)]
   ↓
[LangGraph + ChromaDB + vLLM]
```

## Polling 방식을 채택한 이유

학교 GPU 서버는 사내망(방화벽) 안에 있어 외부에서 직접 호출이 불가능하다.
따라서 백엔드가 워커를 호출하는 Push 방식 대신, 워커가 안에서 밖으로(outbound)
백엔드를 주기적으로 폴링하는 구조를 사용한다.

흐름:
1. 프론트가 진단 요청 → 백엔드가 DB에 status=pending으로 저장
2. AI 워커가 5초마다 GET /pending 폴링 → 작업 가져가며 status=running
3. 워커가 LangGraph 파이프라인 실행 (파싱 → 분류 → 도구 → 진단)
4. 결과를 POST /result로 백엔드에 push → status=success
5. 프론트가 GET polling으로 결과 수신 → 화면 렌더

## API 엔드포인트

### 프론트엔드용
| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | /api/v1/diagnosis | 진단 요청 생성 (pending 저장) |
| GET | /api/v1/diagnosis/{id} | 진단 결과 조회 — ours/gpt 비교 구조 |
| GET | /api/v1/diagnosis | 진단 이력 목록 |

### AI 워커용
| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | /api/v1/diagnosis/pending | pending 작업 1건 가져가기 (자동 status=running) |
| PATCH | /api/v1/diagnosis/{id}/status | 상태 업데이트 (failed 등) |
| POST | /api/v1/diagnosis/{id}/result | 분석 결과 저장 (RAGstar + GPT 비교) |

## DB 설계 (SQLite + SQLAlchemy)

| 테이블 | 역할 | 주요 컬럼 |
|---|---|---|
| users | 사용자 | id, email, name, role |
| oom_logs | 입력 로그 원본 | raw_log, source, line_count, log_metadata(JSON) |
| diagnoses | 진단 작업 단위 | user_id(FK), log_id(FK), status(pending/running/success/failed) |
| results | 진단 결과 | 아래 상세 |

### results 테이블 (21개 컬럼)
자체 모델(RAGstar)과 GPT 결과를 한 행에 나란히 저장해 비교 조회를 단순화:
- RAGstar 결과: oom_type, constraint_type, confidence, root_cause, evidence,
  severity, action_guide_immediate(JSON), action_guide_recommended(JSON), latency_ms
- GPT 결과: gpt_* 접두사로 동일 구조 + gpt_model
- gpt_* 컬럼은 모두 nullable — GPT 호출 실패 시에도 자체 결과는 저장됨

## 결과 스키마 (워커 → 백엔드)

result / gpt_result 모두 평탄(flat) 구조:
- 필수: oom_type, confidence, root_cause
- 옵셔널: constraint_type, evidence, severity, action_guide, latency_ms
- action_guide는 list 또는 {immediate: [], recommended: []} 객체 둘 다 수용
- gpt_result에는 model 필드 추가 (예: "gpt-5.2")

## OOM 진단 카테고리 (4유형)

| 유형 | 설명 |
|---|---|
| global_oom | 시스템 전체 메모리 부족 |
| cgroup_oom | 컨테이너 memory limit 초과 |
| swap_exhaustion | Swap 전부 소진 |
| page_alloc_failure | 높은 order 연속 페이지 할당 실패 |
