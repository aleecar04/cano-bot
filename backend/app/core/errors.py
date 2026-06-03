"""Helpers para lanzar HTTPException con status codes nombrados.

Se prefiere sobre clases custom de dominio porque:
- FastAPI ya tiene handler built-in para HTTPException, no hace falta custom.
- Mantiene los services con un único contrato HTTP estándar.
- El mensaje al cliente queda igual: {"detail": "..."} con el status code.
"""
from fastapi import HTTPException, status


def bad_request(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail)


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail)


def forbidden(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, detail)


def not_found(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail)


def conflict(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, detail)


def service_unavailable(detail: str) -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail)
