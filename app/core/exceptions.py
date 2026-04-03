from typing import Mapping

from fastapi import status


class AppException(Exception):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Application error."
    headers: Mapping[str, str] | None = None

    def __init__(
        self,
        detail: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.detail = detail or self.detail
        self.headers = headers or self.headers
        super().__init__(self.detail)


class ResourceNotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Requested resource was not found."


class DuplicateResourceError(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource already exists."


class AuthenticationError(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Could not validate credentials."
    headers = {"WWW-Authenticate": "Bearer"}


class AuthorizationError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to perform this action."
