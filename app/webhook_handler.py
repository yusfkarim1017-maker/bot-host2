import logging
from typing import Optional
import httpx
from telegram import Update, Bot
from telegram.ext import Application, ContextTypes
from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Bot, BotMode
from sqlalchemy import select

logger = logging.getLogger(__name__)


async def handle_webhook_update(bot_token: str, update_dict: dict) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Bot).where(Bot.token == bot_token, Bot.is_active == True)
        )
        bot = result.scalar_one_or_none()
        
        if not bot:
            logger.warning(f"Bot not found or inactive for token: {bot_token[:10]}...")
            return False
        
        if bot.mode != BotMode.WEBHOOK:
            logger.warning(f"Bot {bot.username} is not in webhook mode")
            return False
        
        try:
            telegram_bot = Bot(token=bot_token)
            application = Application.builder().token(bot_token).build()
            
            update = Update.de_json(update_dict, telegram_bot)
            
            await application.process_update(update)
            await application.shutdown()
            
            logger.info(f"Processed webhook update for bot {bot.username}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing webhook for bot {bot.username}: {e}")
            return False


async def register_webhook(bot: Bot) -> bool:
    if not settings.webhook_base_url or settings.webhook_base_url == "https://your-domain.com":
        logger.warning("WEBHOOK_BASE_URL not configured, skipping webhook registration")
        return False
    
    webhook_url = f"{settings.webhook_base_url}{settings.webhook_path}/{bot.token}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot.token}/setWebhook",
                json={
                    "url": webhook_url,
                    "allowed_updates": ["message", "edited_message", "callback_query", "channel_post"],
                    "drop_pending_updates": True,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                logger.info(f"Webhook registered for bot {bot.username}: {webhook_url}")
                return True
            else:
                logger.error(f"Failed to register webhook for bot {bot.username}: {result}")
                return False
                
    except Exception as e:
        logger.error(f"Error registering webhook for bot {bot.username}: {e}")
        return False


async def unregister_webhook(bot_token: str) -> bool:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/deleteWebhook",
                json={"drop_pending_updates": True},
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("ok"):
                logger.info(f"Webhook unregistered for bot token: {bot_token[:10]}...")
                return True
            else:
                logger.error(f"Failed to unregister webhook: {result}")
                return False
                
    except Exception as e:
        logger.error(f"Error unregistering webhook: {e}")
        return False