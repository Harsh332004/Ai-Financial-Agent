from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.user import User
from backend.schemas.user import LoginRequest, TokenResponse, UserCreate, UserResponse
from backend.services.auth_service import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Create a new user account with an email address and password.\n\n"
        "- Email must be unique — returns **409 Conflict** otherwise.\n"
        "- Password is stored as a bcrypt hash — never in plain text.\n"
        "- Default role is `analyst`; admins can promote to `manager` or `admin`."
    ),
    response_description="Newly created user (password excluded)",
)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and get a JWT access token",
    description=(
        "Authenticate with email and password.\n\n"
        "On success, returns a JWT `access_token` (valid for "
        "`ACCESS_TOKEN_EXPIRE_MINUTES` minutes, default 24 h).\n\n"
        "**How to use in Swagger:** Copy the `access_token` value, "
        "click the **🔒 Authorize** button at the top of the page, "
        "paste the token in the **Value** field, and click *Authorize*. "
        "All protected endpoints will then send `Authorization: Bearer <token>` automatically."
    ),
    response_description="JWT Bearer access token",
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
    description=(
        "Returns the profile of the user who owns the Bearer token in the `Authorization` header.\n\n"
        "Use this to verify that your token is valid and to retrieve your user ID, email, and role."
    ),
    response_description="Current user's profile",
)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
