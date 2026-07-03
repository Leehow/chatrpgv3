from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SourceDocumentRow(Base):
    __tablename__ = "source_documents"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    document_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SourceBlockRow(Base):
    __tablename__ = "source_blocks"
    __table_args__ = (UniqueConstraint("document_id", "page_number", "block_index", name="uq_source_block_position"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    block_index: Mapped[int] = mapped_column(Integer, nullable=False)
    block_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    bbox: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    visibility: Mapped[str] = mapped_column(String(32), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SourceAssetRow(Base):
    __tablename__ = "source_assets"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False)
    asset_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    asset_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class RulesetRow(Base):
    __tablename__ = "rulesets"
    __table_args__ = (UniqueConstraint("system_id", "edition", name="uq_rulesets_system_edition"),)

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    system_id: Mapped[str] = mapped_column(String(64), nullable=False)
    edition: Mapped[str] = mapped_column(String(64), nullable=False)
    ir: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AdventureRow(Base):
    __tablename__ = "adventures"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    system_id: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    ir: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    system_id: Mapped[str] = mapped_column(String(64), nullable=False)
    adventure_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DomainEventRow(Base):
    __tablename__ = "domain_events"
    __table_args__ = (Index("ix_domain_events_session_created", "session_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(96), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    source_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ParserRunRow(Base):
    __tablename__ = "parser_runs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(96), nullable=False)
    profile: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LlmCallRow(Base):
    __tablename__ = "llm_calls"
    __table_args__ = (Index("ix_llm_calls_trace", "trace_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    task: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SemanticEmbeddingRow(Base):
    __tablename__ = "semantic_embeddings"
    __table_args__ = (
        Index(
            "ix_semantic_embeddings_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SemanticMatchRow(Base):
    __tablename__ = "semantic_matches"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    task: Mapped[str] = mapped_column(String(128), nullable=False)
    request: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TraceSpanRow(Base):
    __tablename__ = "trace_spans"
    __table_args__ = (Index("ix_trace_spans_trace", "trace_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_span_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
