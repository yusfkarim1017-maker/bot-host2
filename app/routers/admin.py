import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
from passlib.context import CryptContext
from app.config import settings
from app.database import get_db
from app.models import Bot, BotLog, BotMode
from app.schemas import (
    BotCreate, BotUpdate, BotResponse, BotListResponse,
    BotLogResponse, BotLogListResponse, TokenResponse, LoginRequest,
)
from app.bot_manager import bot_manager

router = APIRouter(prefix="/api", tags=["admin"])
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.admin_secret_key, algorithm=settings.admin_jwt_algorithm)
    return encoded_jwt


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.admin_secret_key,
            algorithms=[settings.admin_jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    if request.secret_key != settings.admin_secret_key:
        raise HTTPException(status_code=401, detail="Invalid secret key")
    
    access_token = create_access_token({"sub": "admin"})
    return TokenResponse(access_token=access_token)


@router.post("/bots", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(bot_data: BotCreate, _: dict = Depends(verify_token)):
    bot = await bot_manager.create_bot(
        token=bot_data.token,
        username=bot_data.username,
        owner_id=bot_data.owner_id,
        mode=bot_data.mode,
    )
    
    if not bot:
        raise HTTPException(status_code=400, detail="Bot with this token already exists")
    
    return bot


@router.get("/bots", response_model=BotListResponse)
async def list_bots(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    _: dict = Depends(verify_token),
):
    bots = await bot_manager.list_bots(skip=skip, limit=limit)
    total = await bot_manager.count_bots()
    return BotListResponse(bots=bots, total=total)


@router.get("/bots/{bot_id}", response_model=BotResponse)
async def get_bot(bot_id: UUID, _: dict = Depends(verify_token)):
    bot = await bot_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot


@router.put("/bots/{bot_id}", response_model=BotResponse)
async def update_bot(bot_id: UUID, bot_data: BotUpdate, _: dict = Depends(verify_token)):
    bot = await bot_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    was_active = bot.is_active
    new_mode = bot_data.mode if bot_data.mode is not None else bot.mode
    
    if bot_data.is_active is not None and bot_data.is_active != bot.is_active:
        if bot_data.is_active:
            await bot_manager.start_bot(bot_id)
        else:
            await bot_manager.stop_bot(bot_id)
    elif was_active and new_mode != bot.mode:
        await bot_manager.switch_mode(bot_id, new_mode)
    
    if bot_data.username is not None or bot_data.owner_id is not None:
        bot = await bot_manager.update_bot(
            bot_id,
            username=bot_data.username,
            owner_id=bot_data.owner_id,
        )
    
    if bot_data.mode is not None and bot_data.mode != bot.mode:
        bot = await bot_manager.get_bot(bot_id)
    
    return bot


@router.delete("/bots/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(bot_id: UUID, _: dict = Depends(verify_token)):
    success = await bot_manager.remove_bot(bot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bot not found")


@router.post("/bots/{bot_id}/start", response_model=BotResponse)
async def start_bot(bot_id: UUID, _: dict = Depends(verify_token)):
    bot = await bot_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    success = await bot_manager.start_bot(bot_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start bot")
    
    return await bot_manager.get_bot(bot_id)


@router.post("/bots/{bot_id}/stop", response_model=BotResponse)
async def stop_bot(bot_id: UUID, _: dict = Depends(verify_token)):
    bot = await bot_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    success = await bot_manager.stop_bot(bot_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to stop bot")
    
    return await bot_manager.get_bot(bot_id)


@router.post("/bots/{bot_id}/switch-mode", response_model=BotResponse)
async def switch_mode(bot_id: UUID, mode: BotMode, _: dict = Depends(verify_token)):
    bot = await bot_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    success = await bot_manager.switch_mode(bot_id, mode)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to switch mode")
    
    return await bot_manager.get_bot(bot_id)


@router.get("/bots/{bot_id}/logs", response_model=BotLogListResponse)
async def get_bot_logs(
    bot_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None),
    _: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
):
    bot = await bot_manager.get_bot(bot_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    query = select(BotLog).where(BotLog.bot_id == bot_id)
    if level:
        query = query.where(BotLog.level == level)
    
    query = query.order_by(BotLog.timestamp.desc()).offset(skip).limit(limit)
    
    result = await db.execute(query)
    logs = list(result.scalars().all())
    
    count_query = select(func.count()).select_from(BotLog).where(BotLog.bot_id == bot_id)
    if level:
        count_query = count_query.where(BotLog.level == level)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    return BotLogListResponse(logs=logs, total=total)