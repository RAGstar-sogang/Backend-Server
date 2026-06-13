from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from database import get_db
from models import Diagnosis, OomLog, Result
from schemas import PendingDiagnosisResponse, StatusUpdateRequest, ResultSubmitRequest, ActionGuideDict
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/diagnosis", tags=["AI"])


@router.get("/pending")
def get_pending_diagnosis(db: Session = Depends(get_db)):
    diagnosis = (
        db.query(Diagnosis)
        .filter(Diagnosis.status == "pending")
        .order_by(Diagnosis.created_at.asc())
        .first()
    )
    if not diagnosis:
        return Response(status_code=204)

    diagnosis.status = "running"
    db.commit()

    log = db.query(OomLog).filter(OomLog.id == diagnosis.log_id).first()
    return PendingDiagnosisResponse(
        diagnosis_id=diagnosis.id,
        raw_log=log.raw_log,
        metadata=log.log_metadata,
    )


@router.patch("/{diagnosis_id}/status")
def update_diagnosis_status(
    diagnosis_id: int, req: StatusUpdateRequest, db: Session = Depends(get_db)
):
    diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not found")

    diagnosis.status = req.status
    db.commit()
    return {"ok": True}


@router.post("/{diagnosis_id}/result")
async def create_result(
    diagnosis_id: int, request: Request, db: Session = Depends(get_db)
):
    body = await request.json()
    logger.warning(f'DEBUG result payload for {diagnosis_id}: {body}')
    from pydantic import ValidationError
    try:
        req = ResultSubmitRequest(**body)
    except ValidationError as e:
        logger.warning(f'DEBUG validation error: {e}')
        raise HTTPException(status_code=422, detail=e.errors())
    diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not found")

    existing = db.query(Result).filter(Result.diagnosis_id == diagnosis_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Result already exists")

    r = req.result

    # action_guide 분기: list / dict / None
    ag = r.action_guide
    if isinstance(ag, list):
        ag_legacy, ag_imm, ag_rec = ag, None, None
    elif isinstance(ag, ActionGuideDict):
        ag_legacy, ag_imm, ag_rec = None, ag.immediate, ag.recommended
    else:
        ag_legacy, ag_imm, ag_rec = None, None, None

    result = Result(
        diagnosis_id=diagnosis_id,
        oom_type=r.oom_type,
        confidence=r.confidence,
        constraint_type=r.constraint_type,
        root_cause=r.root_cause,
        evidence=r.evidence,
        severity=r.severity,
        action_guide=ag_legacy,
        action_guide_immediate=ag_imm,
        action_guide_recommended=ag_rec,
        latency_ms=r.latency_ms,
    )

    # GPT 결과 (nullable)
    if req.gpt_result is not None:
        g = req.gpt_result
        result.gpt_oom_type = g.oom_type
        result.gpt_confidence = g.confidence
        result.gpt_root_cause = g.root_cause
        result.gpt_evidence = g.evidence
        result.gpt_severity = g.severity
        result.gpt_latency_ms = g.latency_ms
        result.gpt_model = g.model

        gag = g.action_guide
        if isinstance(gag, list):
            result.gpt_action_guide_immediate = gag
            result.gpt_action_guide_recommended = []
        elif isinstance(gag, ActionGuideDict):
            result.gpt_action_guide_immediate = gag.immediate
            result.gpt_action_guide_recommended = [].recommended

    db.add(result)
    diagnosis.status = "success"
    db.commit()
    return {"ok": True}
