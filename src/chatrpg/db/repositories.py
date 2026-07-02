from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from chatrpg.core.ids import new_id
from chatrpg.db.models import (
    AdventureRow,
    DomainEventRow,
    RulesetRow,
    SemanticMatchRow,
    SessionRow,
    SourceAssetRow,
    SourceBlockRow,
    SourceDocumentRow,
)
from chatrpg.ir.adventure import AdventureIR
from chatrpg.ir.events import DomainEvent
from chatrpg.ir.ruleset import RulesetIR
from chatrpg.ir.source import SourceAsset, SourceBlock, SourceDocument, SourceRef
from chatrpg.retrieval.semantic import SemanticMatchRequest, SemanticMatchResult


async def ping_postgres(session: AsyncSession) -> str:
    result = await session.execute(text("select version()"))
    return str(result.scalar_one())


class PostgresSourceStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def put_document(self, document: SourceDocument) -> None:
        await self._session.merge(
            SourceDocumentRow(
                id=document.id,
                title=document.title,
                source_type=document.source_type,
                uri=document.uri,
                sha256=document.sha256,
                document_metadata=document.document_metadata,
            )
        )

    async def put_blocks(self, blocks: list[SourceBlock]) -> None:
        for block in blocks:
            await self._session.merge(
                SourceBlockRow(
                    id=block.id,
                    document_id=block.document_id,
                    page_number=block.page_number,
                    block_index=block.block_index,
                    block_kind=block.block_kind,
                    text=block.text,
                    bbox=block.bbox,
                    visibility=block.visibility,
                    sha256=block.sha256,
                )
            )

    async def put_assets(self, assets: list[SourceAsset]) -> None:
        for asset in assets:
            await self._session.merge(
                SourceAssetRow(
                    id=asset.id,
                    document_id=asset.document_id,
                    asset_kind=asset.asset_kind,
                    page_number=asset.page_number,
                    storage_uri=asset.storage_uri,
                    asset_metadata=asset.asset_metadata,
                )
            )

    async def list_blocks(self, *, document_id: str, limit: int = 200) -> list[SourceBlock]:
        rows = await self._session.execute(
            select(SourceBlockRow)
            .where(SourceBlockRow.document_id == document_id)
            .order_by(SourceBlockRow.page_number, SourceBlockRow.block_index)
            .limit(limit)
        )
        return [
            SourceBlock(
                id=row.id,
                document_id=row.document_id,
                page_number=row.page_number,
                block_index=row.block_index,
                block_kind=row.block_kind,
                text=row.text,
                bbox=row.bbox,
                visibility=row.visibility,
                sha256=row.sha256,
            )
            for row in rows.scalars()
        ]

    async def list_assets(self, *, document_id: str) -> list[SourceAsset]:
        rows = await self._session.execute(
            select(SourceAssetRow)
            .where(SourceAssetRow.document_id == document_id)
            .order_by(SourceAssetRow.page_number, SourceAssetRow.id)
        )
        return [
            SourceAsset(
                id=row.id,
                document_id=row.document_id,
                asset_kind=row.asset_kind,
                page_number=row.page_number,
                storage_uri=row.storage_uri,
                asset_metadata=row.asset_metadata,
            )
            for row in rows.scalars()
        ]


class PostgresIRStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def put_ruleset(self, ruleset: RulesetIR) -> str:
        row_id = new_id("rul")
        self._session.add(
            RulesetRow(
                id=row_id,
                system_id=ruleset.system_id,
                edition=ruleset.edition,
                ir=ruleset.model_dump(mode="json"),
                source_refs=[ref.model_dump(mode="json") for ref in ruleset.source_refs],
            )
        )
        return row_id

    async def get_ruleset(self, *, system_id: str, edition: str) -> RulesetIR | None:
        row = (
            await self._session.execute(
                select(RulesetRow)
                .where(RulesetRow.system_id == system_id)
                .where(RulesetRow.edition == edition)
                .order_by(RulesetRow.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return RulesetIR.model_validate(row.ir)

    async def put_adventure(self, adventure: AdventureIR) -> str:
        self._session.add(
            AdventureRow(
                id=adventure.adventure_id,
                system_id=adventure.system_id,
                title=adventure.title,
                ir=adventure.model_dump(mode="json"),
                source_refs=[ref.model_dump(mode="json") for ref in adventure.source_refs],
            )
        )
        return adventure.adventure_id

    async def get_adventure(self, *, adventure_id: str) -> AdventureIR | None:
        row = await self._session.get(AdventureRow, adventure_id)
        if row is None:
            return None
        return AdventureIR.model_validate(row.ir)


class PostgresEventStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(self, *, system_id: str, adventure_id: str | None) -> str:
        session_id = new_id("ses")
        self._session.add(SessionRow(id=session_id, system_id=system_id, adventure_id=adventure_id, state={}))
        return session_id

    async def get_session_row(self, *, session_id: str) -> SessionRow | None:
        return await self._session.get(SessionRow, session_id)

    async def append(self, event: DomainEvent) -> None:
        self._session.add(
            DomainEventRow(
                id=event.id,
                session_id=event.session_id,
                event_type=event.event_type,
                actor_id=event.actor_id,
                payload=event.payload,
                source_refs=[ref.model_dump(mode="json") for ref in event.source_refs],
                trace_id=event.trace_id,
            )
        )

    async def append_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.append(event)

    async def list_events(self, *, session_id: str) -> list[DomainEvent]:
        rows = await self._session.execute(
            select(DomainEventRow)
            .where(DomainEventRow.session_id == session_id)
            .order_by(DomainEventRow.created_at)
        )
        events: list[DomainEvent] = []
        for row in rows.scalars():
            events.append(
                DomainEvent(
                    id=row.id,
                    session_id=row.session_id,
                    event_type=row.event_type,
                    actor_id=row.actor_id,
                    payload=row.payload,
                    source_refs=[SourceRef.model_validate(ref) for ref in row.source_refs],
                    trace_id=row.trace_id,
                    created_at=row.created_at,
                )
            )
        return events


class PostgresSemanticTraceStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_match(
        self,
        *,
        request: SemanticMatchRequest,
        result: SemanticMatchResult,
        trace_id: str,
    ) -> str:
        row_id = new_id("sem")
        self._session.add(
            SemanticMatchRow(
                id=row_id,
                task=request.task,
                request=request.model_dump(mode="json"),
                result=result.model_dump(mode="json"),
                trace_id=trace_id,
            )
        )
        return row_id
