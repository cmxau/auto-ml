from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserOut
from app.services.auth_service import create_token_for_user, register_user

router = APIRouter()


def ok(data: dict, status_code: int = 200):
    return JSONResponse({"success": True, "data": data}, status_code=status_code)


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    user = register_user(db, body.email, body.password, body.full_name)
    if not user:
        raise HTTPException(status_code=409, detail="Email already registered")
    return ok({"user_id": user.id}, status_code=201)


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    token = create_token_for_user(db, body.email, body.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return ok({"access_token": token, "token_type": "bearer"})


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return ok(UserOut.model_validate(current_user).model_dump(mode="json"))
