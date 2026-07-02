from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chatrpg.core.ids import new_id
from chatrpg.db.models import SemanticEmbeddingRow


@dataclass(frozen=True)
class VectorHit:
    owner_kind: str
    owner_id: str
    score: float


class PostgresVectorStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def put(
        self,
        *,
        owner_kind: str,
        owner_id: str,
        embedding_model: str,
        embedding: list[float],
    ) -> str:
        row_id = new_id("emb")
        self._session.add(
            SemanticEmbeddingRow(
                id=row_id,
                owner_kind=owner_kind,
                owner_id=owner_id,
                embedding_model=embedding_model,
                embedding=embedding,
            )
        )
        return row_id

    async def nearest(self, *, embedding: list[float], limit: int = 10) -> list[VectorHit]:
        distance = SemanticEmbeddingRow.embedding.cosine_distance(embedding).label("distance")
        rows = await self._session.execute(
            select(SemanticEmbeddingRow.owner_kind, SemanticEmbeddingRow.owner_id, distance)
            .order_by(distance)
            .limit(limit)
        )
        return [
            VectorHit(owner_kind=row.owner_kind, owner_id=row.owner_id, score=float(1.0 - row.distance))
            for row in rows
        ]
