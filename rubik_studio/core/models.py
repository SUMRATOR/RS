from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    CheckConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from rubik_studio.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Репозиторий объектов ────────────────────────────────────────────────────


class ObjectType(Base):
    __tablename__ = "object_types"

    __table_args__ = (
        UniqueConstraint("id", "database_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )

    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )

    icon: Mapped[str] = mapped_column(
        String(50), default="circle"
    )

    color: Mapped[str] = mapped_column(
        String(7), default="#9E9E9E"
    )

    database_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("modeling_databases.id"),
        nullable=True,
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    objects: Mapped[list["Object"]] = relationship(
        back_populates="type"
    )


class Object(Base):
    __tablename__ = "objects"

    __table_args__ = (
        UniqueConstraint("id", "database_id"),
        Index(
            "ix_objects_database_type_name",
            "database_id",
            "type_id",
            "name",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )

    database_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("modeling_databases.id"),
        nullable=False,
    )

    type_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("object_types.id"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(500), nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    attributes: Mapped[dict] = mapped_column(
        JSON, default=dict
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
    )

    type: Mapped["ObjectType"] = relationship(
        back_populates="objects",
        lazy="selectin",
    )


class ObjectLink(Base):
    __tablename__ = "object_links"

    __table_args__ = (
        UniqueConstraint(
            "database_id",
            "source_id",
            "target_id",
            "link_type",
        ),
        ForeignKeyConstraint(
            ["source_id", "database_id"],
            ["objects.id", "objects.database_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["target_id", "database_id"],
            ["objects.id", "objects.database_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "source_id <> target_id",
            name="ck_object_link_not_self",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )

    database_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("modeling_databases.id"),
        nullable=False,
    )

    source_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )

    target_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )

    link_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )

    attributes: Mapped[dict] = mapped_column(
        JSON, default=dict
    )


# ── BPMN (используется с Этапа 2) ───────────────────────────────────────────


class BpmnModel(Base):
    __tablename__ = "bpmn_models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    xml_content: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class ModelElementBinding(Base):
    __tablename__ = "model_element_bindings"

    __table_args__ = (
        UniqueConstraint("model_id", "bpmn_element_id"),
        ForeignKeyConstraint(
            ["object_id", "database_id"],
            ["objects.id", "objects.database_id"],
        ),
        ForeignKeyConstraint(
            ["model_id", "database_id"],
            ["models.id", "models.database_id"],
            ondelete="CASCADE",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )

    database_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("modeling_databases.id"),
        nullable=False,
    )

    model_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )

    bpmn_element_id: Mapped[str] = mapped_column(
        String(200), nullable=False
    )

    object_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )


# ── Process Mining (используется с Этапа 3) ─────────────────────────────────


class EventLog(Base):
    __tablename__ = "event_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_log_case_ts", "log_id", "case_id", "timestamp"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True, autoincrement=True)
    log_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("event_logs.id", ondelete="CASCADE")
    )
    case_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    activity: Mapped[str] = mapped_column(String(500), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resource: Mapped[str | None] = mapped_column(String(200), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)


# ── Пользователи и аудит ─────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_user_ts", "user_id", "timestamp"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    username: Mapped[str] = mapped_column(String(100), default="local")
    ip_address: Mapped[str] = mapped_column(String(45), default="127.0.0.1")
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), default="")
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    entity_name: Mapped[str] = mapped_column(String(500), default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)

    database_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )


# ── BPMS (используется с Этапа 4) ───────────────────────────────────────────


class ProcessDefinition(Base):
    __tablename__ = "process_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("bpmn_models.id"))
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ProcessInstance(Base):
    __tablename__ = "process_instances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    definition_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("process_definitions.id")
    )
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    variables: Mapped[dict] = mapped_column(JSON, default=dict)
    spiff_state: Mapped[str | None] = mapped_column(Text, nullable=True)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    process_instance_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("process_instances.id", ondelete="CASCADE")
    )
    bpmn_task_id: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="READY")
    assignee_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    assignee_name: Mapped[str] = mapped_column(String(200), default="")
    candidate_group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    form_data: Mapped[dict] = mapped_column(JSON, default=dict)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TaskHistory(Base):
    __tablename__ = "task_history"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, 'sqlite'), primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(50))
    details: Mapped[dict] = mapped_column(JSON, default=dict)

# ============================================================
# RS — ЛОГИЧЕСКИЕ БАЗЫ МОДЕЛИРОВАНИЯ
# ============================================================


class Methodology(Base):
    __tablename__ = "methodologies"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_uuid,
    )

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )


class ModelCategory(Base):
    __tablename__ = "model_categories"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_uuid,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )


class ModelType(Base):
    __tablename__ = "model_types"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_uuid,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("model_categories.id"),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )

    keywords: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )

    editor_status: Mapped[str] = mapped_column(
        String(30),
        default="NOT_IMPLEMENTED",
        nullable=False,
    )

    is_system: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    category: Mapped["ModelCategory"] = relationship(
        lazy="selectin",
    )


class MethodologyModelType(Base):
    __tablename__ = "methodology_model_types"

    methodology_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "methodologies.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    model_type_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "model_types.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )


class ModelingDatabase(Base):
    __tablename__ = "modeling_databases"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_uuid,
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    methodology_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("methodologies.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )

    methodology: Mapped["Methodology"] = relationship(
        lazy="selectin",
    )


class Model(Base):
    __tablename__ = "models"

    __table_args__ = (
        UniqueConstraint("id", "database_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_uuid,
    )

    database_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "modeling_databases.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    model_type_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("model_types.id"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )

    model_type: Mapped["ModelType"] = relationship(
        lazy="selectin",
    )

    database: Mapped["ModelingDatabase"] = relationship(
        lazy="selectin",
    )

# RS_REPOSITORY_ISOLATION_V3


# RS_OBJECT_TEMPLATES_MODEL_V8

class ObjectTemplate(Base):
    """Общий трафарет для создания независимых объектов."""

    __tablename__ = "object_templates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )

    name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )

    description: Mapped[str] = mapped_column(
        Text, default="", nullable=False
    )

    type_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("object_types.id", ondelete="RESTRICT"),
        nullable=False,
    )

    fields: Mapped[list] = mapped_column(
        JSON, default=list, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )

    object_type: Mapped["ObjectType"] = relationship(
        lazy="selectin",
    )

