"""OAuth authentication routes for Google and Kakao."""

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.crud.user import user as user_crud
from app.database import get_db
from app.models.user import AuthProvider, User, UserRole

oauth_router = APIRouter(prefix="/auth", tags=["auth"])


# === Google OAuth ===


@oauth_router.get("/google")
async def google_login(
    request: Request,
    return_to: str = Query("/", description="URL to redirect after login"),
):
    """Initiate Google OAuth login."""
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    request.session["return_to"] = return_to

    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": f"{settings.backend_url}/api/auth/google/callback",
        "response_type": "code",
        "scope": "email profile",
        "state": state,
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=url)


@oauth_router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback."""
    # Verify state
    stored_state = request.session.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{settings.backend_url}/api/auth/google/callback",
            },
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token",
            )

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # Get user info
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info",
            )

        user_data = user_response.json()

    # Create or update user
    user = await _create_or_update_user(
        db=db,
        provider=AuthProvider.GOOGLE,
        provider_id=user_data["id"],
        email=user_data["email"],
        name=user_data.get("name", user_data["email"].split("@")[0]),
        profile_image_url=user_data.get("picture"),
    )

    # Set session
    request.session["user_id"] = user.id
    request.session.pop("oauth_state", None)

    # Redirect to frontend
    return_to = request.session.pop("return_to", "/")
    return RedirectResponse(url=f"{settings.frontend_url}{return_to}")


# === Kakao OAuth ===


@oauth_router.get("/kakao")
async def kakao_login(
    request: Request,
    return_to: str = Query("/", description="URL to redirect after login"),
):
    """Initiate Kakao OAuth login."""
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    request.session["return_to"] = return_to

    params = {
        "client_id": settings.kakao_client_id,
        "redirect_uri": f"{settings.backend_url}/api/auth/kakao/callback",
        "response_type": "code",
        "state": state,
    }
    url = f"https://kauth.kakao.com/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(url=url)


@oauth_router.get("/kakao/callback")
async def kakao_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Handle Kakao OAuth callback."""
    # Verify state
    stored_state = request.session.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state",
        )

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://kauth.kakao.com/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": settings.kakao_client_id,
                "client_secret": settings.kakao_client_secret,
                "code": code,
                "redirect_uri": f"{settings.backend_url}/api/auth/kakao/callback",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange code for token",
            )

        token_data = token_response.json()
        access_token = token_data["access_token"]

        # Get user info
        user_response = await client.get(
            "https://kapi.kakao.com/v2/user/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info",
            )

        user_data = user_response.json()

    # Extract user info from Kakao response
    kakao_account = user_data.get("kakao_account", {})
    profile = kakao_account.get("profile", {})

    email = kakao_account.get("email")
    if not email:
        # Kakao might not provide email, use ID as fallback
        email = f"kakao_{user_data['id']}@kakao.local"

    # Create or update user
    user = await _create_or_update_user(
        db=db,
        provider=AuthProvider.KAKAO,
        provider_id=str(user_data["id"]),
        email=email,
        name=profile.get("nickname", f"User{user_data['id']}"),
        profile_image_url=profile.get("profile_image_url"),
    )

    # Set session
    request.session["user_id"] = user.id
    request.session.pop("oauth_state", None)

    # Redirect to frontend
    return_to = request.session.pop("return_to", "/")
    return RedirectResponse(url=f"{settings.frontend_url}{return_to}")


# === Common ===


@oauth_router.post("/logout")
async def logout(request: Request):
    """Logout and clear session."""
    request.session.clear()
    return {"message": "로그아웃되었습니다"}


@oauth_router.get("/me")
async def get_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get current logged-in user."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    user = await user_crud.get(db, user_id)
    if not user or not user.is_active:
        request.session.clear()
        return None

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "profile_image_url": user.profile_image_url,
        "role": user.role,
    }


async def _create_or_update_user(
    db: AsyncSession,
    provider: AuthProvider,
    provider_id: str,
    email: str,
    name: str,
    profile_image_url: str | None,
) -> User:
    """Create a new user or update existing one."""
    user_id = f"{provider.value}:{provider_id}"

    # Check if user exists by provider ID
    user = await user_crud.get(db, user_id)

    if user:
        # Update existing user
        user.name = name
        user.profile_image_url = profile_image_url
        await user_crud.update_last_login(db, db_obj=user)
    else:
        # Check if email already exists (different provider)
        existing = await user_crud.get_by_email(db, email)
        if existing:
            # Link to existing account
            user = existing
            await user_crud.update_last_login(db, db_obj=user)
        else:
            # Create new user
            user = User(
                id=user_id,
                email=email,
                name=name,
                profile_image_url=profile_image_url,
                provider=provider.value,
                role=UserRole.USER.value,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)

    return user
