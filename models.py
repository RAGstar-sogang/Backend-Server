from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False, default="operator")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    diagnoses = relationship("Diagnosis", back_populates="user")


class OomLog(Base):
    __tablename__ = "oom_logs"

    id = Column(Integer, primary_key=True, index=True)
    raw_log = Column(Text, nullable=False)
    source = Column(String, nullable=False, default="paste")
    line_count = Column(Integer, nullable=False)
    log_metadata = Column(JSON, nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    diagnosis = relationship("Diagnosis", back_populates="log")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    log_id = Column(Integer, ForeignKey("oom_logs.id"), nullable=False)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="diagnoses")
    log = relationship("OomLog", back_populates="diagnosis")
    result = relationship("Result", back_populates="diagnosis", uselist=False)


class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    diagnosis_id = Column(Integer, ForeignKey("diagnoses.id"), unique=True, nullable=False)
    oom_type = Column(String, nullable=True)
    constraint_type = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    root_cause = Column(Text, nullable=True)
    action_guide = Column(JSON, nullable=True)

    # --- v2: 신규 컬럼 (우리 결과) ---
    evidence = Column(Text, nullable=True)
    severity = Column(String, nullable=True)
    action_guide_immediate = Column(JSON, nullable=True)
    action_guide_recommended = Column(JSON, nullable=True)
    latency_ms = Column(Integer, nullable=True)

    # --- v2: GPT 비교 결과 ---
    gpt_oom_type = Column(String, nullable=True)
    gpt_root_cause = Column(Text, nullable=True)
    gpt_evidence = Column(Text, nullable=True)
    gpt_severity = Column(String, nullable=True)
    gpt_action_guide_immediate = Column(JSON, nullable=True)
    gpt_action_guide_recommended = Column(JSON, nullable=True)
    gpt_confidence = Column(Float, nullable=True)
    gpt_latency_ms = Column(Integer, nullable=True)
    gpt_model = Column(String, nullable=True)

    diagnosis = relationship("Diagnosis", back_populates="result")
