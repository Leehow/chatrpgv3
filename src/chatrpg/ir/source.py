from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Visibility = Literal["public", "player", "keeper", "system"]


class SourceRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    document_id: str
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    block_id: str | None = None
    asset_id: str | None = None
    visibility: Visibility = "system"

    @model_validator(mode="after")
    def validate_page_range(self) -> SourceRef:
        if self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return self


class SourceDocument(BaseModel):
    id: str
    title: str
    source_type: Literal["pdf", "markdown", "plaintext", "image"]
    uri: str | None = None
    sha256: str
    document_metadata: dict[str, str] = Field(default_factory=dict)


class SourceBlock(BaseModel):
    id: str
    document_id: str
    page_number: int = Field(ge=1)
    block_index: int = Field(ge=0)
    block_kind: Literal["text", "table", "image", "heading", "unknown"]
    text: str | None = None
    bbox: dict[str, float] | None = None
    visibility: Visibility = "system"
    sha256: str

    def source_ref(self) -> SourceRef:
        return SourceRef(
            document_id=self.document_id,
            page_start=self.page_number,
            page_end=self.page_number,
            block_id=self.id,
            visibility=self.visibility,
        )


class SourceAsset(BaseModel):
    id: str
    document_id: str
    asset_kind: Literal["page_image", "crop", "handout", "map", "table_image"]
    page_number: int = Field(ge=1)
    storage_uri: str
    asset_metadata: dict[str, object] = Field(default_factory=dict)

    def source_ref(self) -> SourceRef:
        return SourceRef(
            document_id=self.document_id,
            page_start=self.page_number,
            page_end=self.page_number,
            asset_id=self.id,
            visibility="system",
        )
