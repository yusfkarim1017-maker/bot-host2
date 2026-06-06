import asyncio
import logging
from typing import Dict, Optional
from telegram import Bot
from telegram.ext import Application, ContextTypes
from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Bot, BotMode
from sqlalchemy import select

logger = logging.getLogger(__name__)


class PollingWorker:
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._applications: Dict[str, Application] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
    
    async def start(self) -> None:
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        logger.info(f"Polling worker started with max {self.max_concurrent} concurrent bots")
    
    async def stop(self) -> None:
        for bot_token, task in self._tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error stopping polling for bot {bot_token[:10]}...: {e}")
        
        for bot_token, app in self._applications.items():
            try:
                await app.stop()
                await app.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down app for bot {bot_token[:10]}...: {e}")
        
        self._tasks.clear()
        self._applications.clear()
        logger.info("Polling worker stopped")
    
    async def add_bot(self, bot: Bot) -> bool:
        if bot.token in self._tasks:
            logger.warning(f"Bot {bot.username} already polling")
            return True
        
        async with self._semaphore:
            try:
                application = Application.builder().token(bot.token).build()
                await application.initialize()
                await application.start()
                await application.updater.start_polling(
                    allowed_updates=["message", "edited_message", "callback_query", "channel_post"],
                    drop_pending_updates=True,
                )
                
                self._applications[bot.token] = application
                logger.info(f"Started polling for bot {bot.username}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start polling for bot {bot.username}: {e}")
                return False
    
    async def remove_bot(self, bot_token: str) -> bool:
        if bot_token not in self._tasks and bot_token not in self._applications:
            return True
        
        app = self._applications.pop(bot_token, None)
        if app:
            try:
                await app.updater.stop()
                await app.stop()
                await app.shutdown()
            except Exception as e:
                logger.error(f"Error stopping polling for bot {bot_token[:10]}...: {e}")
        
        task = self._tasks.pop(bot_token, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Stopped polling for bot {bot_token[:10]}...")
        return True
    
    def is_polling(self, bot_token: str) -> bool:
        return bot_token in self._applications
    
    async def restart_bot(self, bot: Bot) -> bool:
        await self.remove_bot(bot.token)
        return await self.add_bot(bot)


polling_worker = PollingWorker(max_concurrent=settings.polling_concurrent_bots)