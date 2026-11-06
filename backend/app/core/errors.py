"""Service-layer exceptions translated to HTTP responses in one place."""

from fastapi import status


class ServiceError(Exception):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class BadRequestError(ServiceError):
    status_code = status.HTTP_400_BAD_REQUEST


class NotFoundError(ServiceError):
    status_code = status.HTTP_404_NOT_FOUND


class ForbiddenError(ServiceError):
    status_code = status.HTTP_403_FORBIDDEN


class ConflictError(ServiceError):
    status_code = status.HTTP_409_CONFLICT
