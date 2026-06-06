import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from app.webhook_handler import handle_webhook_update
from app.bot_manager import bot_manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook/{bot_token}")
async def receive_webhook(bot_token: str, request: Request):
    try:
        update_dict = await request.json()
    except Exception as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    success = await handle_webhook_update(bot_token, update_dict)
    
    if not success:
        raise HTTPException(status_code=404, detail="Bot not found or inactive")
    
    return {"ok": True}


@router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "telegram-bot-host"}