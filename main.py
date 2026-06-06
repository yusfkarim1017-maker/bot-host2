import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, close_db
from app.bot_manager import bot_manager
from app.routers import webhook, admin

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Telegram Bot Host...")
    
    await init_db()
    logger.info("Database initialized")
    
    await bot_manager.initialize()
    logger.info("Bot manager initialized")
    
    yield
    
    logger.info("Shutting down Telegram Bot Host...")
    await bot_manager.shutdown()
    await close_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Telegram Bot Host",
    description="Multi-bot hosting server for Telegram bots with webhook and polling support",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return {
        "service": "Telegram Bot Host",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )