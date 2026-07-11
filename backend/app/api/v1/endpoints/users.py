"""
User profile endpoints.
"""
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.user import UserResponse, UserUpdateRequest
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the authenticated user's profile."""
    service = UserService(db)
    return await service.get_profile(current_user.id)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update profile fields (first name, last name, default currency)."""
    service = UserService(db)
    return await service.update_profile(current_user.id, request)


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a profile image. Accepts JPG, PNG, WEBP up to 5MB."""
    content = await file.read()
    service = UserService(db)
    return await service.upload_profile_image(
        user_id=current_user.id,
        file_content=content,
        filename=file.filename or "avatar.jpg",
    )
