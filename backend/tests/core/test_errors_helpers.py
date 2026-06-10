import pytest
from fastapi import HTTPException, status

from app.core.errors import (
    bad_request, conflict, forbidden, not_found, service_unavailable, unauthorized,
)


@pytest.mark.parametrize("helper, expected_status", [
    (bad_request, status.HTTP_400_BAD_REQUEST),
    (unauthorized, status.HTTP_401_UNAUTHORIZED),
    (forbidden, status.HTTP_403_FORBIDDEN),
    (not_found, status.HTTP_404_NOT_FOUND),
    (conflict, status.HTTP_409_CONFLICT),
    (service_unavailable, status.HTTP_503_SERVICE_UNAVAILABLE),
])
def test_error_helpers_return_expected_status_and_detail(helper, expected_status):
    exc = helper("mensaje custom")
    assert isinstance(exc, HTTPException)
    assert exc.status_code == expected_status
    assert exc.detail == "mensaje custom"
