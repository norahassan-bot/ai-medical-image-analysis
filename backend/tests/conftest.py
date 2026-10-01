"""Shared Pytest fixtures and configuration for backend tests."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from api.main import app
from api.auth import require_authenticated_user, require_admin, get_current_user_optional, AuthenticatedUser


@pytest.fixture(autouse=True)
def default_auth_override(request):
    """Provide default authenticated user override for non-auth tests so regression suites pass."""
    # Do NOT override dependencies for auth tests
    if (
        "test_auth_rbac" in request.node.nodeid
        or "test_user_portal" in request.node.nodeid
        or "test_token_identity" in request.node.nodeid
        or "test_same_browser_auth" in request.node.nodeid
    ):
        app.dependency_overrides.clear()
        yield
        app.dependency_overrides.clear()
        return

    # Default mock test user with ADMIN role for full suite compatibility
    mock_user = AuthenticatedUser(
        id="test-autouse-user-id",
        username="test_admin_suite",
        role="ADMIN",
        is_active=True,
    )

    async def _mock_require_user():
        return mock_user

    async def _mock_require_admin():
        return mock_user

    async def _mock_current_user_optional():
        return mock_user

    app.dependency_overrides[require_authenticated_user] = _mock_require_user
    app.dependency_overrides[require_admin] = _mock_require_admin
    app.dependency_overrides[get_current_user_optional] = _mock_current_user_optional

    yield

    app.dependency_overrides.clear()
