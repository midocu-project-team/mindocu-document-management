"""Domain exceptions raised by the service layer.

Routers/handlers map these to HTTP responses (see ``api.main``); the services
themselves stay HTTP-agnostic.
"""


class APIError(Exception):
    """Base for expected, client-facing errors. ``status_code`` drives the HTTP reply."""

    status_code = 400

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CaseNotFoundError(APIError):
    status_code = 404

    def __init__(self, case_id: object) -> None:
        super().__init__(f"case {case_id} not found")


class DocumentNotFoundError(APIError):
    status_code = 404

    def __init__(self, document_id: object) -> None:
        super().__init__(f"document {document_id} not found")


class TooManyDocumentsError(APIError):
    status_code = 409

    def __init__(self, limit: int) -> None:
        super().__init__(f"a case may hold at most {limit} PDF(s)")


class InvalidUploadError(APIError):
    status_code = 422

    def __init__(self, file_name: str | None) -> None:
        super().__init__(f"{file_name or 'upload'} is not a valid PDF")
