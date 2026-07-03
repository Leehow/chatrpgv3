from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel

from chatrpg.ir.source import SourceBlock, SourceDocument


class PdfIngestResult(BaseModel):
    document: SourceDocument
    blocks: list[SourceBlock]


def ingest_pdf(*, path: Path, document_id: str, title: str | None = None) -> PdfIngestResult:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF ingest requires the optional ingest dependencies.") from exc

    raw = path.read_bytes()
    document = SourceDocument(
        id=document_id,
        title=title or path.stem,
        source_type="pdf",
        uri=str(path),
        sha256=hashlib.sha256(raw).hexdigest(),
        document_metadata={"file_name": path.name},
    )
    blocks: list[SourceBlock] = []
    with fitz.open(stream=raw, filetype="pdf") as pdf:
        for page_index, page in enumerate(pdf, start=1):
            block_payloads = page.get_text("blocks", sort=True)
            for block_index, payload in enumerate(block_payloads):
                x0, y0, x1, y1, block_text, *_ = payload
                clean = str(block_text).strip()
                block_id = f"{document_id}:p{page_index}:b{block_index}"
                blocks.append(
                    SourceBlock(
                        id=block_id,
                        document_id=document_id,
                        page_number=page_index,
                        block_index=block_index,
                        block_kind="text" if clean else "unknown",
                        text=clean or None,
                        bbox={"x0": float(x0), "y0": float(y0), "x1": float(x1), "y1": float(y1)},
                        visibility="system",
                        sha256=hashlib.sha256(f"{block_id}:{clean}".encode("utf-8")).hexdigest(),
                    )
                )
    return PdfIngestResult(document=document, blocks=blocks)
