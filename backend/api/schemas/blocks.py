"""Response model for the single-block endpoint."""

import uuid

from pydantic import BaseModel

from api.db.models import Block
from pipeline.datatypes import BlockType, BoundingBox


class BlockOut(BaseModel):
    """One content block: its text, type, bbox (bottom-left origin) and page."""

    document_id: uuid.UUID
    block_id: int
    page_number: int
    text: str
    block_type: BlockType
    bbox: BoundingBox | None
    source_ref: str | None

    @classmethod
    def from_block(cls, block: Block) -> "BlockOut":
        x0, y0, x1, y1 =  block.bbox_x0, block.bbox_y0, block.bbox_x1, block.bbox_y1
        any_coord_none = x0 is None or y0 is None or x1 is None or y1 is None 

        bbox = (x0,y0,x1,y1) if not any_coord_none else None

        return cls(
            document_id=block.document_id,
            block_id=block.block_id,
            page_number=block.page_number,
            text=block.text,
            block_type=block.block_type,
            bbox=bbox, 
            source_ref=block.source_ref,
        )
