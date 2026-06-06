import logging
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal
from app.models import Bot, BotMode
from app.webhook_handler import register_webhook, unregister_webhook
from app.polling_worker import polling_worker

logger = logging.getLogger(__name__)


class BotManager:
    def __init__(self):
        self._initialized = False
    
    async def initialize(self) -> None:
        if self._initialized:
            return
        
        await polling_worker.start()
        await self._load_active_bots()
        self._initialized = True
        logger.info("BotManager initialized")
    
    async def shutdown(self) -> None:
        await polling_worker.stop()
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Bot).where(Bot.is_active == True, Bot.mode == BotMode.WEBHOOK)
            )
            for bot in result.scalars().all():
                await unregister_webhook(bot.token)
        
        self._initialized = False
        logger.info("BotManager shutdown complete")
    
    async def _load_active_bots(self) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Bot).where(Bot.is_active == True)
            )
            bots = result.scalars().all()
            
            for bot in bots:
                if bot.mode == BotMode.POLLING:
                    await polling_worker.add_bot(bot)
                elif bot.mode == BotMode.WEBHOOK:
                    await register_webhook(bot)
            
            logger.info(f"Loaded {len(bots)} active bots on startup")
    
    async def start_bot(self, bot_id: UUID) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                logger.warning(f"Bot {bot_id} not found")
                return False
            
            bot.is_active = True
            await session.commit()
            await session.refresh(bot)
            
            if bot.mode == BotMode.POLLING:
                return await polling_worker.add_bot(bot)
            elif bot.mode == BotMode.WEBHOOK:
                return await register_webhook(bot)
            
            return False
    
    async def stop_bot(self, bot_id: UUID) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                logger.warning(f"Bot {bot_id} not found")
                return False
            
            bot.is_active = False
            await session.commit()
            
            if bot.mode == BotMode.POLLING:
                return await polling_worker.remove_bot(bot.token)
            elif bot.mode == BotMode.WEBHOOK:
                return await unregister_webhook(bot.token)
            
            return False
    
    async def remove_bot(self, bot_id: UUID) -> bool:
        await self.stop_bot(bot_id)
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            bot = result.scalar_one_or_none()
            
            if bot:
                await session.delete(bot)
                await session.commit()
                logger.info(f"Bot {bot_id} removed from database")
                return True
            
            return False
    
    async def switch_mode(self, bot_id: UUID, new_mode: BotMode) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                logger.warning(f"Bot {bot_id} not found")
                return False
            
            was_active = bot.is_active
            
            if was_active:
                if bot.mode == BotMode.POLLING:
                    await polling_worker.remove_bot(bot.token)
                elif bot.mode == BotMode.WEBHOOK:
                    await unregister_webhook(bot.token)
            
            bot.mode = new_mode
            await session.commit()
            await session.refresh(bot)
            
            if was_active:
                if new_mode == BotMode.POLLING:
                    return await polling_worker.add_bot(bot)
                elif new_mode == BotMode.WEBHOOK:
                    return await register_webhook(bot)
            
            return True
    
    async def get_bot(self, bot_id: UUID) -> Optional[Bot]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            return result.scalar_one_or_none()
    
    async def get_bot_by_token(self, token: str) -> Optional[Bot]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Bot).where(Bot.token == token)
            )
            return result.scalar_one_or_none()
    
    async def list_bots(self, skip: int = 0, limit: int = 100) -> List[Bot]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Bot).offset(skip).limit(limit).order_by(Bot.created_at.desc())
            )
            return list(result.scalars().all())
    
    async def count_bots(self) -> int:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Bot))
            return len(list(result.scalars().all()))
    
    async def create_bot(
        self,
        token: str,
        username: Optional[str] = None,
        owner_id: Optional[str] = None,
        mode: BotMode = BotMode.POLLING,
    ) -> Optional[Bot]:
        async with AsyncSessionLocal() as session:
            existing = await session.execute(
                select(Bot).where(Bot.token == token)
            )
            if existing.scalar_one_or_none():
                logger.warning(f"Bot with token already exists")
                return None
            
            bot = Bot(
                token=token,
                username=username,
                owner_id=owner_id,
                mode=mode,
                is_active=False,
            )
            session.add(bot)
            await session.commit()
            await session.refresh(bot)
            
            logger.info(f"Created bot {bot.username} with mode {mode.value}")
            return bot
    
    async def update_bot(
        self,
        bot_id: UUID,
        username: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> Optional[Bot]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Bot).where(Bot.id == bot_id)
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                return None
            
            if username is not None:
                bot.username = username
            if owner_id is not None:
                bot.owner_id = owner_id
            
            await session.commit()
            await session.refresh(bot)
            
            logger.info(f"Updated bot {bot_id}")
            return bot


bot_manager = BotManager()