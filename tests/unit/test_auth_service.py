"""
Unit tests for AuthService.

These tests mock the repository layer so they test pure business logic
without touching any database.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.exceptions import AuthenticationException, ConflictException
from app.schemas.user import UserLoginRequest, UserRegisterRequest
from app.services.auth_service import AuthService


@pytest.mark.unit
class TestAuthServiceRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, db_session):
        """User can register with valid data."""
        request = UserRegisterRequest(
            email="newuser@example.com",
            password="Strong@123",
            first_name="John",
            last_name="Doe",
            default_currency="USD",
        )

        with patch("app.services.auth_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.email_exists = AsyncMock(return_value=False)

            from app.models import User
            import uuid
            from datetime import datetime, timezone
            fake_user = MagicMock(spec=User)
            fake_user.id = uuid.uuid4()
            fake_user.email = request.email
            fake_user.first_name = request.first_name
            fake_user.last_name = request.last_name
            fake_user.default_currency = request.default_currency
            fake_user.profile_image_url = None
            fake_user.is_active = True
            fake_user.is_verified = False
            fake_user.role = "user"
            fake_user.created_at = datetime.now(timezone.utc)
            mock_repo.create = AsyncMock(return_value=fake_user)

            db_session.commit = AsyncMock()

            service = AuthService(db_session)
            result = await service.register(request)

        assert result.email == request.email
        assert result.first_name == request.first_name

    @pytest.mark.asyncio
    async def test_register_duplicate_email_raises_conflict(self, db_session):
        """Registering with an existing email raises ConflictException."""
        request = UserRegisterRequest(
            email="existing@example.com",
            password="Strong@123",
            first_name="Jane",
            last_name="Doe",
        )

        with patch("app.services.auth_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.email_exists = AsyncMock(return_value=True)

            service = AuthService(db_session)
            with pytest.raises(ConflictException):
                await service.register(request)


@pytest.mark.unit
class TestAuthServiceLogin:
    @pytest.mark.asyncio
    async def test_login_wrong_password_raises_auth_error(self, db_session):
        """Wrong password raises AuthenticationException."""
        from app.core.security import hash_password
        from app.models import User
        import uuid

        fake_user = MagicMock(spec=User)
        fake_user.id = uuid.uuid4()
        fake_user.hashed_password = hash_password("Correct@123")
        fake_user.is_active = True

        with patch("app.services.auth_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_email = AsyncMock(return_value=fake_user)

            service = AuthService(db_session)
            with pytest.raises(AuthenticationException):
                await service.login(
                    UserLoginRequest(email="user@example.com", password="Wrong@123")
                )

    @pytest.mark.asyncio
    async def test_login_nonexistent_user_raises_auth_error(self, db_session):
        """Login with unknown email raises AuthenticationException (timing-safe)."""
        with patch("app.services.auth_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_email = AsyncMock(return_value=None)

            service = AuthService(db_session)
            with pytest.raises(AuthenticationException):
                await service.login(
                    UserLoginRequest(email="nobody@example.com", password="Any@1234")
                )

    @pytest.mark.asyncio
    async def test_login_inactive_user_raises_auth_error(self, db_session):
        """Deactivated account raises AuthenticationException."""
        from app.core.security import hash_password
        from app.models import User
        import uuid

        fake_user = MagicMock(spec=User)
        fake_user.id = uuid.uuid4()
        fake_user.hashed_password = hash_password("Test@1234")
        fake_user.is_active = False

        with patch("app.services.auth_service.UserRepository") as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_email = AsyncMock(return_value=fake_user)

            service = AuthService(db_session)
            with pytest.raises(AuthenticationException, match="deactivated"):
                await service.login(
                    UserLoginRequest(email="user@example.com", password="Test@1234")
                )
