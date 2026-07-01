"""Case endpoints: CRUD, document upload and status polling."""

import uuid

from fastapi import APIRouter, File, UploadFile, status

from api.dependencies import CaseServiceDep, DocumentServiceDep
from api.schemas.cases import CaseCreate, CaseDetail, CaseRename, CaseSummary
from api.schemas.documents import CaseStatus, DocumentStatus

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseSummary, status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate, service: CaseServiceDep) -> CaseSummary:
    return CaseSummary.from_case(service.create_case(payload.name))


@router.get("", response_model=list[CaseSummary])
def list_cases(service: CaseServiceDep) -> list[CaseSummary]:
    return [CaseSummary.from_case(case) for case in service.list_cases()]


@router.get("/{case_id}", response_model=CaseDetail)
def get_case(case_id: uuid.UUID, service: CaseServiceDep) -> CaseDetail:
    case, segment_counts = service.get_case(case_id)
    return CaseDetail.from_case(case, segment_counts)


@router.patch("/{case_id}", response_model=CaseSummary)
def rename_case(case_id: uuid.UUID, payload: CaseRename, service: CaseServiceDep) -> CaseSummary:
    return CaseSummary.from_case(service.rename_case(case_id, payload.name))


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(case_id: uuid.UUID, service: CaseServiceDep) -> None:
    service.delete_case(case_id)


@router.post(
    "/{case_id}/documents",
    response_model=list[DocumentStatus],
    status_code=status.HTTP_202_ACCEPTED,
)
def upload_documents(
    case_id: uuid.UUID,
    service: DocumentServiceDep,
    files: list[UploadFile] = File(...),
) -> list[DocumentStatus]:
    rows = service.upload_documents(case_id, files)
    return [DocumentStatus.from_row(row) for row in rows]


@router.get("/{case_id}/status", response_model=CaseStatus)
def case_status(case_id: uuid.UUID, service: DocumentServiceDep) -> CaseStatus:
    return CaseStatus.from_case(service.get_case_status(case_id))
