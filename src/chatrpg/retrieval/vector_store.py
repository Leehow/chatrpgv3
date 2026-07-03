from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
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
        vector_value = "[" + ",".join(str(value) for value in embedding) + "]"
        rows = await self._session.execute(
            text(
                "select owner_kind, owner_id, 1 - (embedding <=> CAST(:embedding AS vector)) as score "
                "from semantic_embeddings order by embedding <=> CAST(:embedding AS vector) limit :limit"
            ),
            {"embedding": vector_value, "limit": limit},
        )
        return [
            VectorHit(owner_kind=str(row.owner_kind), owner_id=str(row.owner_id), score=float(row.score))
            for row in rows
        ]
