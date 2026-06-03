from fastapi import HTTPException, status

from app.core.errors import (
    bad_request, unauthorized, forbidden, not_found, conflict, service_unavailable,
)


def test_bad_request_es_400():
    exc = bad_request("X")
    assert isinstance(exc, HTTPException)
    assert exc.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.detail == "X"


def test_unauthorized_es_401():
    assert unauthorized("X").status_code == status.HTTP_401_UNAUTHORIZED


def test_forbidden_es_403():
    assert forbidden("X").status_code == status.HTTP_403_FORBIDDEN


def test_not_found_es_404():
    assert not_found("X").status_code == status.HTTP_404_NOT_FOUND


def test_conflict_es_409():
    assert conflict("X").status_code == status.HTTP_409_CONFLICT


def test_service_unavailable_es_503():
    assert service_unavailable("X").status_code == status.HTTP_503_SERVICE_UNAVAILABLE


def test_detail_se_propaga():
    for helper in (bad_request, unauthorized, forbidden, not_found, conflict, service_unavailable):
        assert helper("mensaje custom").detail == "mensaje custom"
