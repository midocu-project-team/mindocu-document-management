"""Segment endpoints: single-segment detail and the manual relevance toggle."""

import uuid

from fastapi import APIRouter

from api.dependencies import SegmentServiceDep
from api.schemas.segments import SegmentDetail, SegmentUpdate

router = APIRouter(prefix="/segments", tags=["segments"])


@router.get("/{segment_id}", response_model=SegmentDetail)
def get_segment(segment_id: uuid.UUID, service: SegmentServiceDep) -> SegmentDetail:
    """One segment with all its detail (references, relevance, title, ...)."""
    return SegmentDetail.from_segment(service.get_segment(segment_id))


@router.patch("/{segment_id}", response_model=SegmentDetail)
def update_segment(
    segment_id: uuid.UUID, payload: SegmentUpdate, service: SegmentServiceDep
) -> SegmentDetail:
    """Manually flips a segment's relevance; does not re-run enrichment."""
    return SegmentDetail.from_segment(
        service.update_relevance(segment_id, payload.relevance)
    )
