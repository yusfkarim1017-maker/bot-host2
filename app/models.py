import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Enum, ForeignKey, Text, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class BotMode(str, enum.Enum):
    WEBHOOK = "webhook"
    POLLING = "polling"


class Bot(Base):
    __tablename__ = "bots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    mode = Column(Enum(BotMode), default=BotMode.POLLING, nullable=False)
    owner_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    logs = relationship("BotLog", back_populates="bot", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_bots_is_active", "is_active"),
        Index("ix_bots_owner_id", "owner_id"),
    )


class BotLog(Base):
    __tablename__ = "bot_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bot_id = Column(UUID(as_uuid=True), ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    level = Column(String(20), default="info", nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    bot = relationship("Bot", back_populates="logs")

    __table_args__ = (
        Index("ix_bot_logs_bot_id_timestamp", "bot_id", "timestamp"),
    )