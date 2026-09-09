from fastapi import HTTPException
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


class ApplicationException(HTTPException):
    def __init__(
        self,
        detail: str,
        status_code: int = HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail=detail,
        )