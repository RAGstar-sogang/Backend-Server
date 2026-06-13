from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Diagnosis, OomLog, Result
from schemas import (
    DiagnosisCreateRequest,
    DiagnosisCreateResponse,
    DiagnosisDetailResponseV2,
    DiagnosisListItem,
    OursResponse,
    GptResponse,
    ActionGuideResponse,
)

router = APIRouter(prefix="/api/v1/diagnosis", tags=["Diagnosis"])


@router.post("", status_code=201)
def create_diagnosis(req: DiagnosisCreateRequest, db: Session = Depends(get_db)):
    raw_log = req.raw_log
    line_count = len(raw_log.strip().splitlines())

    log = OomLog(
        raw_log=raw_log,
        source=req.source,
        line_count=line_count,
        log_metadata=req.metadata,
    )
    db.add(log)
    db.flush()

    diagnosis = Diagnosis(user_id=1, log_id=log.id, status="pending")
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)

    return DiagnosisCreateResponse(diagnosis_id=diagnosis.id, status=diagnosis.status)


@router.get("", response_model=list[DiagnosisListItem])
def list_diagnoses(db: Session = Depends(get_db)):
    diagnoses = (
        db.query(Diagnosis)
        .order_by(Diagnosis.created_at.desc())
        .limit(50)
        .all()
    )
    items = []
    for d in diagnoses:
        oom_type = None
        if d.result:
            oom_type = d.result.oom_type
        items.append(
            DiagnosisListItem(
                diagnosis_id=d.id,
                status=d.status,
                created_at=d.created_at,
                oom_type=oom_type,
            )
        )
    return items


@router.get("/{diagnosis_id}")
def get_diagnosis(diagnosis_id: int, db: Session = Depends(get_db)):
    diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not found")

    response = {
        "diagnosis_id": diagnosis.id,
        "status": diagnosis.status,
        "created_at": diagnosis.created_at,
        "ours": None,
        "gpt": None,
    }

    if diagnosis.status != "success" or diagnosis.result is None:
        return response

    r = diagnosis.result
    # action_guide: 새 컬럼 우선, 없으면 옛 list 컬럼 fallback
    if r.action_guide_immediate is not None or r.action_guide_recommended is not None:
        ours_ag = ActionGuideResponse(
            immediate=r.action_guide_immediate or [],
            recommended=r.action_guide_recommended or [],
        )
    elif r.action_guide and isinstance(r.action_guide, list):
        ours_ag = ActionGuideResponse(immediate=r.action_guide, recommended=[])
    else:
        ours_ag = ActionGuideResponse(immediate=[], recommended=[])

    response["ours"] = OursResponse(
        oom_type=r.oom_type,
        constraint_type=r.constraint_type,
        confidence=r.confidence,
        root_cause=r.root_cause,
        evidence=r.evidence,
        severity=r.severity,
        action_guide=ours_ag,
        latency_ms=r.latency_ms,
    )

    if r.gpt_oom_type is not None:
        response["gpt"] = GptResponse(
            oom_type=r.gpt_oom_type,
            confidence=r.gpt_confidence,
            root_cause=r.gpt_root_cause,
            evidence=r.gpt_evidence,
            severity=r.gpt_severity,
            action_guide=ActionGuideResponse(
                immediate=r.gpt_action_guide_immediate or [],
                recommended=r.gpt_action_guide_recommended or [],
            ),
            latency_ms=r.gpt_latency_ms,
            model=r.gpt_model,
        )

    return response
