from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict, Union
from datetime import datetime


# --- Frontend: POST /api/v1/diagnosis ---
class DiagnosisCreateRequest(BaseModel):
    raw_log: str
    metadata: Optional[dict] = None
    source: str = "paste"


class DiagnosisCreateResponse(BaseModel):
    diagnosis_id: int
    status: str


# --- Frontend: GET /api/v1/diagnosis/{id} ---
class ResultDetail(BaseModel):
    oom_type: Optional[str] = None
    constraint_type: Optional[str] = None
    confidence: Optional[float] = None
    root_cause: Optional[str] = None
    action_guide: Any = None


class DiagnosisDetailResponse(BaseModel):
    diagnosis_id: int
    status: str
    raw_log_preview: Optional[str] = None
    metadata: Optional[dict] = None
    result: Optional[ResultDetail] = None


# --- Frontend: GET /api/v1/diagnosis ---
class DiagnosisListItem(BaseModel):
    diagnosis_id: int
    status: str
    created_at: datetime
    oom_type: Optional[str] = None


# --- AI: GET /api/v1/diagnosis/pending ---
class PendingDiagnosisResponse(BaseModel):
    diagnosis_id: int
    raw_log: str
    metadata: Optional[dict] = None


# --- AI: PATCH /api/v1/diagnosis/{id}/status ---
class StatusUpdateRequest(BaseModel):
    status: str = Field(..., pattern="^(running|failed)$")


# --- AI: POST /api/v1/diagnosis/{id}/result ---
class ResultInner(BaseModel):
    oom_type: Optional[str] = None
    constraint_type: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    root_cause: Optional[str] = None
    action_guide: Any = None


class ResultCreateRequest(BaseModel):
    result: ResultInner
    intermediate_results: Optional[dict] = None


# ============================================================
# v2.1: POST /diagnosis/{id}/result 입력 스키마 (평탄 구조 — 워커 명세 대응)
# ============================================================

class ActionGuideDict(BaseModel):
    immediate: List[str] = []
    recommended: List[str] = []


class OursResultFlat(BaseModel):
    oom_type: str
    confidence: float
    root_cause: str
    constraint_type: Optional[str] = None
    action_guide: Union[List[str], ActionGuideDict, None] = None
    latency_ms: Optional[int] = None
    evidence: Optional[str] = None
    severity: Optional[str] = None


class GptResultFlat(BaseModel):
    oom_type: str
    confidence: float
    root_cause: str
    constraint_type: Optional[str] = None
    action_guide: Union[List[str], ActionGuideDict, None] = None
    latency_ms: Optional[int] = None
    evidence: Optional[str] = None
    severity: Optional[str] = None
    model: str


class ResultSubmitRequest(BaseModel):
    result: OursResultFlat
    gpt_result: Optional[GptResultFlat] = None
    intermediate_results: Optional[Dict[str, Any]] = None


# ============================================================
# v2: GET /diagnosis/{id} 응답 스키마 (ours/gpt 비교)
# ============================================================

class ActionGuideResponse(BaseModel):
    immediate: List[str] = []
    recommended: List[str] = []


class OursResponse(BaseModel):
    oom_type: Optional[str] = None
    constraint_type: Optional[str] = None
    confidence: Optional[float] = None
    root_cause: Optional[str] = None
    evidence: Optional[str] = None
    severity: Optional[str] = None
    action_guide: Optional[ActionGuideResponse] = None
    latency_ms: Optional[int] = None


class GptResponse(BaseModel):
    oom_type: Optional[str] = None
    confidence: Optional[float] = None
    root_cause: Optional[str] = None
    evidence: Optional[str] = None
    severity: Optional[str] = None
    action_guide: Optional[ActionGuideResponse] = None
    latency_ms: Optional[int] = None
    model: Optional[str] = None


class DiagnosisDetailResponseV2(BaseModel):
    diagnosis_id: int
    status: str
    created_at: datetime
    ours: Optional[OursResponse] = None
    gpt: Optional[GptResponse] = None
